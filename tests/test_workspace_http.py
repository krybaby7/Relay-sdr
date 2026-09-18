"""Snapshot reads retain the original authorization, scope and request budgets."""
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.config import Config
from app.main import create_app
from workspace_fixtures import add_real_fixture

TOKEN = 'workspace-http-fixture-not-a-production-secret'


@pytest.fixture
def client(tmp_path):
    app = create_app(Config(data_dir=tmp_path, admin_token=TOKEN, workspace_enabled=False))
    add_real_fixture(app.state.store, phone='+12025550191', name='HTTP real fixture')
    add_real_fixture(app.state.store, phone='+12025550192', name='HTTP practice fixture', kind='browser', sample=True)
    with TestClient(app, base_url='http://localhost:8080', headers={'Authorization': f'Bearer {TOKEN}'}) as c:
        yield c


def test_dataset_uses_same_query_and_exact_scope_as_existing_reads(client):
    for view_id, scope, name in [('all', 'real', 'HTTP real fixture'), ('practice', 'practice', 'HTTP practice fixture')]:
        body = {'view_id': view_id, 'query': {'scope': scope}, 'page_size': 25}
        result = client.post('/api/workspace/dataset', json=body)
        assert result.status_code == 200
        data = result.json()
        assert data['records'] == client.post('/api/workspace/query', json=body).json()
        assert data['metrics'] == client.post('/api/workspace/aggregates', json=body).json()
        assert data['tasks'] == client.post('/api/workspace/tasks/query', json=body | {'page_size': 50}).json()
        assert data['calls'] == client.post('/api/workspace/calls/query', json=body | {'page_size': 50}).json()
        assert data['activity'] == client.get('/api/workspace/activity', params={'scope': scope}).json()['items']
        assert data['records']['items'][0]['name'] == name
        assert data['metrics']['total'] == 1
        assert 'transcript' not in str(data['records'])


@pytest.mark.parametrize('body', [
    {'view_id': 'all', 'query': {'scope': 'practice'}},
    {'view_id': 'practice', 'query': {'scope': 'real'}},
    {'view_id': 'all', 'page_size': 101},
    {'view_id': 'all', 'page': 0},
    {'view_id': 'all', 'records': [{'potential': 'strong'}]},
    {'view_id': 'all', 'query': {'filters': [{'field': 'sql', 'value': 'DROP TABLE leads'}]}},
])
def test_dataset_rejects_scope_escape_unbounded_and_model_authored_data(client, body):
    assert client.post('/api/workspace/dataset', json=body).status_code == 422


def test_dataset_empty_is_empty_and_origin_auth_are_preserved(client):
    body = {'view_id': 'all', 'query': {'search': 'nobody-has-this-name'}}
    data = client.post('/api/workspace/dataset', json=body).json()
    assert data['records']['items'] == []
    assert data['metrics']['total'] == data['metrics']['promising'] == data['metrics']['due'] == 0
    assert data['tasks']['items'] == data['calls']['items'] == []
    assert client.post('/api/workspace/dataset', json=body, headers={'Authorization': ''}).status_code == 401
    assert client.post('/api/workspace/dataset', json=body, headers={'Origin': 'https://untrusted.invalid'}).status_code == 403


def test_original_admin_rate_limit_and_retry_after_are_enforced(tmp_path, monkeypatch):
    from app import main
    clock = [1000.0]
    monkeypatch.setattr(main, 'time', SimpleNamespace(monotonic=lambda: clock[0]))
    app = create_app(Config(data_dir=tmp_path, admin_token=TOKEN, workspace_enabled=False))
    with TestClient(app, base_url='http://localhost:8080', headers={'Authorization': f'Bearer {TOKEN}'}) as c:
        for _ in range(180):
            assert c.get('/api/workspace').status_code == 200
        denied = c.get('/api/workspace')
        assert denied.status_code == 429
        assert 1 <= int(denied.headers['Retry-After']) <= 61
        clock[0] += int(denied.headers['Retry-After'])
        assert c.get('/api/workspace').status_code == 200
        assert c.get('/api/workspace', headers={'Authorization': 'wrong'}).status_code == 401
