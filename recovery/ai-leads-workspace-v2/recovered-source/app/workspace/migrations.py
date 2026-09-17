"""Versioned, additive migrations from Relay 0.1's actual six-table schema."""
from __future__ import annotations

import hashlib
import json
import time

SCHEMA = '''
CREATE TABLE IF NOT EXISTS ws_migrations(version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS ws_lead_index(
 lead_id TEXT PRIMARY KEY, sample INTEGER NOT NULL, name TEXT, company TEXT, phone TEXT,
 status TEXT, consent INTEGER NOT NULL, created_at TEXT);
CREATE INDEX IF NOT EXISTS ws_leads_scope_name ON ws_lead_index(sample,name,lead_id);
CREATE TABLE IF NOT EXISTS ws_call_index(
 call_id TEXT PRIMARY KEY, lead_id TEXT, kind TEXT, status TEXT, created_at TEXT, ended_at TEXT);
CREATE INDEX IF NOT EXISTS ws_calls_lead ON ws_call_index(lead_id,created_at DESC);
CREATE INDEX IF NOT EXISTS ws_calls_status ON ws_call_index(kind,status);
CREATE TABLE IF NOT EXISTS ws_capture(
 call_id TEXT PRIMARY KEY, revision INTEGER NOT NULL DEFAULT 0, segment_count INTEGER NOT NULL DEFAULT 0,
 byte_count INTEGER NOT NULL DEFAULT 0, dropped INTEGER NOT NULL DEFAULT 0,
 last_event REAL NOT NULL DEFAULT 0, bridge_active INTEGER NOT NULL DEFAULT 0,
 close_observed INTEGER NOT NULL DEFAULT 0, legacy INTEGER NOT NULL DEFAULT 0,
 flags TEXT NOT NULL DEFAULT '[]');
CREATE TABLE IF NOT EXISTS ws_segments(
 id TEXT PRIMARY KEY, call_id TEXT NOT NULL, seq INTEGER NOT NULL, event_id TEXT,
 content_hash TEXT NOT NULL, role TEXT NOT NULL, text TEXT NOT NULL,
 start_ms REAL, end_ms REAL, received_at TEXT NOT NULL, raw TEXT NOT NULL,
 supersedes TEXT, active INTEGER NOT NULL DEFAULT 1, redacted INTEGER NOT NULL DEFAULT 0,
 UNIQUE(call_id,seq));
CREATE UNIQUE INDEX IF NOT EXISTS ws_segments_event ON ws_segments(call_id,event_id,content_hash)
 WHERE event_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS ws_segments_call ON ws_segments(call_id,active,seq);
CREATE TABLE IF NOT EXISTS ws_heads(
 lead_id TEXT PRIMARY KEY, generation INTEGER NOT NULL DEFAULT 0,
 assessed_generation INTEGER NOT NULL DEFAULT -1, assessment_version INTEGER,
 status TEXT NOT NULL DEFAULT 'unassessed', changed_at REAL NOT NULL DEFAULT 0);
CREATE TABLE IF NOT EXISTS ws_assessments(
 id INTEGER PRIMARY KEY AUTOINCREMENT, lead_id TEXT NOT NULL, generation INTEGER NOT NULL,
 created_at TEXT NOT NULL, rubric_version INTEGER NOT NULL, model TEXT NOT NULL,
 prompt_version TEXT NOT NULL, schema_version TEXT NOT NULL, data TEXT NOT NULL,
 UNIQUE(lead_id,generation,rubric_version,prompt_version));
CREATE INDEX IF NOT EXISTS ws_assessments_lead ON ws_assessments(lead_id,id DESC);
CREATE TABLE IF NOT EXISTS ws_facts(
 id TEXT PRIMARY KEY, lead_id TEXT NOT NULL, call_id TEXT, source_revision INTEGER NOT NULL,
 topic TEXT NOT NULL, data TEXT NOT NULL, created_at TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS ws_facts_lead ON ws_facts(lead_id,call_id);
CREATE TABLE IF NOT EXISTS ws_notes(
 id TEXT PRIMARY KEY, lead_id TEXT NOT NULL, topic TEXT NOT NULL, value TEXT,
 text TEXT NOT NULL, confirmed INTEGER NOT NULL, created_at TEXT NOT NULL,
 supersedes TEXT, active INTEGER NOT NULL DEFAULT 1);
CREATE INDEX IF NOT EXISTS ws_notes_lead ON ws_notes(lead_id,active);
CREATE TABLE IF NOT EXISTS ws_tasks(
 id TEXT PRIMARY KEY, lead_id TEXT NOT NULL, call_id TEXT, source_key TEXT NOT NULL UNIQUE,
 kind TEXT NOT NULL, party TEXT NOT NULL, status TEXT NOT NULL, due_at TEXT,
 created_at TEXT NOT NULL, updated_at TEXT NOT NULL, data TEXT NOT NULL,
 version INTEGER NOT NULL DEFAULT 1);
CREATE INDEX IF NOT EXISTS ws_tasks_due ON ws_tasks(status,due_at,lead_id);
CREATE TABLE IF NOT EXISTS ws_jobs(
 id TEXT PRIMARY KEY, dedupe TEXT NOT NULL UNIQUE, kind TEXT NOT NULL, lead_id TEXT,
 generation INTEGER, status TEXT NOT NULL, attempts INTEGER NOT NULL DEFAULT 0,
 available_at REAL NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
 error TEXT, payload TEXT NOT NULL, result TEXT, model TEXT NOT NULL,
 prompt_version TEXT NOT NULL, schema_version TEXT NOT NULL, rubric_version INTEGER NOT NULL);
CREATE INDEX IF NOT EXISTS ws_jobs_ready ON ws_jobs(status,available_at);
CREATE INDEX IF NOT EXISTS ws_jobs_lead ON ws_jobs(lead_id,created_at DESC);
CREATE TABLE IF NOT EXISTS ws_drafts(job_id TEXT PRIMARY KEY, data TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS ws_extractions(
 cache_key TEXT PRIMARY KEY, call_id TEXT NOT NULL, revision INTEGER NOT NULL,
 chunk INTEGER NOT NULL, data TEXT NOT NULL, created_at TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS ws_extractions_call ON ws_extractions(call_id,revision);
CREATE TABLE IF NOT EXISTS ws_workspace(
 singleton INTEGER PRIMARY KEY CHECK(singleton=1), version INTEGER NOT NULL, data TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS ws_revisions(
 version INTEGER PRIMARY KEY, actor TEXT NOT NULL, reason TEXT NOT NULL,
 created_at TEXT NOT NULL, data TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS ws_proposals(
 id TEXT PRIMARY KEY, base_version INTEGER NOT NULL, status TEXT NOT NULL,
 created_at TEXT NOT NULL, data TEXT NOT NULL, job_id TEXT);
CREATE TABLE IF NOT EXISTS ws_audit(
 id INTEGER PRIMARY KEY AUTOINCREMENT, created_at TEXT NOT NULL, actor TEXT NOT NULL,
 kind TEXT NOT NULL, subject TEXT, summary TEXT NOT NULL, data TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS ws_audit_subject ON ws_audit(subject,id DESC);
CREATE TABLE IF NOT EXISTS ws_fields(id TEXT PRIMARY KEY, version INTEGER NOT NULL, data TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS ws_values(
 lead_id TEXT NOT NULL, field_id TEXT NOT NULL, version INTEGER NOT NULL,
 data TEXT, PRIMARY KEY(lead_id,field_id));
CREATE TABLE IF NOT EXISTS ws_usage(
 id INTEGER PRIMARY KEY AUTOINCREMENT, day TEXT NOT NULL, job_id TEXT NOT NULL,
 reserved_tokens INTEGER NOT NULL, actual_tokens INTEGER, model TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS ws_usage_day ON ws_usage(day);
'''

