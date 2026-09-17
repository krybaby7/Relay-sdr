"""Authenticated, bounded application capabilities; no generic tool executor."""
from __future__ import annotations

import asyncio
import json
import time
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query as Param, Request
from fastapi.responses import StreamingResponse
from pydantic import Field

from ..db import now_iso
from . import evidence, intelligence, presentation, queries, redaction
from .model import ModelUnavailable
from .schema import Closed, Query, ChangeSet, FieldDefinition, ID


class QueryRequest(Closed):
    view_id: ID
    query: Query | None = None
    page: Annotated[int, Field(ge=1, le=100000)] = 1
    page_size: Annotated[int, Field(ge=1, le=100)] = 25


class Command(Closed):
    text: Annotated[str, Field(min_length=1, max_length=2000)]
    view_id: ID
    base_version: Annotated[int, Field(ge=1)]


class Restore(Closed):
    base_version: Annotated[int, Field(ge=1)]
    target_version: Annotated[int | None, Field(ge=1)] = None


class Approval(Closed):
    approve: bool
    base_version: Annotated[int, Field(ge=1)]


class Pause(Closed):
    paused: bool


class Note(Closed):
    text: Annotated[str, Field(min_length=1, max_length=5000)]
    topic: str = 'note'
    value: Literal['yes', 'no', 'unknown'] = 'unknown'
    confirmed: bool = False
    supersedes: str | None = None
    generation: Annotated[int, Field(ge=0)]


class Value(Closed):
    version: Annotated[int, Field(ge=0)]
    value: str | bool | int | float | None


class TaskEdit(Closed):
    version: Annotated[int, Field(ge=1)]
    status: Literal['open', 'needs_review', 'waiting', 'proposed', 'done', 'cancelled']
    due_at: Annotated[str | None, Field(max_length=50)] = None


class Correction(Closed):
    revision: Annotated[int, Field(ge=0)]
    text: Annotated[str, Field(min_length=1, max_length=16000)]
    reason: Annotated[str, Field(min_length=5, max_length=500)]


class Redaction(Closed):
    revision: Annotated[int, Field(ge=0)]
    reason: Annotated[str, Field(min_length=5, max_length=500)]
    confirm: bool


class RubricEdit(Closed):
    expected_version: Annotated[int, Field(ge=1)]
    approved: bool
    criteria: dict[str, Annotated[int, Field(ge=1, le=5)]]
    description: Annotated[str, Field(min_length=20, max_length=2000)]


