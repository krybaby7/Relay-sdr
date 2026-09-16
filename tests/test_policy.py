from datetime import datetime, timezone
import pytest
from pydantic import ValidationError
from app.models import LeadInput, Playbook
from app.policy import dial_blockers

@pytest.mark.parametrize('phone',['+1 (202) 555-0121','+1-202-555-0121','+12025550121'])
def test_e164_normalization(phone):
    assert LeadInput(name='A',phone=phone).phone=='+12025550121'

@pytest.mark.parametrize('phone',['2025550121','0012025550121','+01234567890','+abc1234567','+12025550121ext2','+1;DROP TABLE leads'])
def test_e164_rejects_ambiguous(phone):
    with pytest.raises(ValidationError): LeadInput(name='A',phone=phone)

def test_consent_needs_evidence():
    with pytest.raises(ValidationError): LeadInput(name='A',phone='+12025550121',consent=True)

def test_bad_timezone():
    with pytest.raises(ValidationError): LeadInput(name='A',phone='+12025550121',timezone='Cairo')

def test_default_playbook_cannot_be_approved():
    with pytest.raises(ValidationError): Playbook(approved=True)

@pytest.mark.parametrize('change',[{'start_hour':17,'end_hour':9},{'weekdays':[]},{'weekdays':[7]},{'voice':'invented'}])
def test_bad_playbook(change):
    with pytest.raises(ValidationError): Playbook(**change)

def test_all_valid_conditions_pass(config,store,book,lead):
    assert dial_blockers(config,store,lead,book)==[]

@pytest.mark.parametrize('field,value,part',[
 ('enable_outbound',False,'disabled'),('openai_key','','configuration'),('allowed_numbers',set(),'allowlist')])
def test_config_gates(config,store,book,lead,field,value,part):
    setattr(config,field,value)
    assert any(part in x for x in dial_blockers(config,store,lead,book))

@pytest.mark.parametrize('change,part',[({'sample':True},'Sample'),({'consent':False},'Permission'),({'consent_note':''},'Permission'),({'opted_out':True},'do-not-call')])
def test_lead_gates(config,store,book,lead,change,part):
    assert any(part in x for x in dial_blockers(config,store,lead|change,book))

def test_unapproved_gate(config,store,book,lead):
    assert any('approve' in x for x in dial_blockers(config,store,lead,book|{'approved':False}))

def test_local_call_window(config,store,book,lead):
    lead['timezone']='Africa/Cairo';book.update(start_hour=9,end_hour=17,weekdays=list(range(7)))
    # September Cairo is UTC+3 under the installed timezone database.
    assert any('window' in x for x in dial_blockers(config,store,lead,book,datetime(2026,9,16,4,tzinfo=timezone.utc)))
    assert not dial_blockers(config,store,lead,book,datetime(2026,9,16,8,tzinfo=timezone.utc))

def test_end_hour_is_exclusive(config,store,book,lead):
    lead['timezone']='UTC';book.update(start_hour=9,end_hour=17)
    assert any('window' in x for x in dial_blockers(config,store,lead,book,datetime(2026,9,16,17,tzinfo=timezone.utc)))

def test_suppression_survives_duplicate_import(config,store,book,lead):
    store.suppress(lead['phone'],'No more calls.')
    existing,created=store.add_lead(lead|{'consent':True})
    assert not created and existing['opted_out'] and not existing['consent']
    assert any('do-not-call' in x for x in dial_blockers(config,store,existing,book))

def test_concurrency_limit(config,store,book,lead):
    store.new_call('browser')
    assert any('concurrent' in x for x in dial_blockers(config,store,lead,book))

def test_daily_attempt_limit(config,store,book,lead):
    config.max_daily=1;call,_=store.new_call('twilio',lead['id']);store.patch('calls',call['id'],status='failed')
    assert any('daily' in x for x in dial_blockers(config,store,lead,book))

def test_unknown_blocks_other_calls(config,store,book,lead):
    call,_=store.new_call('twilio');store.patch('calls',call['id'],status='unknown')
    assert any('unknown' in x for x in dial_blockers(config,store,lead,book))
