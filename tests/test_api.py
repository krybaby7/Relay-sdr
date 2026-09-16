import json
import httpx
import pytest
from app.telephony import twilio_signature, validate_signature
from conftest import PHONE,SID,TOKEN


def test_auth_required(client):
    assert client.get('/api/state',headers={'Authorization':''}).status_code==401

def test_host_guard(client):
    assert client.get('/api/state',headers={'Host':'evil.example'}).status_code==400

def test_cross_origin_denied(client):
    assert client.post('/api/demo',headers={'Origin':'https://evil.example'}).status_code==403

def test_security_headers_and_local_assets(client):
    r=client.get('/')
    assert r.status_code==200 and 'Relay SDR' in r.text
    assert "script-src 'self'" in r.headers['content-security-policy']
    assert r.headers['cache-control']=='no-store'
    assert client.get('/assets/app.js').status_code==200

def test_secrets_not_in_state(client,config):
    body=client.get('/api/state').text
    for key in [config.openai_key,config.twilio_token,config.admin_token]: assert key not in body

def test_large_body_rejected(client):
    assert client.post('/api/leads',content=b'x'*262145).status_code==413

def test_invalid_lead_is_422(client):
    r=client.post('/api/leads',json={'name':'A','phone':'wrong'})
    assert r.status_code==422 and 'field' in r.json()['detail'][0]

def test_duplicate_keeps_original(client,lead):
    r=client.post('/api/leads',json={'name':'Overwrite attempt','phone':PHONE})
    assert not r.json()['created'] and r.json()['lead']['name']==lead['name']

def test_edit_does_not_change_phone_identity(client,lead):
    fields={k:lead[k] for k in ['name','company','phone','timezone','language','notes','consent','consent_note']}
    fields['phone']='+12025550122'
    assert client.put('/api/leads/'+lead['id'],json=fields).status_code==409

def test_edit_cannot_unsuppress(client,lead,store):
    client.post('/api/leads/'+lead['id']+'/suppress')
    fields={k:lead[k] for k in ['name','company','phone','timezone','language','notes','consent','consent_note']}
    result=client.put('/api/leads/'+lead['id'],json=fields)
    assert result.status_code==200 and not result.json()['consent'] and result.json()['opted_out']

def test_csv_partial_errors_and_duplicates(client,lead):
    csv='name,phone,consent,consent_note\nDuplicate,+12025550121,false,\nNew,+12025550122,false,\nBad,not-a-number,false,\nNo proof,+12025550123,true,\n'
    result=client.post('/api/leads/import',json={'csv':csv}).json()
    assert result['added']==1 and result['duplicates']==1 and len(result['errors'])==2

def test_csv_unknown_consent_rejected(client):
    result=client.post('/api/leads/import',json={'csv':'name,phone,consent\nA,+12025550125,maybe'}).json()
    assert result['added']==0 and len(result['errors'])==1

def test_csv_missing_headers(client):
    assert client.post('/api/leads/import',json={'csv':'name,company\nA,B'}).status_code==422

def test_demo_is_labeled_and_no_provider_used(client,provider,store):
    call=client.post('/api/demo').json()
    assert call['kind']=='simulation' and 'SCRIPTED DEMO' in call['summary'] and len(call['transcript'])==9
    assert not provider.dials and not store.all('outbox')

def test_sample_never_dialed(client,store,book,provider):
    client.post('/api/sample-leads');lead=store.all('leads')[0]
    r=client.post('/api/calls/dial',json={'lead_id':lead['id'],'confirm':True,'request_id':'sample_request_12345'})
    assert r.status_code==409 and any('Sample' in x for x in r.json()['detail'])
    assert not provider.dials

def test_dial_needs_explicit_confirmation(client,lead,book,provider):
    r=client.post('/api/calls/dial',json={'lead_id':lead['id'],'request_id':'request_1234567890'})
    assert r.status_code==422 and not provider.dials

def test_dial_idempotent_and_snapshots_playbook(client,lead,book,provider,store):
    payload={'lead_id':lead['id'],'confirm':True,'request_id':'request_1234567890'}
    a=client.post('/api/calls/dial',json=payload).json();b=client.post('/api/calls/dial',json=payload).json()
    assert not a['reused'] and b['reused'] and len(provider.dials)==1
    assert a['call']['id']==b['call']['id'] and a['call']['provider_sid']==SID
    assert store.get('calls',a['call']['id'])['playbook_snapshot']==book

def test_network_timeout_is_unknown_not_auto_retried(client,lead,book,provider,store):
    provider.failure=httpx.ReadTimeout('simulated timeout')
    payload={'lead_id':lead['id'],'confirm':True,'request_id':'timeout_1234567890'}
    a=client.post('/api/calls/dial',json=payload).json()
    assert a['call']['status']=='unknown'
    b=client.post('/api/calls/dial',json=payload).json()
    assert b['reused'] and len(provider.dials)==1
    payload['request_id']='timeout_new_attempt_999'
    assert client.post('/api/calls/dial',json=payload).status_code==409

