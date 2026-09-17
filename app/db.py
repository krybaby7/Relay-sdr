from __future__ import annotations
import json, sqlite3, threading, uuid
from datetime import datetime, timezone
from pathlib import Path
from .models import Playbook

def now_iso(): return datetime.now(timezone.utc).isoformat()
def uid(prefix): return f'{prefix}_{uuid.uuid4().hex}'

class AtomicConnection(sqlite3.Connection):
    """Nested application transactions use savepoints; inner helpers never commit outer work.

    Callers must hold Store.lock for every transaction. This is deliberately a
    single-process connection, not a multi-worker database abstraction.
    """
    def __enter__(self):
        stack = getattr(self, '_savepoints', [])
        name = 'relay_' + uuid.uuid4().hex
        self.execute('SAVEPOINT ' + name)
        stack.append(name)
        self._savepoints = stack
        return self

    def __exit__(self, typ, value, traceback):
        name = self._savepoints.pop()
        if typ is not None:
            self.execute('ROLLBACK TO SAVEPOINT ' + name)
        self.execute('RELEASE SAVEPOINT ' + name)
        return False


class Store:
    """Single-process pilot store. Do not run multiple Uvicorn workers."""
    def __init__(self, path: Path | str):
        self.lock = threading.RLock()
        self.conn = sqlite3.connect(str(path), check_same_thread=False, factory=AtomicConnection)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript('''
            PRAGMA journal_mode=WAL;
            PRAGMA secure_delete=ON;
            CREATE TABLE IF NOT EXISTS leads(id TEXT PRIMARY KEY, phone TEXT UNIQUE, data TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS calls(id TEXT PRIMARY KEY, request_id TEXT UNIQUE, data TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY, data TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS suppression(phone TEXT PRIMARY KEY, reason TEXT, created_at TEXT);
            CREATE TABLE IF NOT EXISTS tools(key TEXT PRIMARY KEY, data TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS outbox(id TEXT PRIMARY KEY, data TEXT NOT NULL);
        ''')
        self.conn.commit()
        if self.get_setting('playbook') is None: self.setting('playbook', Playbook().model_dump())
        from .workspace import migrations, presentation
        migrations.migrate(self)
        presentation.initialize(self)

    def get_setting(self, key):
        with self.lock:
            row = self.conn.execute('SELECT data FROM settings WHERE key=?', (key,)).fetchone()
            return json.loads(row[0]) if row else None
    def setting(self, key, data):
        with self.lock, self.conn:
            previous = self.get_setting(key)
            self.conn.execute('INSERT OR REPLACE INTO settings VALUES (?,?)', (key, json.dumps(data)))
            if key == 'playbook' and previous != data and self.conn.execute(
                    "SELECT 1 FROM sqlite_master WHERE type='table' AND name='ws_heads'").fetchone():
                import time
                from .workspace.presentation import audit
                self.conn.execute('UPDATE ws_heads SET generation=generation+1,changed_at=? WHERE lead_id IN '
                                  '(SELECT lead_id FROM ws_lead_index WHERE sample=0)', (time.time(),))
                audit(self, 'human', 'playbook', None, 'Approved product context changed; affected assessments require reconciliation.')
    def all(self, table, *, include_transcript=False):
        assert table in ('leads', 'calls', 'outbox')
        with self.lock:
            return [self._hydrate(table, json.loads(r[0]), include_transcript) for r in self.conn.execute(f'SELECT data FROM {table} ORDER BY rowid DESC')]
    def get(self, table, id, *, include_transcript=True):
        assert table in ('leads', 'calls', 'outbox')
        with self.lock:
            row = self.conn.execute(f'SELECT data FROM {table} WHERE id=?', (id,)).fetchone()
            return self._hydrate(table, json.loads(row[0]), include_transcript) if row else None
    def _hydrate(self, table, data, include_transcript):
        if table == 'calls':
            from .workspace import evidence
            data['capture'] = evidence.metadata(self, data['id'])
            data['transcript_fragments'] = data['capture']['segment_count']
            data['transcript'] = evidence.segments(self, data['id'], limit=100000) if include_transcript else []
        return data
    def patch(self, table, id, **changes):
        assert table in ('leads', 'calls', 'outbox')
        with self.lock, self.conn:
            data = self.get(table, id, include_transcript=False)
            if not data: raise KeyError(id)
            from .workspace import evidence
            before = dict(data)
            if table == 'calls' and 'transcript' in changes:
                raise ValueError('Transcript replacement is forbidden; use audited segment correction.')
            if table == 'leads' and 'phone' in changes and changes['phone'] != data['phone']:
                raise ValueError('Telephone identity is immutable.')
            data.update(changes)
            if table == 'calls':
                data.pop('capture', None)
                data.pop('transcript_fragments', None)
                data['transcript'] = []
                data['transcript_storage'] = 'indexed_v1'
            self.conn.execute(f'UPDATE {table} SET data=? WHERE id=?', (json.dumps(data), id))
            if table == 'calls' and any(before.get(k) != data.get(k) for k in
                    ('status', 'ended_at', 'requests', 'outcome', 'summary', 'next_step')):
                evidence.dirty_call(self, id)
                from .workspace.presentation import audit
                audit(self, 'system', 'call_updated', id, 'Captured call lifecycle or outcome changed.')
            elif table == 'leads' and any(before.get(k) != data.get(k) for k in
                    ('notes', 'company', 'timezone')):
                if before.get('notes') != data.get('notes'):
                    self._legacy_note(id, data.get('notes', ''))
                evidence.dirty_lead(self, id)
            if table == 'leads' and before != data:
                from .workspace.presentation import audit
                audit(self, 'human', 'lead_updated', id, 'Lead record updated; contact policy remains enforced separately.')
            return self._hydrate(table, data, False)
    def add_lead(self, data, sample=False):
        with self.lock, self.conn:
            row = self.conn.execute('SELECT data FROM leads WHERE phone=?', (data['phone'],)).fetchone()
            if row: return json.loads(row[0]), False
            data = dict(data, id=uid('lead'), created_at=now_iso(), status='new', sample=sample,
                        consent_recorded_at=now_iso() if data.get('consent') else None,
                        opted_out=self.suppressed(data['phone']))
            if data['opted_out']: data.update(status='do_not_call', consent=False)
            self.conn.execute('INSERT INTO leads VALUES (?,?,?)', (data['id'], data['phone'], json.dumps(data)))
            self._legacy_note(data['id'], data.get('notes', ''))
            from .workspace.presentation import audit
            audit(self, 'human', 'lead_created', data['id'], 'Fictional sample created.' if sample else 'Lead record created, initially unassessed.')
            return data, True
    def _legacy_note(self, lead_id, text):
        # Keep legacy UI notes as explicit, unconfirmed human source revisions.
        previous = self.conn.execute("SELECT id FROM ws_notes WHERE lead_id=? AND id LIKE 'legacy_note_%' AND active=1", (lead_id,)).fetchone()
        if previous:
            self.conn.execute('UPDATE ws_notes SET active=0 WHERE id=?', (previous['id'],))
        if text and str(text).strip():
            self.conn.execute('INSERT INTO ws_notes VALUES(?,?,?,?,?,?,?,?,1)',
                (uid('legacy_note'), lead_id, 'note', 'unknown', str(text).strip(), 0, now_iso(), previous['id'] if previous else None))

    def suppressed(self, phone):
        with self.lock:
            return bool(self.conn.execute('SELECT 1 FROM suppression WHERE phone=?', (phone,)).fetchone())
    def suppress(self, phone, reason):
        with self.lock, self.conn:
            self.conn.execute('INSERT OR IGNORE INTO suppression VALUES (?,?,?)', (phone, reason, now_iso()))
            row = self.conn.execute('SELECT data FROM leads WHERE phone=?', (phone,)).fetchone()
            if row:
                data = json.loads(row[0]); data.update(opted_out=True, consent=False, status='do_not_call')
                self.conn.execute('UPDATE leads SET data=? WHERE phone=?', (json.dumps(data), phone))
                from .workspace.presentation import audit
                audit(self, 'system', 'suppression', data['id'], 'Permanent do-not-call suppression applied.')
    def new_call(self, kind, lead_id=None, request_id=None):
        with self.lock, self.conn:
            if request_id:
                row = self.conn.execute('SELECT data FROM calls WHERE request_id=?', (request_id,)).fetchone()
                if row: return json.loads(row[0]), False
            call = dict(id=uid('call'), kind=kind, lead_id=lead_id, created_at=now_iso(),
                        ended_at=None, status='created', provider_sid=None, session_id=None,
                        lead_timezone=(self.get('leads', lead_id) or {}).get('timezone') if lead_id else None,
                        transcript=[], transcript_storage='indexed_v1', outcome=None, summary='', next_step='', requests=[],
                        error=None, usage=None, usage_finalized=False)
            self.conn.execute('INSERT INTO calls VALUES (?,?,?)', (call['id'], request_id, json.dumps(call)))
            return call, True
    def by_request(self, request_id):
        with self.lock:
            row = self.conn.execute('SELECT data FROM calls WHERE request_id=?', (request_id,)).fetchone()
            return json.loads(row[0]) if row else None
    def transcript(self, call_id, event):
        from .workspace.evidence import append
        return append(self, call_id, event)

    def tool_result(self, key):
        with self.lock:
            row = self.conn.execute('SELECT data FROM tools WHERE key=?', (key,)).fetchone()
            return json.loads(row[0]) if row else None
    def remember_tool(self, key, result):
        with self.lock, self.conn:
            created = self.conn.execute('INSERT OR IGNORE INTO tools VALUES (?,?)', (key, json.dumps(result)))
            if created.rowcount:
                from .workspace.presentation import audit
                call_id = key.split(':', 1)[0]
                if self.conn.execute('SELECT 1 FROM calls WHERE id=?', (call_id,)).fetchone():
                    audit(self, 'voice', 'tool_result', call_id, 'Call tool result recorded.',
                          {'tool_key': key, 'result': result})
    def enqueue(self, call):
        with self.lock, self.conn:
            # One outcome export per finished call. Call ID is the receiver's idempotency key too.
            existing = self.get('outbox', call['id'])
            if existing: return existing
            event = dict(id=call['id'], type='call.completed', status='pending_review', attempts=0,
                         created_at=now_iso(), sent_at=None, last_error=None,
                         payload=dict(call_id=call['id'], lead_id=call['lead_id'], kind=call['kind'],
                         status=call['status'], provider_sid=call['provider_sid'],
                         outcome=call['outcome'], summary=call['summary'], next_step=call['next_step'],
                         requests=call['requests'], ended_at=call['ended_at']))
            self.conn.execute('INSERT INTO outbox VALUES (?,?)', (event['id'], json.dumps(event)))
            return event
    def close(self): self.conn.close()
