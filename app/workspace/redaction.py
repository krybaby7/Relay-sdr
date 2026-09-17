"""Audited source edits. Redaction removes derived copies, not just visible text.

Independent human notes, external deliveries and backups are separate records;
no claim is made that a local operation deletes someone else's copy.
"""
from __future__ import annotations

import json
import time
from ..db import now_iso
from . import evidence, presentation


def source(store, ident, *, lead_id=None, call_id=None):
    row = store.conn.execute('SELECT s.*,c.lead_id FROM ws_segments s JOIN ws_call_index c ON c.call_id=s.call_id WHERE s.id=?', (ident,)).fetchone()
    if not row or (lead_id is not None and row['lead_id'] != lead_id) or (call_id is not None and row['call_id'] != call_id):
        raise KeyError(ident)
    return dict(row)


def correct(store, ident, *, revision, text, reason):
    if not isinstance(text, str) or not 1 <= len(text) <= 16000 or not 5 <= len(reason) <= 500:
        raise ValueError('A correction needs bounded source text and an audit reason.')
    with store.lock, store.conn:
        row = source(store, ident)
        cap = evidence.metadata(store, row['call_id'])
        if cap['revision'] != revision or not row['active'] or row['redacted']:
            raise presentation.Conflict('Source changed; refresh the call before correcting it.')
        eid = row['event_id'] or 'human-source:' + ident
        new_id = evidence.append(store, row['call_id'], {
            'type': 'session.input_transcript.delta' if row['role'] == 'lead' else 'session.output_transcript.delta',
            'event_id': eid, 'delta': text, 'start_ms': row['start_ms'], 'end_ms': row['end_ms'],
        }, human=True)
        if new_id is None:
            raise ValueError('Correction is unchanged, duplicated, or exceeds the capture limit.')
        store.conn.execute('UPDATE ws_segments SET active=0 WHERE id=?', (ident,))
        store.conn.execute('UPDATE ws_segments SET supersedes=?,source_order=? WHERE id=?', (ident, row['source_order'], new_id))
        evidence.flag(store, row['call_id'], 'human_source_correction')
        presentation.audit(store, 'human', 'source_correction', row['call_id'], reason,
                           {'replaces': ident, 'segment_id': new_id})
        return {'segment_id': new_id, 'revision': evidence.metadata(store, row['call_id'])['revision']}


def redact(store, ident, *, revision, reason, confirm):
    if confirm is not True or not isinstance(reason, str) or not 5 <= len(reason) <= 500:
        raise ValueError('Explicit confirmation and a bounded audit reason are required.')
    with store.lock, store.conn:
        row = source(store, ident)
        call_id, lead_id = row['call_id'], row['lead_id']
        cap = evidence.metadata(store, call_id)
        if cap['revision'] != revision:
            raise presentation.Conflict('Source changed; refresh before redacting.')
        # Purge every revision of this logical fragment, including raw payloads.
        related = store.conn.execute('SELECT id,event_id FROM ws_segments WHERE call_id=? AND source_order=?',
                                     (call_id, row['source_order'])).fetchall()
        for item in related:
            if item['event_id']:
                store.conn.execute('INSERT OR IGNORE INTO ws_redactions VALUES(?,?)', (call_id, item['event_id']))
        store.conn.execute("UPDATE ws_segments SET text='',raw='{}',redacted=1 WHERE call_id=? AND source_order=?", (call_id, row['source_order']))
        store.conn.execute('UPDATE ws_capture SET revision=revision+1,last_event=? WHERE call_id=?', (time.time(), call_id))
        evidence.flag(store, call_id, 'operator_redaction')
        # Do not risk retaining the removed quote in an older model interpretation.
        # Preserve job/task identity and workflow history, not sensitive derivations.
        if lead_id:
            store.conn.execute('DELETE FROM ws_facts WHERE lead_id=?', (lead_id,))
            store.conn.execute('DELETE FROM ws_assessments WHERE lead_id=?', (lead_id,))
            store.conn.execute("UPDATE ws_heads SET assessment_version=NULL,assessed_generation=-1,status='unassessed' WHERE lead_id=?", (lead_id,))
            for task in store.conn.execute('SELECT id,status FROM ws_tasks WHERE lead_id=?', (lead_id,)).fetchall():
                safe = {'wording': '[Source-derived task content removed after redaction]', 'reference': None,
                        'nature': 'redacted_source', 'date_phrase': '', 'date_resolution': 'requires_review',
                        'execution': 'internal_only', 'source_active': False}
                status = task['status'] if task['status'] in ('done', 'cancelled') else 'needs_review'
                store.conn.execute('UPDATE ws_tasks SET data=?,status=?,due_at=NULL,version=version+1,updated_at=? WHERE id=?',
                                   (json.dumps(safe), status, now_iso(), task['id']))
        affected = [r['id'] for r in store.conn.execute("SELECT id FROM ws_jobs WHERE lead_id=? OR kind='command'", (lead_id,))]
        for job_id in affected:
            store.conn.execute('DELETE FROM ws_drafts WHERE job_id=?', (job_id,))
            store.conn.execute("UPDATE ws_jobs SET status='superseded',error='Source redacted; run invalidated.',result=NULL WHERE id=? AND status!='succeeded'", (job_id,))
            store.conn.execute('INSERT OR IGNORE INTO ws_checkpoint_purge VALUES(?)', (job_id,))
            store.conn.execute('DELETE FROM ws_proposals WHERE job_id=?', (job_id,))
        store.conn.execute('DELETE FROM ws_extractions WHERE call_id=? OR call_id=? OR call_id IN (SELECT call_id FROM ws_call_index WHERE lead_id=?)',
                           (call_id, 'notes:' + (lead_id or ''), lead_id))
        # Source-derived in-call summaries and requests may contain the redacted text.
        call = store.get('calls', call_id, include_transcript=False)
        store.patch('calls', call_id, summary='', next_step='', requests=[], end_reason='',
                    content_redacted=True)
        store.conn.execute('DELETE FROM tools WHERE key LIKE ? ESCAPE \'\\\'', (call_id.replace('_', '\\_') + ':%',))
        store.conn.execute("UPDATE ws_audit SET data='{}',summary='Call tool metadata removed after source redaction.' WHERE subject=? AND kind='tool_result'", (call_id,))
        outbox = store.get('outbox', call_id)
        if outbox:
            payload = dict(outbox['payload'], summary='', next_step='', requests=[], content_redacted=True)
            store.patch('outbox', call_id, payload=payload,
                        status='sent' if outbox['status'] == 'sent' else 'pending_review')
        # Invalidates in-flight layout plans whose bounded query included this lead.
        state = presentation.current(store)
        version = state['version'] + 1
        spec = json.dumps(state['spec'])
        store.conn.execute('UPDATE ws_workspace SET version=? WHERE singleton=1', (version,))
        store.conn.execute('INSERT INTO ws_revisions VALUES(?,?,?,?,?)',
                           (version, 'human', 'Source redaction invalidated in-flight plans; layout retained.', now_iso(), spec))
        presentation.audit(store, 'human', 'source_redaction', call_id, reason,
                           {'logical_source': ident, 'revisions_removed': len(related), 'derived_lead_intelligence_removed': bool(lead_id)})
        result = {'status': 'redacted', 'revision': evidence.metadata(store, call_id)['revision'],
                  'notice': 'Derived local intelligence was invalidated. Independent notes, backups and external deliveries are not erased by this operation.'}
    # SQLite secure_delete is enabled. Checkpoint WAL where possible, outside a transaction.
    with store.lock:
        store.conn.execute('PRAGMA wal_checkpoint(PASSIVE)')
    return result
