"""Append-only capture with explicit revisions, bounded storage, and honest coverage.

Readable groups are conveniences, not verified speaker turns or diarization.
A provider close/usage event never certifies that every spoken word was captured.
"""
from __future__ import annotations

import hashlib
import json
import math
import time
from ..db import now_iso, uid

MAX_SEGMENTS = 100_000
MAX_BYTES = 8 * 1024 * 1024
TERMINAL = {'completed', 'failed', 'busy', 'no-answer', 'canceled', 'interrupted'}


def metadata(store, call_id):
    row = store.conn.execute('SELECT * FROM ws_capture WHERE call_id=?', (call_id,)).fetchone()
    if not row:
        return None
    result = dict(row)
    result['flags'] = json.loads(result['flags'])
    call = store.conn.execute('SELECT status FROM ws_call_index WHERE call_id=?', (call_id,)).fetchone()
    if result['dropped']:
        status = 'truncated'
    elif result['bridge_active']:
        status = 'capturing'
    elif result['legacy']:
        status = 'legacy_unverified'
    elif not result['segment_count']:
        status = 'no_transcript'
    elif not result['close_observed']:
        status = 'incomplete'
    else:
        status = 'captured_not_certified_complete'
    result.update(status=status, complete=False, timing='source_only',
                  terminal=bool(call and call['status'] in TERMINAL), audio_recorded=False)
    return result


def dirty_lead(store, lead_id):
    if lead_id:
        store.conn.execute('UPDATE ws_heads SET generation=generation+1, changed_at=? WHERE lead_id=?',
                           (time.time(), lead_id))


def dirty_call(store, call_id):
    row = store.conn.execute('SELECT lead_id,kind FROM ws_call_index WHERE call_id=?', (call_id,)).fetchone()
    if row and row['kind'] == 'twilio':
        lead = store.conn.execute('SELECT sample FROM ws_lead_index WHERE lead_id=?', (row['lead_id'],)).fetchone()
        if lead and not lead['sample']:
            dirty_lead(store, row['lead_id'])


def flag(store, call_id, name, **changes):
    with store.lock, store.conn:
        row = metadata(store, call_id)
        if not row:
            raise KeyError(call_id)
        flags = set(row['flags'])
        if name:
            flags.add(name)
        allowed = {'bridge_active', 'close_observed'}
        if set(changes) - allowed:
            raise ValueError('Unsupported capture change.')
        parts = ['flags=?', 'last_event=?'] + [f'{k}=?' for k in changes]
        values = [json.dumps(sorted(flags)), time.time()] + [int(v) for v in changes.values()]
        store.conn.execute(f'UPDATE ws_capture SET {",".join(parts)} WHERE call_id=?', (*values, call_id))
        dirty_call(store, call_id)


def append(store, call_id, event, *, max_segments=MAX_SEGMENTS, max_bytes=MAX_BYTES):
    text = event.get('delta', '')
    if not isinstance(text, str):
        raise ValueError('Transcript delta must be text.')
    role = 'lead' if event.get('type') == 'session.input_transcript.delta' else 'agent'
    eid = event.get('event_id')
    if eid is not None and (not isinstance(eid, str) or len(eid) > 250):
        eid = None
    raw = {k: event.get(k) for k in ('type', 'event_id', 'delta', 'start_ms', 'end_ms')}
    digest = hashlib.sha256(json.dumps(raw, sort_keys=True).encode()).hexdigest()
    with store.lock, store.conn:
        cap = metadata(store, call_id)
        if not cap:
            raise KeyError(call_id)
        if eid and store.conn.execute('SELECT 1 FROM ws_segments WHERE call_id=? AND event_id=? AND content_hash=?',
                                      (call_id, eid, digest)).fetchone():
            return None
        if cap['segment_count'] >= max_segments or cap['byte_count'] + len(text.encode()) > max_bytes:
            store.conn.execute('UPDATE ws_capture SET dropped=dropped+1,revision=revision+1,last_event=? WHERE call_id=?',
                               (time.time(), call_id))
            dirty_call(store, call_id)
            return None
        flags = set(cap['flags'])
        timing = []
        for key in ('start_ms', 'end_ms'):
            value = event.get(key)
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
                value = None
                flags.add('timing_missing_or_invalid')
            timing.append(value)
        if all(v is not None for v in timing) and timing[1] < timing[0]:
            timing = [None, None]
            flags.add('timing_missing_or_invalid')
        previous = store.conn.execute('SELECT id FROM ws_segments WHERE call_id=? AND event_id=? AND active=1',
                                      (call_id, eid)).fetchone() if eid else None
        supersedes = previous['id'] if previous else None
        if previous:
            store.conn.execute('UPDATE ws_segments SET active=0 WHERE id=?', (supersedes,))
            flags.add('revised_source_events')
        ident = uid('seg')
        store.conn.execute('INSERT INTO ws_segments VALUES(?,?,?,?,?,?,?,?,?,?,?,?,1,0)',
                           (ident, call_id, cap['segment_count'] + 1, eid, digest, role, text, *timing,
                            now_iso(), json.dumps(raw), supersedes))
        store.conn.execute('UPDATE ws_capture SET revision=revision+1,segment_count=segment_count+1,'
                           'byte_count=byte_count+?,last_event=?,flags=? WHERE call_id=?',
                           (len(text.encode()), time.time(), json.dumps(sorted(flags)), call_id))
        dirty_call(store, call_id)
        return ident


