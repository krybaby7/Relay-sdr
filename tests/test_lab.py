"""Lab: GPT-Live + Grok orchestrator config, folded playbook, keyless test-talk.

Does not contact providers. Keys never appear in API payloads.
"""
from __future__ import annotations

import json

import httpx
from fastapi.testclient import TestClient

from app.config import Config
from app.main import create_app
from app.workspace.model import ResponsesModel
from app.workspace.schema import Plan
from conftest import TOKEN

GROK_RESPONSES = 'https://api.x.ai/v1/responses'


def test_lab_app_js_parses():
    import subprocess
    from pathlib import Path
    script = Path(__file__).resolve().parents[1] / 'web' / 'app.js'
    result = subprocess.run(['node', '-c', str(script)], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


def test_lab_state_shows_live_and_grok_without_secrets(client, config):
    config.workspace_key = 'xai-secret-must-never-appear'
    body = client.get('/api/state')
    state = body.json()
    live = state['lab']['live']
    grok = state['lab']['orchestrator']
    assert live['key_configured'] is True
    assert live['browser_test_allowed'] is True
    assert live['live_model'] == config.live_model
    assert grok['configured'] is False
    assert grok['provider'] == 'xai'
    assert grok['paused'] is False
    assert state['lab']['rubric']['criteria']['need'] == 3
    text = body.text
    for secret in (config.openai_key, config.twilio_token, config.admin_token, config.workspace_key):
        assert secret not in text
    assert 'sk-' not in text


def test_browser_test_toggle_gates_voice_ticket(client, config):
    assert client.get('/api/state').json()['lab']['live']['browser_test_allowed'] is True
    off = client.post('/api/lab/browser-test', json={'allowed': False})
    assert off.status_code == 200 and off.json()['browser_test_allowed'] is False
    blocked = client.post('/api/voice/ticket', json={})
    assert blocked.status_code == 409
    assert 'Lab' in blocked.json()['detail'] or 'turned off' in blocked.json()['detail'].lower()
    on = client.post('/api/lab/browser-test', json={'allowed': True})
    assert on.json()['browser_test_allowed'] is True
    assert client.post('/api/voice/ticket', json={}).status_code == 200
    assert client.get('/api/state').json()['lab']['live']['browser_test_allowed'] is True


def test_voice_ticket_still_requires_live_key(client, config):
    config.openai_key = ''
    assert client.post('/api/voice/ticket', json={}).status_code == 409


def test_lab_pause_resume_and_rubric_have_no_calling_tools(client):
    paused = client.post('/api/workspace/settings/pause', json={'paused': True}).json()
    assert paused['paused'] is True
    assert client.get('/api/state').json()['lab']['orchestrator']['paused'] is True
    resumed = client.post('/api/workspace/settings/pause', json={'paused': False}).json()
    assert resumed['paused'] is False
    rubric = client.get('/api/state').json()['lab']['rubric']
    saved = client.put('/api/workspace/rubric', json={
        'expected_version': rubric['version'],
        'approved': True,
        'criteria': {'need': 4, 'fit': 3, 'intent': 2, 'authority': 1},
        'description': 'Need and approved product fit first. Intent and authority are supporting evidence only.',
    })
    assert saved.status_code == 200
    assert saved.json()['approved'] is True and saved.json()['criteria']['need'] == 4
    assert 'tools' not in paused and paused.get('has_calling_tools') is not True


def test_playbook_save_stays_on_lab_state(client):
    book = client.get('/api/state').json()['playbook']
    book.update(company='Burnish Lab Co', product='A fictional operator Lab product used only in tests.',
                language='English', tone='Warm and brief.', voice='cedar')
    saved = client.put('/api/playbook', json=book)
    assert saved.status_code == 200
    state = client.get('/api/state').json()
    assert state['playbook']['voice'] == 'cedar'
    assert state['playbook']['company'] == 'Burnish Lab Co'


def test_grok_client_uses_xai_responses_and_never_sends_tools(tmp_path):
    config = Config(data_dir=tmp_path, admin_token=TOKEN, workspace_key='mock-xai-key',
                    workspace_model='grok-4.6')
    captured = []

    def capture(request):
        body = json.loads(request.content)
        captured.append(body)
        assert str(request.url) == GROK_RESPONSES
        assert 'openai.com' not in str(request.url)
        assert 'tools' not in body and 'stream' not in body
        assert body['store'] is False
        assert body['text']['format']['strict'] is True
        return httpx.Response(200, json={
            'status': 'completed',
            'output': [{'type': 'message', 'content': [{'type': 'output_text', 'text':
                '{"reason":"No workspace change.","operations":[]}'}]}],
            'usage': {'total_tokens': 12},
        })

    model = ResponsesModel(config, transport=httpx.MockTransport(capture))
    result = model.generate('plan', {'operator_command': 'leave layout'}, Plan)
    assert result['data']['operations'] == []
    assert captured[0]['model'] == 'grok-4.6'


def test_configured_grok_status_does_not_leak_key(tmp_path):
    secret = 'xai-lab-secret-value-never-in-json'
    config = Config(data_dir=tmp_path, admin_token=TOKEN, workspace_enabled=True,
                    workspace_key=secret, workspace_model='grok-4.6')
    app = create_app(config)
    with TestClient(app, base_url='http://localhost:8080', headers={'Authorization': f'Bearer {TOKEN}'}) as client:
        state = client.get('/api/state').json()
        grok = state['lab']['orchestrator']
        assert grok['configured'] is True
        assert grok['enabled_by_server'] is True
        assert grok['model'] == 'grok-4.6'
        assert grok['provider'] == 'xai'
        payload = client.get('/api/state').text + client.get('/api/workspace').text
        assert secret not in payload
        assert 'api.openai.com' not in payload
