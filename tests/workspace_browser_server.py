"""Loopback-only disposable browser fixture. No real keys, contacts or dialing.

This script is never imported or enabled by the application. It uses the actual
HTTP routes, worker and SQLite store with an explicitly labeled mock model.
Recovered from the interrupted continuation execution record; rerun verification.
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.config import Config
from app.db import now_iso, uid
from app.main import create_app
from app.models import LeadInput
from app.workspace import presentation
from app.workspace.schema import ChangeSet
from workspace_fixtures import FixtureModel, add_real_fixture
import uvicorn

TOKEN = 'relay-browser-fixture-token-not-a-production-secret'


class BrowserModel(FixtureModel):
    fixture_mode = True

    def generate(self, stage, payload, output_model):
        if stage == 'plan' and payload.get('operator_command'):
            command = payload['operator_command'].lower()
            self.requests.append((stage, payload))
            if 'failure' in command:
                return {'data': {'reason': 'Rejected fixture output', 'operations': [{'op': 'dial', 'number': 'never'}]}}
            if 'proposal' in command:
                query = {'scope': 'real', 'search': '', 'filters': [{'field': 'awaiting_proposal', 'op': 'eq', 'value': True}], 'sort': 'priority', 'direction': 'desc', 'group': 'priority'}
                operation = {'op': 'create_view', 'view_id': 'fixture_proposals', 'name': 'Awaiting proposals', 'duplicate_from': 'all', 'query': query}
            else:
                operation = {'op': 'edit_view', 'view_id': payload['current_view_id'], 'name': 'Agent-organized leads'}
            return {'data': {'reason': 'Deterministic fixture organization — not a live model response.', 'operations': [operation]}, 'total_tokens': 10}
        return super().generate(stage, payload, output_model)


def build_app(path: Path):
    config = Config(data_dir=path, admin_token=TOKEN, workspace_enabled=True,
                    workspace_model='mock-browser-fixture', workspace_settle_seconds=0.05,
                    workspace_poll_seconds=0.05, workspace_daily_requests=10000,
                    workspace_daily_tokens=100000000, enable_outbound=False, port=8091)
    app = create_app(config, workspace_model=BrowserModel())
    store = app.state.store
    store.setting('playbook', dict(store.get_setting('playbook'), approved=True, product='Fictional verified workflow product.'))
    store.setting('ws_rubric', dict(store.get_setting('ws_rubric'), approved=True))
    first = None
    for n, company in enumerate(['Acme', 'Atlas', 'Birch', 'Cedar', 'Delta', 'Ember']):
        lead, call = add_real_fixture(store, phone=f'+120255501{10+n}', name=f'Fictional {company}')
        store.patch('leads', lead['id'], company=f'{company} Example Ltd')
        store.patch('calls', call['id'], summary='Fictional buyer requests a proposal and procurement review.',
                    next_step='Review the recorded internal callback request.')
        if first is None:
            first = lead
    for n in range(20, 45):
        store.add_lead(LeadInput(name=f'Uncalled fixture {n:02}', company='Fictional Northwind',
                                phone=f'+120255501{n}', timezone='UTC').model_dump())
    add_real_fixture(store, phone='+12025550180', name='Practice-only sample', kind='browser', sample=True)
    store.new_call('browser')
    for n in range(52):
        call, _ = store.new_call('twilio', first['id'])
        store.patch('calls', call['id'], status='no-answer', ended_at=now_iso())
    with store.lock, store.conn:
        for n in range(30):
            store.conn.execute('INSERT INTO ws_notes VALUES(?,?,?,?,?,?,?,?,1)',
                               (uid('note'), first['id'], 'note', 'unknown', f'Fictional historical note {n:02}.', 0, now_iso(), None))
    for _ in range(100):
        time.sleep(0.01)
        if not app.state.workspace.tick() and store.conn.execute('SELECT count(*) FROM ws_heads WHERE assessed_generation<generation AND lead_id IN (SELECT lead_id FROM ws_lead_index WHERE name LIKE "Fictional%")').fetchone()[0] == 0:
            break
    due = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
    with store.lock, store.conn:
        store.conn.execute("UPDATE ws_tasks SET due_at=?,status='open'", (due,))
    store.suppress('+12025550115', 'Fictional fixture opt-out. Do not contact.')
    current = presentation.current(store)
    presentation.publish(store, ChangeSet(base_version=current['version'],
        reason='Fictional fixture starts on all records.', operations=[{'op': 'preferences', 'mode': 'adaptive',
        'default_view': 'all', 'allow_structural_auto': False}]), actor='human')
    assert not config.enable_outbound and not config.openai_key and not config.workspace_key
    assert store.all('outbox') == []
    return app


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=8091)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='relay-browser-fixture-') as temp:
        uvicorn.run(build_app(Path(temp)), host='127.0.0.1', port=args.port, log_level='warning')