def segments(store, call_id, *, offset=0, limit=200, include_replaced=False):
    active = '' if include_replaced else 'AND active=1'
    rows = store.conn.execute(f'SELECT id,call_id,seq,event_id,role,text,start_ms,end_ms,received_at,'
                             f'supersedes,active,redacted FROM ws_segments WHERE call_id=? {active} '
                             'ORDER BY seq LIMIT ? OFFSET ?', (call_id, limit, offset)).fetchall()
    return [dict(r) for r in rows]


def readable_sources(store, call_id, *, max_chars=24000):
    """Yield bounded text groups and exact segment-to-character mappings, never drop input.

    Limits apply to each chunk, not to the whole call. Worker budgets explicitly
    label coverage when it cannot process every returned chunk in this run.
    """
    groups, current, length = [], None, 0
    rows = store.conn.execute('SELECT id,role,text,start_ms,end_ms FROM ws_segments '
                             'WHERE call_id=? AND active=1 AND redacted=0 ORDER BY seq', (call_id,))
    for row in rows:
        text = row['text']
        for start in range(0, max(len(text), 1), 4000):
            piece = text[start:start + 4000]
            if not piece:
                continue
            if current is None or current['role'] != row['role'] or len(current['text']) + len(piece) > 4000:
                if current:
                    groups.append(current)
                current = {'source_id': f"{row['id']}:{start}", 'call_id': call_id, 'role': row['role'],
                           'text': '', 'spans': [], 'start_ms': row['start_ms'], 'end_ms': row['end_ms']}
            offset = len(current['text'])
            current['text'] += piece
            current['spans'].append({'segment_id': row['id'], 'group_start': offset,
                                     'group_end': offset + len(piece), 'segment_start': start})
            current['end_ms'] = row['end_ms']
    if current:
        groups.append(current)
    chunk = []
    for group in groups:
        if chunk and length + len(group['text']) > max_chars:
            yield chunk
            chunk, length = [], 0
        chunk.append(group)
        length += len(group['text'])
    if chunk:
        yield chunk


def resolve_reference(ref, sources, *, lead_id, store):
    source = sources.get(ref['source_id'])
    if not source or ref['quote'] not in source['text']:
        raise ValueError('Evidence quote does not match the supplied source.')
    if source.get('note_id'):
        return {'note_id': source['note_id'], 'quote': ref['quote'], 'call_id': None,
                'segment_id': None, 'spans': [], 'source_time': None, 'interpretation': 'human_note'}
    row = store.conn.execute('SELECT lead_id,kind FROM ws_call_index WHERE call_id=?', (source['call_id'],)).fetchone()
    if not row or row['lead_id'] != lead_id or row['kind'] != 'twilio':
        raise ValueError('Evidence belongs to a different lead or a practice call.')
    start = source['text'].index(ref['quote'])
    end = start + len(ref['quote'])
    spans = []
    for span in source['spans']:
        lo, hi = max(start, span['group_start']), min(end, span['group_end'])
        if hi > lo:
            spans.append({'segment_id': span['segment_id'],
                          'start': span['segment_start'] + lo - span['group_start'],
                          'end': span['segment_start'] + hi - span['group_start']})
    if not spans:
        raise ValueError('Empty evidence span.')
    return {'call_id': source['call_id'], 'segment_id': spans[0]['segment_id'], 'spans': spans,
            'quote': ref['quote'], 'source_time': source.get('start_ms'), 'interpretation': 'source_quote'}
