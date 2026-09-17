from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from app.config import Config
from app.main import create_app

TOKEN = 'test-workspace-token-which-is-long-enough'
PHONE = '+12025550121'
SID = 'CA' + '2'*32

class FakeTwilio:
    def __init__(self): self.dials=[]; self.stops=[]; self.failure=None; self.state='completed'
    async def dial(self, call_id, phone):
        self.dials.append((call_id, phone))
        if self.failure: raise self.failure
        return {'sid': SID, 'status': 'queued'}
    async def hangup(self, sid):
        self.stops.append(sid)
        if self.failure: raise self.failure
        return {'sid': sid, 'status':'completed'}
    async def fetch_call(self, sid):
        if self.failure: raise self.failure
        return {'sid':sid,'status':self.state,'to':PHONE,'from':'+12025550199'}

@pytest.fixture
def config(tmp_path):
    return Config(data_dir=tmp_path, admin_token=TOKEN, openai_key='fake-key-never-sent',
        enable_outbound=True, public_url='https://relay.example', twilio_sid='AC'+'1'*32,
        twilio_token='fake-twilio-secret', twilio_from='+12025550199', allowed_numbers={PHONE})

@pytest.fixture
def provider(): return FakeTwilio()

@pytest.fixture
def app(config,provider): return create_app(config,provider=provider)

@pytest.fixture
def client(app):
    with TestClient(app,base_url='http://localhost:8080', headers={'Authorization':f'Bearer {TOKEN}'}) as client:
        yield client

@pytest.fixture
def store(app): return app.state.store

@pytest.fixture
def book(store):
    book=store.get_setting('playbook')
    book.update(company='Real Test Business',product='A pilot product with explicitly verified business facts.',approved=True,
                start_hour=0,end_hour=24,weekdays=list(range(7)))
    store.setting('playbook',book)
    return book

@pytest.fixture
def lead(client):
    result=client.post('/api/leads',json={'name':'Test Lead','company':'Test Business','phone':PHONE,'timezone':'UTC',
        'consent':True,'consent_note':'2026-09-16: test operator explicitly permitted AI sales calls to their own number.'})
    assert result.status_code==200,result.text
    return result.json()['lead']