TRIGGERS = '''
CREATE TRIGGER IF NOT EXISTS ws_lead_insert AFTER INSERT ON leads BEGIN
 INSERT OR REPLACE INTO ws_lead_index VALUES(new.id,coalesce(json_extract(new.data,'$.sample'),0),
 json_extract(new.data,'$.name'),json_extract(new.data,'$.company'),new.phone,
 json_extract(new.data,'$.status'),coalesce(json_extract(new.data,'$.consent'),0),
 json_extract(new.data,'$.created_at'));
 INSERT OR IGNORE INTO ws_heads(lead_id) VALUES(new.id);
END;
CREATE TRIGGER IF NOT EXISTS ws_lead_update AFTER UPDATE ON leads BEGIN
 INSERT OR REPLACE INTO ws_lead_index VALUES(new.id,coalesce(json_extract(new.data,'$.sample'),0),
 json_extract(new.data,'$.name'),json_extract(new.data,'$.company'),new.phone,
 json_extract(new.data,'$.status'),coalesce(json_extract(new.data,'$.consent'),0),
 json_extract(new.data,'$.created_at'));
END;
CREATE TRIGGER IF NOT EXISTS ws_call_insert AFTER INSERT ON calls BEGIN
 INSERT OR REPLACE INTO ws_call_index VALUES(new.id,json_extract(new.data,'$.lead_id'),
 json_extract(new.data,'$.kind'),json_extract(new.data,'$.status'),
 json_extract(new.data,'$.created_at'),json_extract(new.data,'$.ended_at'));
 INSERT OR IGNORE INTO ws_capture(call_id) VALUES(new.id);
END;
CREATE TRIGGER IF NOT EXISTS ws_call_update AFTER UPDATE ON calls BEGIN
 INSERT OR REPLACE INTO ws_call_index VALUES(new.id,json_extract(new.data,'$.lead_id'),
 json_extract(new.data,'$.kind'),json_extract(new.data,'$.status'),
 json_extract(new.data,'$.created_at'),json_extract(new.data,'$.ended_at'));
END;
'''