def router(store, worker, admin):
    result = APIRouter(prefix='/api/workspace', dependencies=[Depends(admin)])

    def locked(fn, *args, **kwargs):
        try:
            with store.lock:
                return fn(*args, **kwargs)
        except presentation.Conflict as exc:
            raise HTTPException(409, str(exc)) from None
        except KeyError:
            raise HTTPException(404, 'Scoped workspace record not found.') from None
        except ModelUnavailable as exc:
            raise HTTPException(503, str(exc)) from None
        except ValueError as exc:
            # Pydantic errors can contain raw input. Never reflect source/model content.
            from pydantic import ValidationError
            message = 'Workspace validation failed.' if isinstance(exc, ValidationError) else str(exc)
            raise HTTPException(422, message) from None

    def effective(body):
        view = presentation.view_by_id(presentation.current(store)['spec'], body.view_id)
        query = body.query or Query.model_validate(view['query'])
        if query.scope != view['query']['scope']:
            raise ValueError('Query scope must match the saved view; practice stays separate.')
        return query

    def cursor():
        return store.conn.execute('SELECT coalesce(max(id),0) FROM ws_audit').fetchone()[0]

    @result.get('')
    def bootstrap():
        with store.lock:
            data = presentation.current(store)
            return data | {
                'fields': [json.loads(r['data']) for r in store.conn.execute('SELECT data FROM ws_fields ORDER BY id')],
                'rubric': store.get_setting('ws_rubric'), 'orchestrator': worker.settings(),
                'proposals': queries.json_rows(store.conn.execute("SELECT * FROM ws_proposals WHERE status='pending' ORDER BY created_at DESC LIMIT 50")),
                'cursor': cursor(), 'timezone': store.get_setting('ws_timezone') or 'UTC',
                'fixture_mode': bool(getattr(worker.model, 'fixture_mode', False)),
            }

    @result.post('/query')
    def leads(body: QueryRequest):
        return locked(lambda: queries.query_leads(store, effective(body), page=body.page, page_size=body.page_size))

    @result.post('/aggregates')
    def aggregates(body: QueryRequest):
        return locked(lambda: queries.aggregates(store, effective(body)))

    @result.post('/tasks/query')
    def tasks(body: QueryRequest):
        return locked(lambda: queries.tasks_for_query(store, effective(body), page=body.page, page_size=body.page_size))

    @result.post('/calls/query')
    def calls(body: QueryRequest):
        return locked(lambda: queries.calls_for_query(store, effective(body), page=body.page, page_size=body.page_size))

    @result.get('/leads/{lead_id}')
    def lead(lead_id: str):
        return locked(queries.lead_detail, store, lead_id)

    @result.get('/leads/{lead_id}/calls')
    def lead_calls(lead_id: str, page: Annotated[int, Param(ge=1, le=100000)] = 1,
                   page_size: Annotated[int, Param(ge=1, le=100)] = 50):
        def read():
            if not store.get('leads', lead_id):
                raise KeyError(lead_id)
            rows = store.conn.execute('''SELECT ci.*,cap.segment_count,cap.dropped,cap.close_observed
              FROM ws_call_index ci JOIN ws_capture cap ON ci.call_id=cap.call_id WHERE ci.lead_id=?
              ORDER BY ci.created_at DESC,ci.call_id LIMIT ? OFFSET ?''', (lead_id, page_size + 1, (page - 1) * page_size)).fetchall()
            return {'items': [dict(r) for r in rows[:page_size]], 'page': page, 'has_more': len(rows) > page_size}
        return locked(read)

    @result.get('/leads/{lead_id}/collections/{kind}')
    def collection(lead_id: str, kind: Literal['notes', 'tasks', 'history'],
                   page: Annotated[int, Param(ge=1, le=100000)] = 1,
                   page_size: Annotated[int, Param(ge=1, le=100)] = 25):
        def read():
            if not store.get('leads', lead_id):
                raise KeyError(lead_id)
            # Fixed projections and identifiers; never interpolate caller-supplied SQL.
            statements = {
                'notes': 'SELECT * FROM ws_notes WHERE lead_id=? ORDER BY created_at DESC,id DESC',
                'tasks': 'SELECT * FROM ws_tasks WHERE lead_id=? ORDER BY created_at DESC,id DESC',
                'history': "SELECT id,generation,created_at,model,rubric_version,json_extract(data,'$.potential') AS potential FROM ws_assessments WHERE lead_id=? ORDER BY id DESC",
            }
            rows = store.conn.execute(statements[kind] + ' LIMIT ? OFFSET ?',
                                      (lead_id, page_size + 1, (page-1)*page_size)).fetchall()
            items = queries.json_rows(rows[:page_size]) if kind == 'tasks' else [dict(r) for r in rows[:page_size]]
            return {'items': items, 'page': page, 'has_more': len(rows) > page_size}
        return locked(read)

    @result.get('/notes/{note_id}')
    def note_source(note_id: str, lead_id: str):
        def read():
            row = store.conn.execute('SELECT * FROM ws_notes WHERE id=? AND lead_id=?', (note_id, lead_id)).fetchone()
            if not row:
                raise KeyError(note_id)
            return dict(row)
        return locked(read)

    @result.get('/calls/{call_id}')
    def call(call_id: str, offset: Annotated[int, Param(ge=0, le=100000)] = 0,
             limit: Annotated[int, Param(ge=1, le=200)] = 100, include_replaced: bool = False,
             lead_id: str | None = None):
        def read():
            value = store.get('calls', call_id, include_transcript=False)
            if not value or (lead_id is not None and value['lead_id'] != lead_id):
                raise KeyError(call_id)
            return queries.call_detail(store, call_id, offset=offset, limit=limit, include_replaced=include_replaced)
        return locked(read)

    @result.get('/segments/{segment_id}')
    def segment(segment_id: str, lead_id: str, call_id: str | None = None):
        def read():
            row = redaction.source(store, segment_id, lead_id=lead_id, call_id=call_id)
            predicate = 'call_id=? AND (source_order<? OR (source_order=? AND seq<?))'
            args = (row['call_id'], row['source_order'], row['source_order'], row['seq'])
            offset = store.conn.execute('SELECT count(*) FROM ws_segments WHERE ' + predicate +
                                        ('' if not row['active'] else ' AND active=1'), args).fetchone()[0]
            row.pop('raw', None)
            row.pop('content_hash', None)
            return row | {'page_offset': offset, 'capture_revision': evidence.metadata(store, row['call_id'])['revision']}
        return locked(read)

    @result.post('/segments/{segment_id}/correct')
    def correct(segment_id: str, body: Correction):
        return locked(redaction.correct, store, segment_id, **body.model_dump())

    @result.post('/segments/{segment_id}/redact')
    def redact(segment_id: str, body: Redaction):
        return locked(redaction.redact, store, segment_id, **body.model_dump())

    @result.get('/assessments/{assessment_id}')
    def assessment(assessment_id: int, lead_id: str):
        def read():
            row = store.conn.execute('SELECT * FROM ws_assessments WHERE id=? AND lead_id=?', (assessment_id, lead_id)).fetchone()
            if not row:
                raise KeyError(assessment_id)
            return dict(row) | {'data': json.loads(row['data'])}
        return locked(read)

    @result.post('/leads/{lead_id}/notes')
    def note(lead_id: str, body: Note):
        return locked(intelligence.add_note, store, lead_id, **body.model_dump())

    @result.post('/tasks/{task_id}')
    def task(task_id: str, body: TaskEdit):
        return locked(intelligence.update_task, store, task_id, **body.model_dump())

    @result.post('/changes')
    def changes(body: ChangeSet):
        return locked(presentation.publish, store, body, actor='human')

    @result.post('/restore')
    def restore(body: Restore):
        return locked(presentation.restore, store, **body.model_dump())

    @result.get('/revisions')
    def revisions(before: Annotated[int | None, Param(ge=1)] = None,
                  limit: Annotated[int, Param(ge=1, le=100)] = 50):
        with store.lock:
            rows = store.conn.execute('SELECT version,actor,reason,created_at FROM ws_revisions WHERE version<? ORDER BY version DESC LIMIT ?',
                                      (before or 2**62, limit + 1)).fetchall()
            return {'items': [dict(r) for r in rows[:limit]], 'has_more': len(rows) > limit}

    @result.post('/proposals/{proposal_id}')
    def proposal(proposal_id: str, body: Approval):
        return locked(presentation.approve_proposal, store, proposal_id, **body.model_dump())

    @result.post('/fields')
    def field(body: FieldDefinition):
        return locked(presentation.define_field, store, body)

    @result.put('/leads/{lead_id}/fields/{field_id}')
    def value(lead_id: str, field_id: str, body: Value):
        return locked(presentation.field_value, store, lead_id, field_id, **body.model_dump())

    @result.put('/rubric')
    def rubric(body: RubricEdit):
        def write():
            with store.conn:
                old = store.get_setting('ws_rubric')
                if body.expected_version != old['version']:
                    raise presentation.Conflict('Rubric changed; refresh first.')
                if set(body.criteria) != set(intelligence.RUBRIC_TOPICS):
                    raise ValueError('Rubric must have exactly need, fit, intent and authority weights.')
                rubric = body.model_dump(exclude={'expected_version'}) | {'version': old['version'] + 1}
                store.setting('ws_rubric', rubric)
                store.conn.execute('UPDATE ws_heads SET generation=generation+1,changed_at=? WHERE lead_id IN (SELECT lead_id FROM ws_lead_index WHERE sample=0)', (time.time(),))
                presentation.audit(store, 'human', 'rubric', None, 'Sales rubric version updated; affected assessments become stale.', {'version': rubric['version']})
                return rubric
        return locked(write)

    @result.post('/settings/pause')
    def pause(body: Pause):
        with store.lock, store.conn:
            store.setting('ws_paused', body.paused)
            presentation.audit(store, 'human', 'worker_setting', None, 'Workspace analysis paused.' if body.paused else 'Workspace analysis resumed when server configuration permits.')
            return worker.settings()

    @result.post('/commands')
    def command(body: Command):
        # enqueue is local; this never waits for a model or runs a calling tool.
        def enqueue():
            pending = store.conn.execute("SELECT count(*) FROM ws_jobs WHERE kind='command' AND status IN ('queued','running','retry')").fetchone()[0]
            if pending >= 20:
                raise HTTPException(429, 'At most 20 queued workspace commands.')
            return worker.enqueue_command(body.text, body.view_id, body.base_version)
        return locked(enqueue)

    @result.get('/jobs')
    def jobs(limit: Annotated[int, Param(ge=1, le=100)] = 50):
        with store.lock:
            rows = store.conn.execute('SELECT id,kind,lead_id,status,attempts,error,created_at,updated_at,model,result FROM ws_jobs ORDER BY created_at DESC,id LIMIT ?', (limit,)).fetchall()
            return {'items': [dict(r) | {'result': json.loads(r['result']) if r['result'] else None} for r in rows]}

    @result.post('/jobs/{job_id}/retry')
    def retry(job_id: str):
        def write():
            with store.conn:
                row = store.conn.execute('SELECT * FROM ws_jobs WHERE id=?', (job_id,)).fetchone()
                if not row:
                    raise KeyError(job_id)
                if not worker.config.workspace_enabled or not worker.model.available or store.get_setting('ws_paused'):
                    raise ModelUnavailable('Configure and resume the workspace model before retrying.')
                if row['status'] not in ('failed', 'waiting_configuration', 'retry'):
                    raise presentation.Conflict('Only failed, waiting, or retrying jobs may be retried.')
                if row['lead_id']:
                    head = store.conn.execute('SELECT generation FROM ws_heads WHERE lead_id=?', (row['lead_id'],)).fetchone()
                    if head['generation'] != row['generation']:
                        raise presentation.Conflict('Newer evidence needs a new run; the worker discovers it automatically.')
                elif json.loads(row['payload'])['base_version'] != presentation.current(store)['version']:
                    raise presentation.Conflict('Workspace changed; submit a new command against the current version.')
                store.conn.execute('DELETE FROM ws_drafts WHERE job_id=?', (job_id,))
                store.conn.execute('INSERT OR IGNORE INTO ws_checkpoint_purge VALUES(?)', (job_id,))
                store.conn.execute("UPDATE ws_jobs SET status='queued',attempts=0,error=NULL,result=NULL,available_at=?,updated_at=? WHERE id=?", (time.time(), now_iso(), job_id))
                presentation.audit(store, 'human', 'job_retry', row['lead_id'] or job_id, 'Requested retry of internal workspace analysis.')
                return {'id': job_id, 'status': 'queued'}
        return locked(write)

    @result.get('/activity')
    def activity(scope: Literal['real', 'practice'] = 'real',
                 limit: Annotated[int, Param(ge=1, le=100)] = 30):
        with store.lock:
            predicate = "(ci.call_id IS NOT NULL AND ci.kind!='twilio') OR (ci.call_id IS NULL AND li.sample=1)" if scope == 'practice' else "(ci.call_id IS NOT NULL AND ci.kind='twilio' AND coalesce(cl.sample,0)=0) OR (ci.call_id IS NULL AND coalesce(li.sample,0)=0)"
            rows = store.conn.execute('''SELECT a.id,a.created_at,a.actor,a.kind,a.subject,a.summary FROM ws_audit a
              LEFT JOIN ws_call_index ci ON ci.call_id=a.subject LEFT JOIN ws_lead_index li ON li.lead_id=a.subject
              LEFT JOIN ws_lead_index cl ON cl.lead_id=ci.lead_id WHERE ''' + predicate + ' ORDER BY a.id DESC LIMIT ?', (limit,)).fetchall()
            return {'items': [dict(r) for r in rows], 'scope': scope}

    @result.get('/events')
    async def events(request: Request, after: Annotated[int, Param(ge=0)] = 0):
        async def updates():
            observed = after
            for _ in range(60):
                if await request.is_disconnected():
                    break
                with store.lock:
                    latest = cursor()
                if latest != observed:
                    observed = latest
                    yield 'data: ' + json.dumps({'cursor': latest}) + '\n\n'
                else:
                    yield ': keepalive\n\n'
                await asyncio.sleep(1)
        return StreamingResponse(updates(), media_type='text/event-stream', headers={'X-Accel-Buffering': 'no'})

    return result
