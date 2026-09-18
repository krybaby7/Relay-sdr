"""Single-process durable jobs + LangGraph SQLite checkpoints.

A bounded background thread executes the graph; the live audio event loop never
waits for a workspace model. A running server is required; nothing runs when the
server is stopped. Every commit checks source generation and rubric version.
"""
from __future__ import annotations

import asyncio
import json
import sqlite3
import threading
import time
from datetime import datetime, timezone, timedelta
from typing import TypedDict

from langgraph.graph import StateGraph, START, END
from langsmith import tracing_context
from langgraph.checkpoint.sqlite import SqliteSaver

from ..db import uid, now_iso
from . import evidence, intelligence, presentation, queries
from .schema import Extraction, Plan, ChangeSet, Query
from .model import ResponsesModel, ModelUnavailable, ModelFailure, PROMPT_VERSION, SCHEMA_VERSION


class StaleRun(RuntimeError):
    pass


class BudgetExceeded(RuntimeError):
    pass


class ChunkContinuation(RuntimeError):
    """A bounded slice finished; continue cached extraction in a later tick."""


class Stopping(RuntimeError):
    pass


class JSONSerializer:
    """No pickle, imports, constructors, or arbitrary-object deserialization."""
    def dumps_typed(self, value):
        return 'json', json.dumps(value, ensure_ascii=False).encode()

    def loads_typed(self, value):
        typ, data = value
        if typ != 'json':
            raise ValueError('Only JSON workflow checkpoints are accepted.')
        return json.loads(data)


class RunState(TypedDict):
    job_id: str
    phase: str