def migrate(store):
    from ..db import now_iso
    conn = store.conn
    with store.lock:
        conn.executescript(SCHEMA)
        if not conn.execute('SELECT 1 FROM ws_migrations WHERE version=1').fetchone():
            with conn:
                for row in conn.execute('SELECT id,phone,data FROM leads').fetchall():
                    lead = json.loads(row['data'])
                    conn.execute('INSERT OR REPLACE INTO ws_lead_index VALUES(?,?,?,?,?,?,?,?)',
                                 (row['id'], bool(lead.get('sample')), lead.get('name'), lead.get('company'),
                                  row['phone'], lead.get('status'), bool(lead.get('consent')), lead.get('created_at')))
                    conn.execute('INSERT OR IGNORE INTO ws_heads(lead_id,changed_at) VALUES(?,?)', (row['id'], time.time()))
                for row in conn.execute('SELECT id,data FROM calls').fetchall():
                    call = json.loads(row['data'])
                    conn.execute('INSERT OR REPLACE INTO ws_call_index VALUES(?,?,?,?,?,?)',
                                 (row['id'], call.get('lead_id'), call.get('kind'), call.get('status'),
                                  call.get('created_at'), call.get('ended_at')))
                    entries = call.get('transcript', [])
                    byte_count = 0
                    for n, e in enumerate(entries):
                        text = str(e.get('text', ''))
                        byte_count += len(text.encode('utf-8'))
                        ident = 'seg_' + hashlib.sha256(f"{row['id']}:{n}".encode()).hexdigest()[:32]
                        digest = hashlib.sha256(json.dumps(e, sort_keys=True).encode()).hexdigest()
                        conn.execute('INSERT INTO ws_segments VALUES(?,?,?,?,?,?,?,?,?,?,?,?,1,0)',
                                     (ident, row['id'], n + 1, None, digest, e.get('role', 'unknown'), text,
                                      e.get('start_ms'), e.get('end_ms'), call.get('created_at') or now_iso(),
                                      json.dumps(e), None))
                    flags = ['legacy_capture_unverified']
                    if len(entries) >= 12000:
                        flags.append('legacy_limit_reached_possible_truncation')
                    conn.execute('INSERT OR REPLACE INTO ws_capture VALUES(?,?,?,?,?, ?,0,0,1,?)',
                                 (row['id'], len(entries), len(entries), byte_count, 0, time.time(), json.dumps(flags)))
                    call['transcript'] = []
                    call['transcript_storage'] = 'indexed_v1'
                    conn.execute('UPDATE calls SET data=? WHERE id=?', (json.dumps(call), row['id']))
                conn.execute('INSERT INTO ws_migrations VALUES(1,?)', (now_iso(),))
        conn.executescript(TRIGGERS)
        conn.commit()