def test_second_lead_blocked_by_concurrency(client,lead,book,provider):
    client.post('/api/calls/dial',json={'lead_id':lead['id'],'confirm':True,'request_id':'first_request_12345'})
    r=client.post('/api/calls/dial',json={'lead_id':lead['id'],'confirm':True,'request_id':'second_request_12345'})
    assert r.status_code==409 and len(provider.dials)==1

def test_reconcile_provider_confirmed_state(client,lead,book,store):
    call,_=store.new_call('twilio',lead['id']);store.patch('calls',call['id'],status='unknown',provider_sid=SID)
    r=client.post(f'/api/calls/{call["id"]}/reconcile')
    assert r.status_code==200 and r.json()['status']=='completed'
    assert store.all('outbox')[0]['status']=='pending_review'

def test_reconcile_without_sid_stays_blocked(client,lead,book,store):
    call,_=store.new_call('twilio',lead['id']);store.patch('calls',call['id'],status='unknown')
    assert client.post(f'/api/calls/{call["id"]}/reconcile').status_code==409
    assert store.get('calls',call['id'])['status']=='unknown'

def test_intake_token_scoped_no_dial(client,config,provider):
    config.inbound_token='intake-only-token'
    body={'name':'API Lead','phone':'+12025550127'}
    assert client.post('/integrations/leads',json=body).status_code==401
    r=client.post('/integrations/leads',json=body,headers={'Authorization':'Bearer intake-only-token'})
    assert r.status_code==200 and r.json()['dialed'] is False and not provider.dials
    assert client.get('/api/state',headers={'Authorization':'Bearer intake-only-token'}).status_code==401

def test_browser_requires_key(client,config):
    config.openai_key=''
    assert client.post('/api/voice/ticket',json={}).status_code==409

def test_unsigned_twilio_webhook_rejected(client,store,lead,config):
    call,_=store.new_call('twilio',lead['id'])
    r=client.post(f'/twilio/status/{call["id"]}',data={'CallSid':SID})
    assert r.status_code==403

def signed_post(client,config,path,form):
    signature=twilio_signature(config.twilio_token,config.public_url+path,{k:[v] for k,v in form.items()})
    return client.post(path,data=form,headers={'X-Twilio-Signature':signature})

def twilio_form(config,lead,**extra):
    return {'AccountSid':config.twilio_sid,'CallSid':SID,'From':config.twilio_from,'To':lead['phone'],**extra}

def test_callbacks_ignore_out_of_order_and_terminal_regression(client,store,lead,config):
    call,_=store.new_call('twilio',lead['id']);path=f'/twilio/status/{call["id"]}'
    for status,sequence in [('in-progress','2'),('ringing','1'),('completed','3'),('ringing','4')]:
        assert signed_post(client,config,path,twilio_form(config,lead,CallStatus=status,SequenceNumber=sequence)).status_code==204
    assert store.get('calls',call['id'])['status']=='completed'
    assert len(store.all('outbox'))==1

def test_twiml_binds_parameter_and_websocket(client,store,lead,config):
    call,_=store.new_call('twilio',lead['id']);path=f'/twilio/voice/{call["id"]}'
    r=signed_post(client,config,path,twilio_form(config,lead))
    assert r.status_code==200
    assert 'wss://relay.example/twilio/media/' in r.text and 'relayToken' in r.text
    assert '<Hangup' in r.text and config.twilio_token not in r.text
    assert store.get('calls',call['id'])['provider_sid']==SID

def test_twiml_hangs_up_suppressed_lead(client,store,lead,config):
    call,_=store.new_call('twilio',lead['id']);store.suppress(lead['phone'],'Stop')
    r=signed_post(client,config,f'/twilio/voice/{call["id"]}',twilio_form(config,lead))
    assert '<Hangup' in r.text and '<Stream' not in r.text

def test_signed_but_wrong_call_context_denied(client,store,lead,config):
    call,_=store.new_call('twilio',lead['id']);form=twilio_form(config,lead);form['To']='+12025550188'
    assert signed_post(client,config,f'/twilio/voice/{call["id"]}',form).status_code==403

def test_official_signature_example():
    params={k:[v] for k,v in dict(CallSid='CA1234567890ABCDE',Caller='+14158675310',Digits='1234',From='+14158675310',To='+18005551212').items()}
    url='https://example.com/myapp.php?foo=1&bar=2'
    assert twilio_signature('12345',url,params)=='L/OH5YylLD5NRKLltdqwSvS0BnU='
    assert not validate_signature('12345',url,params,'wrong')

def test_outbox_needs_config_and_confirmation(client,store,lead):
    call,_=store.new_call('twilio',lead['id']);store.patch('calls',call['id'],status='completed');store.enqueue(store.get('calls',call['id']))
    assert client.post(f'/api/outbox/{call["id"]}/deliver',json={}).status_code==422
    assert client.post(f'/api/outbox/{call["id"]}/deliver',json={'confirm':True}).status_code==409