class WorkspaceWorker:
    def __init__(self, store, config, *, model=None):
        self.store, self.config = store, config
        self.model = model or ResponsesModel(config)
        self.stop_event = threading.Event()
        self.running = False
        self.wake = asyncio.Event()
        self.loop_handle = None
        self.checkpoint_connection = sqlite3.connect(str(config.data_dir / 'workspace-checkpoints.sqlite3'),
                                                     check_same_thread=False)
        self.checkpoint_connection.execute('PRAGMA journal_mode=WAL')
        saver = SqliteSaver(self.checkpoint_connection, serde=JSONSerializer())
        graph = StateGraph(RunState)
        steps = [('readiness', self.prepare), ('extract', self.extract), ('reconcile', self.reconcile),
                 ('compute', self.compute), ('internal_work', self.internal_work), ('plan', self.plan),
                 ('validate', self.validate), ('commit', self.commit), ('notify', self.notify)]
        previous = START
        for name, handler in steps:
            graph.add_node(name, handler)
            graph.add_edge(previous, name)
            previous = name
        graph.add_edge(previous, END)
        self.graph = graph.compile(checkpointer=saver)
        self.saver = saver
        self.tick_lock = threading.Lock()
        self.checkpoint_connection.execute('PRAGMA secure_delete=ON')
        with store.lock, store.conn:
            store.conn.execute("UPDATE ws_jobs SET status='queued',available_at=?,updated_at=? WHERE status='running'",
                               (time.time(), now_iso()))
            if self.model.available:
                store.conn.execute("UPDATE ws_jobs SET status='queued',available_at=? WHERE status='waiting_configuration'", (time.time(),))
            for row in store.conn.execute('SELECT call_id FROM ws_capture WHERE bridge_active=1').fetchall():
                evidence.flag(store, row['call_id'], 'server_restart_during_capture', bridge_active=False)

    def settings(self):
        return {'enabled_by_server': self.config.workspace_enabled, 'configured': bool(self.model.available),
                'paused': bool(self.store.get_setting('ws_paused')), 'model': self.config.workspace_model,
                'max_chunks_per_run': self.config.workspace_max_chunks,
                'max_daily_requests': self.config.workspace_daily_requests,
                'max_daily_reserved_tokens': self.config.workspace_daily_tokens,
                'processing': 'single_process_while_server_runs', 'running': self.running,
                'prompt_version': PROMPT_VERSION, 'schema_version': SCHEMA_VERSION}

    async def loop(self):
        self.running = True
        self.loop_handle = asyncio.get_running_loop()
        try:
            while not self.stop_event.is_set():
                try:
                    await asyncio.to_thread(self.tick)
                except Exception as exc:
                    with self.store.lock, self.store.conn:
                        presentation.audit(self.store, 'system', 'worker_error', None,
                                           f'Workspace worker iteration failed ({type(exc).__name__}); retrying.')
                if not self.stop_event.is_set():
                    try:
                        await asyncio.wait_for(self.wake.wait(), timeout=self.config.workspace_poll_seconds)
                    except asyncio.TimeoutError:
                        pass
                    self.wake.clear()
        finally:
            self.running = False

    def stop(self):
        self.stop_event.set()
        if self.loop_handle and not self.loop_handle.is_closed():
            self.loop_handle.call_soon_threadsafe(self.wake.set)

    def close(self):
        self.checkpoint_connection.close()

    def enqueue_command(self, text, view_id, base_version):
        if not self.config.workspace_enabled or not self.model.available or self.store.get_setting('ws_paused'):
            raise ModelUnavailable('Enable and configure the server-side workspace model first. Manual editing remains available.')
        if not isinstance(text, str) or not 1 <= len(text.strip()) <= 2000:
            raise ValueError('Command must contain 1–2,000 characters.')
        with self.store.lock, self.store.conn:
            state = presentation.current(self.store)
            if state['version'] != base_version:
                raise presentation.Conflict('Workspace changed before command submission.')
            presentation.view_by_id(state['spec'], view_id)
            return self._enqueue('command', None, None, uid('command'),
                                 {'command': text.strip(), 'view_id': view_id, 'base_version': base_version})

    def _enqueue(self, kind, lead_id, generation, dedupe, payload):
        ident = uid('job')
        rubric = self.store.get_setting('ws_rubric')
        self.store.conn.execute('INSERT OR IGNORE INTO ws_jobs VALUES(?,?,?,?,?,\'queued\',0,?,?,?,?,?,?,?,?,?,?)',
                               (ident, dedupe, kind, lead_id, generation, time.time(), now_iso(), now_iso(),
                                None, json.dumps(payload), None, self.config.workspace_model,
                                PROMPT_VERSION, SCHEMA_VERSION, rubric['version']))
        row = self.store.conn.execute('SELECT id,status FROM ws_jobs WHERE dedupe=?', (dedupe,)).fetchone()
        return dict(row)

    def scan(self):
        now = time.time()
        with self.store.lock, self.store.conn:
            rows = self.store.conn.execute('''SELECT h.* FROM ws_heads h JOIN ws_lead_index l ON l.lead_id=h.lead_id
              WHERE l.sample=0 AND h.generation>h.assessed_generation AND h.changed_at<?
              AND (EXISTS(SELECT 1 FROM ws_call_index c WHERE c.lead_id=h.lead_id AND c.kind='twilio'
                    AND c.status IN ('completed','failed','busy','no-answer','canceled','interrupted'))
                   OR EXISTS(SELECT 1 FROM ws_notes n WHERE n.lead_id=h.lead_id AND n.active=1))
              AND NOT EXISTS(SELECT 1 FROM ws_call_index c JOIN ws_capture cap ON c.call_id=cap.call_id
                WHERE c.lead_id=h.lead_id AND c.kind='twilio' AND (cap.bridge_active=1 OR cap.last_event>?
                  OR c.status NOT IN ('completed','failed','busy','no-answer','canceled','interrupted')))
              ORDER BY h.changed_at LIMIT 20''', (now - self.config.workspace_settle_seconds,
                                                 now - self.config.workspace_settle_seconds)).fetchall()
            rubric = self.store.get_setting('ws_rubric')
            for row in rows:
                dedupe = f"lead:{row['lead_id']}:{row['generation']}:{rubric['version']}:{PROMPT_VERSION}:{SCHEMA_VERSION}:{self.config.workspace_model}"
                self._enqueue('analysis', row['lead_id'], row['generation'], dedupe, {})

    def tick(self):
        # Only one graph invocation/checkpoint writer even in test/admin callers.
        if not self.tick_lock.acquire(blocking=False):
            return False
        try:
            self.cleanup_checkpoints()
            return self._tick()
        finally:
            self.cleanup_checkpoints()
            self.tick_lock.release()

    def cleanup_checkpoints(self):
        with self.store.lock:
            ids = [r['job_id'] for r in self.store.conn.execute('SELECT job_id FROM ws_checkpoint_purge LIMIT 100')]
        for ident in ids:
            self.saver.delete_thread(ident)
            with self.store.lock, self.store.conn:
                self.store.conn.execute('DELETE FROM ws_checkpoint_purge WHERE job_id=?', (ident,))

    def _tick(self):
        if self.stop_event.is_set() or not self.config.workspace_enabled or self.store.get_setting('ws_paused'):
            return False
        self.scan()
        with self.store.lock, self.store.conn:
            row = self.store.conn.execute("SELECT * FROM ws_jobs WHERE status IN ('queued','retry') AND available_at<=? "
                                           'ORDER BY created_at,id LIMIT 1', (time.time(),)).fetchone()
            if not row:
                return False
            job = dict(row)
            if not self.model.available:
                self._finish(job, 'waiting_configuration', error='Workspace model unavailable. Manual editing remains available.')
                return True
            self.store.conn.execute("UPDATE ws_jobs SET status='running',attempts=attempts+1,updated_at=?,error=NULL WHERE id=?",
                                    (now_iso(), job['id']))
        config = {'configurable': {'thread_id': job['id']}, 'recursion_limit': 30}
        try:
            if job['result']:
                self._finish(job, 'succeeded')
                return True
            snapshot = self.graph.get_state(config)
            input_state = None if snapshot.next else {'job_id': job['id'], 'phase': 'queued'}
            with tracing_context(enabled=False):
                self.graph.invoke(input_state, config)
            self._finish(job, 'succeeded')
        except ChunkContinuation:
            with self.store.lock, self.store.conn:
                self.store.conn.execute('UPDATE ws_jobs SET attempts=max(0,attempts-1) WHERE id=?', (job['id'],))
            self._finish(job, 'retry', error='Bounded extraction slice saved; continuing remaining source chunks.',
                         available_at=time.time() + self.config.workspace_poll_seconds)
        except StaleRun:
            self._finish(job, 'superseded', error='Newer evidence, corrections, rubric, or model/schema configuration superseded this run.')
        except presentation.Conflict:
            self._finish(job, 'superseded', error='Workspace changed during planning; the stale plan was not published.')
        except ModelUnavailable as exc:
            self._finish(job, 'waiting_configuration', error=str(exc))
        except BudgetExceeded:
            tomorrow = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
            self._finish(job, 'retry', error='Daily workspace model budget reached; resumes next UTC day.',
                         available_at=tomorrow.timestamp())
        except Stopping:
            self._finish(job, 'queued', error='Server stopped; durable job resumes on restart.')
        except Exception as exc:
            attempts = job['attempts'] + 1
            self._finish(job, 'retry' if attempts < 3 else 'failed',
                         error=f'Workspace run failed ({type(exc).__name__}); no unvalidated changes published.',
                         available_at=time.time() + min(300, 5 * 2 ** attempts))
        return True

    def _finish(self, job, status, *, error=None, available_at=None):
        with self.store.lock, self.store.conn:
            self.store.conn.execute('UPDATE ws_jobs SET status=?,error=?,available_at=?,updated_at=? WHERE id=?',
                                    (status, error, available_at or time.time(), now_iso(), job['id']))
            if job['lead_id'] and status in ('failed', 'waiting_configuration'):
                self.store.conn.execute('UPDATE ws_heads SET status=? WHERE lead_id=? AND generation=?',
                                        (status, job['lead_id'], job['generation']))
            if status in ('succeeded', 'superseded'):
                self.store.conn.execute('DELETE FROM ws_drafts WHERE job_id=?', (job['id'],))
                self.store.conn.execute('INSERT OR IGNORE INTO ws_checkpoint_purge VALUES(?)', (job['id'],))
            presentation.audit(self.store, 'system', 'job', job['lead_id'] or job['id'],
                               error or f'Workspace {job["kind"]} run {status}.', {'job_id': job['id'], 'status': status})

    def job(self, state):
        if self.stop_event.is_set():
            raise Stopping()
        with self.store.lock:
            row = self.store.conn.execute('SELECT * FROM ws_jobs WHERE id=?', (state['job_id'],)).fetchone()
            if not row or row['status'] == 'superseded':
                raise StaleRun()
            result = dict(row)
            self.assert_runtime(result)
            result['payload'] = json.loads(result['payload'])
            if result['lead_id']:
                self.assert_fresh(result)
            return result

    def assert_runtime(self, job):
        # Never resume a draft/checkpoint under another model or schema while
        # labeling its output as the old configuration. Analysis will be queued
        # afresh by scan(); operator commands require explicit resubmission.
        if (job['model'] != self.config.workspace_model or
                job['prompt_version'] != PROMPT_VERSION or job['schema_version'] != SCHEMA_VERSION):
            raise StaleRun()

    def assert_fresh(self, job):
        self.assert_runtime(job)
        head = self.store.conn.execute('SELECT generation FROM ws_heads WHERE lead_id=?', (job['lead_id'],)).fetchone()
        rubric = self.store.get_setting('ws_rubric')
        if not head or head['generation'] != job['generation'] or rubric['version'] != job['rubric_version']:
            raise StaleRun()

    def draft(self, job):
        row = self.store.conn.execute('SELECT data FROM ws_drafts WHERE job_id=?', (job['id'],)).fetchone()
        return json.loads(row['data']) if row else {}

    def save_draft(self, job, data):
        with self.store.lock, self.store.conn:
            status = self.store.conn.execute('SELECT status FROM ws_jobs WHERE id=?', (job['id'],)).fetchone()
            if not status or status['status'] == 'superseded':
                raise StaleRun()
            if job['lead_id']:
                self.assert_fresh(job)
            self.store.conn.execute('INSERT OR REPLACE INTO ws_drafts VALUES(?,?)', (job['id'], json.dumps(data)))

    def prepare(self, state):
        job = self.job(state)
        with self.store.lock:
            draft = {'claims': [], 'commitments': [], 'questions': [], 'plan': None,
                     'base_version': presentation.current(self.store)['version'], 'coverage': {
                         'total_chunks': 0, 'processed_chunks': 0, 'total_characters': 0, 'processed_characters': 0,
                         'all_chunks_processed': True, 'transcript_certified_complete': False, 'capture_gaps': []}}
            if job['kind'] == 'analysis':
                lead = self.store.get('leads', job['lead_id'])
                if not lead or lead.get('sample'):
                    raise StaleRun()
                ids = self.store.conn.execute("SELECT call_id FROM ws_call_index WHERE lead_id=? AND kind='twilio' "
                                               "AND status IN ('completed','failed','busy','no-answer','canceled','interrupted') "
                                               'ORDER BY created_at', (lead['id'],)).fetchall()
                draft['calls'] = {}
                for item in ids:
                    call = self.store.get('calls', item['call_id'], include_transcript=False)
                    cap = call['capture']
                    if cap['bridge_active'] or time.time() - cap['last_event'] < self.config.workspace_settle_seconds:
                        raise StaleRun()
                    call.pop('transcript', None)
                    draft['calls'][item['call_id']] = call
                    if cap['flags'] or cap['dropped'] or not cap['close_observed']:
                        draft['coverage']['capture_gaps'].append({'call_id': call['id'], 'status': cap['status'], 'flags': cap['flags']})
                draft['notes'] = [dict(r) for r in self.store.conn.execute(
                    'SELECT * FROM ws_notes WHERE lead_id=? AND active=1 ORDER BY created_at', (lead['id'],))]
                draft['lead'] = {k: lead.get(k) for k in ('id', 'name', 'company', 'timezone', 'notes', 'sample', 'phone')}
            else:
                draft['base_version'] = job['payload']['base_version']
        self.save_draft(job, draft)
        return {'phase': 'ready'}

    def model_request(self, job, stage, payload, output_model):
        if self.stop_event.is_set():
            raise Stopping()
        self.assert_runtime(job)
        encoded = json.dumps(payload, ensure_ascii=False).encode()
        if len(encoded) > 160000:
            raise ModelFailure('Bounded workspace context exceeds the application limit.')
        reservation = len(encoded) + len(json.dumps(output_model.model_json_schema()).encode()) + 4000 + self.config.workspace_output_tokens
        day = datetime.now(timezone.utc).date().isoformat()
        with self.store.lock, self.store.conn:
            used = self.store.conn.execute('SELECT count(*),coalesce(sum(reserved_tokens),0) FROM ws_usage WHERE day=?', (day,)).fetchone()
            if used[0] >= self.config.workspace_daily_requests or used[1] + reservation > self.config.workspace_daily_tokens:
                raise BudgetExceeded()
            cur = self.store.conn.execute('INSERT INTO ws_usage(day,job_id,reserved_tokens,model) VALUES(?,?,?,?)',
                                          (day, job['id'], reservation, self.config.workspace_model))
            usage_id = cur.lastrowid
        result = self.model.generate(stage, payload, output_model)
        try:
            result['data'] = output_model.model_validate(result['data']).model_dump()
        except Exception:
            raise ModelFailure('Workspace output failed application schema validation.') from None
        with self.store.lock, self.store.conn:
            self.store.conn.execute('UPDATE ws_usage SET actual_tokens=? WHERE id=?', (result.get('total_tokens'), usage_id))
        return result['data']

    def extract(self, state):
        job = self.job(state)
        if job['kind'] == 'command':
            return {'phase': 'extraction_not_needed'}
        with self.store.lock:
            draft = self.draft(job)
            rubric = self.store.get_setting('ws_rubric')
            book = self.store.get_setting('playbook')
            book_context = {k: book.get(k) for k in ('approved', 'company', 'product', 'customer_profile', 'facts', 'qualification')}
        def source_units():
            for call_id, call in draft['calls'].items():
                with self.store.lock:
                    chunks = list(evidence.readable_sources(self.store, call_id, max_chars=self.config.workspace_chunk_chars))
                for n, chunk in enumerate(chunks):
                    yield call_id, call['capture']['revision'], n, chunk
            notes = [n for n in draft['notes'] if not n['confirmed']]
            chunk, size, n = [], 0, 0
            for note in notes:
                source = {'source_id': note['id'], 'note_id': note['id'], 'text': note['text'], 'role': 'operator_note'}
                if chunk and size + len(note['text']) > self.config.workspace_chunk_chars:
                    yield None, job['generation'], n, chunk
                    chunk, size, n = [], 0, n + 1
                chunk.append(source)
                size += len(note['text'])
            if chunk:
                yield None, job['generation'], n, chunk
        draft['claims'], draft['commitments'], draft['questions'] = [], [], []
        coverage = draft['coverage']
        coverage.update(total_chunks=0, processed_chunks=0, total_characters=0, processed_characters=0)
        usable_calls = set()
        requests_made = 0
        for call_id, revision, n, chunk in source_units():
            coverage['total_chunks'] += 1
            coverage['total_characters'] += sum(len(source['text']) for source in chunk)
            self.job(state)
            key = intelligence.digest([call_id or job['lead_id'], revision, n, rubric['version'],
                                       intelligence.digest(book_context), PROMPT_VERSION, SCHEMA_VERSION,
                                       self.config.workspace_model, intelligence.digest(chunk)])
            with self.store.lock:
                cache = self.store.conn.execute('SELECT data FROM ws_extractions WHERE cache_key=?', (key,)).fetchone()
            if cache:
                extraction = json.loads(cache['data'])
            elif requests_made < self.config.workspace_max_chunks:
                payload = {'operator_command': None, 'playbook': book_context, 'rubric': rubric,
                           'sources': [{k: v for k, v in source.items() if k != 'spans'} for source in chunk],
                           'scope': 'real', 'call_id': call_id,
                           'capture_notice': 'Source fragments only. Missing words/timing are not recoverable.'}
                raw = self.model_request(job, 'extract', payload, Extraction)
                requests_made += 1
                with self.store.lock, self.store.conn:
                    self.assert_fresh(job)
                    extraction = intelligence.validate_extraction(self.store, job['lead_id'], call_id, revision, raw, chunk)
                    self.store.conn.execute('INSERT OR REPLACE INTO ws_extractions VALUES(?,?,?,?,?,?)',
                                            (key, call_id or 'notes:' + job['lead_id'], revision, n, json.dumps(extraction), now_iso()))
            else:
                continue
            draft['claims'].extend(extraction['claims'])
            draft['commitments'].extend(extraction['commitments'])
            draft['questions'].extend(extraction['questions'])
            if extraction['conversation'] and call_id:
                usable_calls.add(call_id)
            coverage['processed_chunks'] += 1
            coverage['processed_characters'] += sum(len(source['text']) for source in chunk)
        coverage['all_chunks_processed'] = coverage['processed_chunks'] == coverage['total_chunks']
        draft['usable_calls'] = len(usable_calls)
        draft['claims'] = list({c['id']: c for c in draft['claims']}.values())
        self.save_draft(job, draft)
        if not coverage['all_chunks_processed']:
            raise ChunkContinuation()
        return {'phase': 'extracted'}

    def reconcile(self, state):
        job = self.job(state)
        if job['kind'] == 'analysis':
            with self.store.lock:
                draft = self.draft(job)
                head = self.store.conn.execute('SELECT assessment_version FROM ws_heads WHERE lead_id=?', (job['lead_id'],)).fetchone()
                draft['previous_assessment_id'] = head['assessment_version']
                draft['notes'] = [dict(r) for r in self.store.conn.execute('SELECT * FROM ws_notes WHERE lead_id=? AND active=1 ORDER BY created_at',
                                                                         (job['lead_id'],))]
            self.save_draft(job, draft)
        return {'phase': 'reconciled'}

    def compute(self, state):
        job = self.job(state)
        if job['kind'] == 'analysis':
            with self.store.lock:
                draft = self.draft(job)
                rubric = self.store.get_setting('ws_rubric')
            draft['assessment'] = intelligence.compute_assessment(draft['claims'], draft['notes'], rubric,
                usable_calls=draft['usable_calls'], coverage=draft['coverage'], previous=draft['previous_assessment_id'],
                playbook_approved=bool(self.store.get_setting('playbook').get('approved')))
            draft['assessment']['questions'] = draft['questions']
            self.save_draft(job, draft)
        return {'phase': 'computed'}

    def internal_work(self, state):
        self.job(state)
        return {'phase': 'internal_work_staged'}

    def plan(self, state):
        job = self.job(state)
        with self.store.lock:
            draft = self.draft(job)
            workspace = presentation.current(self.store)
            if workspace['version'] != draft['base_version']:
                if job['kind'] == 'command':
                    raise presentation.Conflict()
                draft['plan_skipped'] = 'Workspace changed while analyzing; assessment retained, layout left unchanged.'
                self.save_draft(job, draft)
                return {'phase': 'layout_skipped'}
            if job['kind'] == 'analysis' and (not draft['claims'] or workspace['spec']['mode'] == 'manual'):
                return {'phase': 'no_evidence_no_layout_changes'}
            target_view = job['payload'].get('view_id', 'today')
            view = presentation.view_by_id(workspace['spec'], target_view)
            projection = queries.query_leads(self.store, Query.model_validate(view['query']), page_size=20)
            needed_widgets = set(view['widgets'])
            compact_spec = dict(workspace['spec'])
            compact_spec['views'] = workspace['spec']['views']
            compact_spec['widgets'] = {k: v for k, v in workspace['spec']['widgets'].items()
                                       if k in needed_widgets or any(k in v['widgets'] for v in workspace['spec']['views'] if v['id'] == 'all')}
            payload = {'operator_command': job['payload'].get('command'), 'current_view_id': target_view,
                       'workspace_version': workspace['version'], 'workspace': compact_spec,
                       'leads': projection['items'], 'total_matching': projection['total'],
                       'new_assessment': {k: draft.get('assessment', {}).get(k) for k in
                         ('potential', 'stage', 'confidence', 'unknowns', 'needs_decision', 'awaiting_proposal')},
                       'constraints': 'Only modify referenced widgets; protected All leads remains unfiltered. '
                                      'No model-authored record arrays or metrics are accepted in operations.'}
        try:
            plan = self.model_request(job, 'plan', payload, Plan)
            draft['plan'] = plan
        except (ModelFailure, ModelUnavailable, BudgetExceeded):
            if job['kind'] == 'command':
                raise
            draft['plan'] = None
            draft['plan_skipped'] = 'Presentation planning unavailable; the validated evidence assessment is retained.'
        self.save_draft(job, draft)
        return {'phase': 'planned'}

    def validate(self, state):
        job = self.job(state)
        with self.store.lock:
            draft = self.draft(job)
            if draft.get('plan', {}).get('operations') if draft.get('plan') else False:
                changes = ChangeSet(base_version=draft['base_version'], **draft['plan'])
                workspace = presentation.current(self.store)
                if workspace['version'] != changes.base_version:
                    if job['kind'] == 'command':
                        raise presentation.Conflict()
                    draft['plan_skipped'] = 'Newer manual layout retained.'
                    draft['plan'] = None
                else:
                    try:
                        presentation.transform(self.store, workspace['spec'], changes, 'agent')
                    except (ValueError, KeyError):
                        if job['kind'] == 'command':
                            raise ModelFailure('Workspace plan failed validation; the saved workspace is unchanged.') from None
                        draft['plan'] = None
                        draft['plan_skipped'] = 'Generated presentation plan failed validation; evidence assessment retained.'
        self.save_draft(job, draft)
        return {'phase': 'validated'}

    def commit(self, state):
        job = self.job(state)
        with self.store.lock, self.store.conn:
            draft = self.draft(job)
            result = {}
            if job['kind'] == 'analysis':
                self.assert_fresh(job)
                assessment = draft['assessment']
                self.store.conn.execute('INSERT OR IGNORE INTO ws_assessments(lead_id,generation,created_at,rubric_version,model,prompt_version,schema_version,data) '
                                        'VALUES(?,?,?,?,?,?,?,?)', (job['lead_id'], job['generation'], now_iso(), job['rubric_version'],
                                                                  job['model'], PROMPT_VERSION, SCHEMA_VERSION, json.dumps(assessment)))
                assessment_id = self.store.conn.execute('SELECT id FROM ws_assessments WHERE lead_id=? AND generation=? AND rubric_version=? AND prompt_version=?',
                                                        (job['lead_id'], job['generation'], job['rubric_version'], PROMPT_VERSION)).fetchone()['id']
                status = 'assessed' if draft['claims'] else 'no_conversation'
                self.store.conn.execute('UPDATE ws_heads SET assessed_generation=?,assessment_version=?,status=? WHERE lead_id=? AND generation=?',
                                        (job['generation'], assessment_id, status, job['lead_id'], job['generation']))
                for claim in draft['claims']:
                    self.store.conn.execute('INSERT OR REPLACE INTO ws_facts VALUES(?,?,?,?,?,?,?)',
                                            (claim['id'], job['lead_id'], claim['call_id'], claim['source_revision'],
                                             claim['topic'], json.dumps(claim), now_iso()))
                intelligence.upsert_tasks(self.store, draft['lead'], draft['commitments'], draft['calls'], questions=draft['questions'])
                for task in self.store.conn.execute('SELECT * FROM ws_tasks WHERE lead_id=?', (job['lead_id'],)).fetchall():
                    data = json.loads(task['data'])
                    ref = data.get('reference') or {}
                    ids = [s['segment_id'] for s in ref.get('spans', [])]
                    if ids and any(not self.store.conn.execute('SELECT 1 FROM ws_segments WHERE id=? AND active=1 AND redacted=0', (sid,)).fetchone() for sid in ids):
                        data['source_active'] = False
                        next_status = task['status'] if task['status'] in ('done', 'cancelled') else 'needs_review'
                        self.store.conn.execute('UPDATE ws_tasks SET data=?,status=?,version=version+1 WHERE id=?',
                                                (json.dumps(data), next_status, task['id']))
                presentation.audit(self.store, 'agent', 'assessment', job['lead_id'],
                                   f'Assessment updated: {assessment["potential"]}. Source coverage {draft["coverage"]["processed_chunks"]}/{draft["coverage"]["total_chunks"]} chunks.',
                                   {'assessment_id': assessment_id, 'generation': job['generation'], 'rubric_version': job['rubric_version']})
                result['assessment_id'] = assessment_id
            if draft.get('plan') and draft['plan']['operations']:
                state_now = presentation.current(self.store)
                if state_now['version'] == draft['base_version']:
                    result['workspace'] = presentation.publish(self.store, ChangeSet(base_version=draft['base_version'], **draft['plan']),
                                                                actor='agent', job_id=job['id'])
                    result['workspace'].pop('spec', None)
                elif job['kind'] == 'command':
                    raise presentation.Conflict()
                else:
                    result['layout_skipped'] = 'Newer manual layout retained.'
            else:
                result['workspace'] = {'status': 'unchanged', 'reason': (draft.get('plan') or {}).get('reason') or draft.get('plan_skipped') or 'No useful layout change.'}
            self.store.conn.execute('UPDATE ws_jobs SET result=? WHERE id=?', (json.dumps(result), job['id']))
        return {'phase': 'committed'}

    def notify(self, state):
        self.job(state)
        return {'phase': 'complete'}
