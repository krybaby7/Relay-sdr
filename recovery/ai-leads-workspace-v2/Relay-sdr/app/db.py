from __future__ import annotations
import json, sqlite3, threading, uuid
from datetime import datetime, timezone
from pathlib import Path
from .models import Playbook

def now_iso(): return datetime.now(timezone.utc).isoformat()
def uid(prefix): return f'{prefix}_{uuid.uuid4().hex}'

class Store:
    """Single-process pilot store. Do not run multiple Uvicorn workers."""
    def __init__(self, path: Path | str):
        self.lock = threading.RLock()
        self.conn = sqlite3.connect(str(path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript('''
            PRAGMA journal_mode=WAL;
            CREATE TABLE IF NOT EXISTS leads(id TEXT PRIMARY KEY, phone TEXT UNIQUE, data TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS calls(id TEXT PRIMARY KEY, request_id TEXT UNIQUE, data TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY, data TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS suppression(phone TEXT PRIMARY KEY, reason TEXT, created_at TEXT);
            CREATE TABLE IF NOT EXISTS tools(key TEXT PRIMARY KEY, data TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS outbox(id TEXT PRIMARY KEY, data TEXT NOT NULL);
        ''')
        self.conn.commit()
        if self.get_setting('playbook') is None: self.setting('playbook', Playbook().model_dump())

    def get_setting(self, key):
        with self.lock:
            row = self.conn.execute('SELECT data FROM settings WHERE key=?', (key,)).fetchone()
            return json.loads(row[0]) if row else None
    def setting(self, key, data):
        with self.lock, self.conn:
            self.conn.execute('INSERT OR REPLACE INTO settings VALUES (?,?)', (key, json.dumps(data)))
    def all(self, table):
        assert table in ('leads', 'calls', 'outbox')
        with self.lock:
            return [json.loads(r[0]) for r in self.conn.execute(f'SELECT data FROM {table} ORDER BY rowid DESC')]
    def get(self, table, id):
        assert table in ('leads', 'calls', 'outbox')
        with self.lock:
            row = self.conn.execute(f'SELECT data FROM {table} WHERE id=?', (id,)).fetchone()
            return json.loads(row[0]) if row else None
    def patch(self, table, id, **changes):
        assert table in ('leads', 'calls', 'outbox')
        with self.lock, self.conn:
            data = self.get(table, id)
            if not data: raise KeyError(id)
            data.update(changes)
            self.conn.execute(f'UPDATE {table} SET data=? WHERE id=?', (json.dumps(data), id))
            return data
    def add_lead(self, data, sample=False):
        with self.lock, self.conn:
            row = self.conn.execute('SELECT data FROM leads WHERE phone=?', (data['phone'],)).fetchone()
            if row: return json.loads(row[0]), False
            data = dict(data, id=uid('lead'), created_at=now_iso(), status='new', sample=sample,
                        consent_recorded_at=now_iso() if data.get('consent') else None,
                        opted_out=self.suppressed(data['phone']))
            if data['opted_out']: data.update(status='do_not_call', consent=False)
            self.conn.execute('INSERT INTO leads VALUES (?,?,?)', (data['id'], data['phone'], json.dumps(data)))
            return data, True
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
    def new_call(self, kind, lead_id=None, request_id=None):
        with self.lock, self.conn:
            if request_id:
                row = self.conn.execute('SELECT data FROM calls WHERE request_id=?', (request_id,)).fetchone()
                if row: return json.loads(row[0]), False
            call = dict(id=uid('call'), kind=kind, lead_id=lead_id, created_at=now_iso(),
                        ended_at=None, status='created', provider_sid=None, session_id=None,
                        transcript=[], outcome=None, summary='', next_step='', requests=[],
                        error=None, usage=None, usage_finalized=False)
            self.conn.execute('INSERT INTO calls VALUES (?,?,?)', (call['id'], request_id, json.dumps(call)))
            return call, True
    def by_request(self, request_id):
        with self.lock:
            row = self.conn.execute('SELECT data FROM calls WHERE request_id=?', (request_id,)).fetchone()
            return json.loads(row[0]) if row else None
    def transcript(self, call_id, event):
        with self.lock:
            c = self.get('calls', call_id)
            entries = c['transcript']
            if len(entries) >= 12000: return
            if event.get('event_id') and any(x.get('event_id') == event['event_id'] for x in entries[-100:]): return
            entries.append(dict(role='lead' if event['type'] == 'session.input_transcript.delta' else 'agent',
                text=event.get('delta', ''), start_ms=event.get('start_ms'), end_ms=event.get('end_ms'),
                event_id=event.get('event_id')))
            self.patch('calls', call_id, transcript=entries)
    def tool_result(self, key):
        with self.lock:
            row = self.conn.execute('SELECT data FROM tools WHERE key=?', (key,)).fetchone()
            return json.loads(row[0]) if row else None
    def remember_tool(self, key, result):
        with self.lock, self.conn:
            self.conn.execute('INSERT OR IGNORE INTO tools VALUES (?,?)', (key, json.dumps(result)))
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
