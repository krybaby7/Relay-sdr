"""Deterministic acceptance: no live model, telephony, webhook or lead contact.

These tests exercise real SQLite, LangGraph checkpoints, HTTP validation and
versioned publication. FixtureModel is explicitly NOT a model-quality evaluation.
"""
from __future__ import annotations

import copy
import json
import sqlite3
import threading
import time
from dataclasses import replace
from datetime import datetime, timedelta, timezone

import httpx
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.config import Config
from app.db import Store, now_iso
from app.main import create_app
from app.models import LeadInput
from app.workspace import evidence, intelligence, migrations, presentation, queries, redaction
from app.workspace.model import ModelFailure, ModelUnavailable, ResponsesModel, strict_schema
from app.workspace.schema import ChangeSet, Extraction, FieldDefinition, Plan, Query, Workspace
from app.workspace.worker import WorkspaceWorker
from workspace_fixtures import FixtureModel, TEXT, add_real_fixture

TOKEN = 'isolated-workspace-test-token-not-a-production-secret'


@pytest.fixture
def ws(tmp_path):
    config = Config(data_dir=tmp_path, admin_token=TOKEN, workspace_enabled=True,
                    workspace_model='mock-fixture', workspace_settle_seconds=0,
                    workspace_poll_seconds=0.01, workspace_daily_requests=200,
                    workspace_daily_tokens=10000000)
    store = Store(tmp_path / 'relay.sqlite3')
    book = store.get_setting('playbook')
    store.setting('playbook', dict(book, approved=True, product='Fictional verified workflow product.'))
    store.setting('ws_rubric', dict(store.get_setting('ws_rubric'), approved=True))
    model = FixtureModel()
    workers = []

    def worker(**changes):
        obj = WorkspaceWorker(store, replace(config, **changes), model=model)
        workers.append(obj)
        return obj

    yield store, config, model, worker
    for w in workers:
        try:
            w.close()
        except sqlite3.ProgrammingError:
            pass
    store.close()


def assessment(store, lead_id):
    return queries.lead_detail(store, lead_id)['assessment']['data']


def change(store, *ops, actor='human', version=None):
    return presentation.publish(store, ChangeSet(base_version=version or presentation.current(store)['version'],
                                reason='Deterministic acceptance edit', operations=list(ops)), actor=actor)


def force_ready(store):
    with store.lock, store.conn:
        store.conn.execute('UPDATE ws_jobs SET available_at=0')
        store.conn.execute('UPDATE ws_heads SET changed_at=0')
        store.conn.execute('UPDATE ws_capture SET last_event=0')


def run_all(w, store, limit=40):
    for _ in range(limit):
        force_ready(store)
        if not w.tick():
            return
    raise AssertionError('Worker did not converge within bounded test ticks.')


def test_real_fixture_cumulative_assessment_and_internal_only_tasks(ws):
    store, _, model, new_worker = ws
    lead, call = add_real_fixture(store)
    w = new_worker()
    assert w.tick()
    result = assessment(store, lead['id'])
    assert result['potential'] == 'strong'
    assert result['awaiting_proposal'] is True and result['procurement'] is True
    assert result['coverage']['all_chunks_processed'] is True
    assert result['coverage']['transcript_certified_complete'] is False
    assert result['confidence'] == 'partial'
    claims = result['claims']
    assert len(claims) == 6
    ref = claims[0]['references'][0]
    assert ref['call_id'] == call['id'] and len(ref['spans']) == 2
    assert all(s['segment_id'].startswith('seg_') for s in ref['spans'])
    tasks = queries.lead_detail(store, lead['id'])['tasks']
    assert len(tasks) == 1 and tasks[0]['kind'] == 'callback'
    assert tasks[0]['data']['execution'] == 'internal_only'
    assert store.all('outbox') == []
    assert len(model.requests) == 2
    assert not w.tick()
    assert store.conn.execute('SELECT count(*) FROM ws_drafts').fetchone()[0] == 0
    assert store.conn.execute('SELECT count(*) FROM ws_checkpoint_purge').fetchone()[0] == 0


def test_uncalled_and_no_answer_never_fabricate_qualification(ws):
    store, _, model, new_worker = ws
    uncalled, _ = store.add_lead(LeadInput(name='Uncalled fixture', phone='+12025550142', timezone='UTC').model_dump())
    lead, _ = add_real_fixture(store, text='')
    w = new_worker()
    run_all(w, store)
    assert assessment(store, lead['id'])['potential'] == 'unassessed'
    assert assessment(store, lead['id'])['claims'] == []
    assert queries.lead_detail(store, uncalled['id'])['assessment'] is None
    assert not model.requests
    assert queries.query_leads(store, Query())['total'] == 2


@pytest.mark.parametrize('gate', ['rubric', 'playbook'])
def test_unapproved_business_context_cannot_become_qualified(ws, gate):
    store, _, _, new_worker = ws
    key = 'ws_rubric' if gate == 'rubric' else 'playbook'
    store.setting(key, dict(store.get_setting(key), approved=False))
    lead, _ = add_real_fixture(store)
    run_all(new_worker(), store)
    assert assessment(store, lead['id'])['potential'] == 'unassessed'
    if gate == 'playbook':
        assert assessment(store, lead['id'])['criteria']['fit']['value'] == 'unknown'


def test_long_history_resumes_cached_chunks_across_worker_restart(ws):
    store, _, model, new_worker = ws
    lead, _ = add_real_fixture(store, text=(TEXT + ' ') * 25)
    w = new_worker(workspace_chunk_chars=4000, workspace_max_chunks=1)
    assert w.tick()
    assert queries.lead_detail(store, lead['id'])['assessment'] is None
    first = len([r for r in model.requests if r[0] == 'extract'])
    assert first == 1
    assert store.conn.execute('SELECT status FROM ws_jobs').fetchone()[0] == 'retry'
    assert store.conn.execute('SELECT count(*) FROM ws_extractions').fetchone()[0] == 1
    w.close()
    w = new_worker(workspace_chunk_chars=4000, workspace_max_chunks=1)
    run_all(w, store)
    data = assessment(store, lead['id'])
    assert data['coverage']['total_chunks'] >= 2
    assert data['coverage']['processed_chunks'] == data['coverage']['total_chunks']
    assert len([r for r in model.requests if r[0] == 'extract']) == data['coverage']['total_chunks']
    assert store.conn.execute('SELECT count(*) FROM ws_assessments').fetchone()[0] == 1


def test_finalization_race_waits_for_bridge_and_unknown_call_resolution(ws):
    store, _, model, new_worker = ws
    lead, call = add_real_fixture(store)
    w = new_worker()
    evidence.flag(store, call['id'], None, bridge_active=True)
    store.patch('calls', call['id'], status='completed')
    assert not w.tick()
    evidence.flag(store, call['id'], None, bridge_active=False)
    store.patch('calls', call['id'], status='unknown')
    assert not w.tick()
    assert model.requests == []
    store.patch('calls', call['id'], status='completed')
    assert w.tick()
    assert assessment(store, lead['id'])['potential'] == 'strong'


def test_late_transcript_revision_invalidates_assessment_and_preserves_history(ws):
    store, _, model, new_worker = ws
    lead, call = add_real_fixture(store)
    w = new_worker()
    assert w.tick()
    before = queries.lead_detail(store, lead['id'])
    store.transcript(call['id'], {'type': 'session.input_transcript.delta', 'event_id': 'e2',
                                 'delta': TEXT[19:] + ' This is late source material.'})
    assert queries.lead_detail(store, lead['id'])['stale']
    assert w.tick()
    after = queries.lead_detail(store, lead['id'])
    assert not after['stale'] and len(after['history']) == 2
    assert after['assessment']['id'] != before['assessment']['id']
    assert len(after['tasks']) == 1
    assert len([r for r in model.requests if r[0] == 'extract']) == 2


def test_human_edits_during_model_request_discard_stale_run(ws):
    store, _, model, new_worker = ws
    lead, _ = add_real_fixture(store)
    w = new_worker()

    def correction():
        head = queries.lead_detail(store, lead['id'])['head']
        intelligence.add_note(store, lead['id'], text='The operator verified that interest was declined.',
                              topic='intent', value='no', confirmed=True, generation=head['generation'])
    model.before_return = correction
    assert w.tick()
    assert queries.lead_detail(store, lead['id'])['assessment'] is None
    assert store.conn.execute('SELECT status FROM ws_jobs').fetchone()[0] == 'superseded'
    run_all(w, store)
    data = assessment(store, lead['id'])
    assert data['criteria']['intent']['value'] == 'no'
    assert data['potential'] == 'promising'
    assert any(c['topic'] == 'intent' and c['human_note_id'] for c in data['conflicts'])


@pytest.mark.parametrize('topic,field', [('procurement', 'procurement'), ('proposal', 'awaiting_proposal')])
def test_confirmed_non_rubric_correction_overrides_later_unreviewed_model(ws, topic, field):
    store, _, _, new_worker = ws
    lead, _ = add_real_fixture(store)
    head = queries.lead_detail(store, lead['id'])['head']
    intelligence.add_note(store, lead['id'], text='Verified human correction for this fixture.', topic=topic,
                          value='no', confirmed=True, generation=head['generation'])
    run_all(new_worker(), store)
    data = assessment(store, lead['id'])
    assert data[field] is False
    assert data['topics'][topic]['source'] == 'human_confirmed'
    assert any(c['topic'] == topic for c in data['conflicts'])
    assert any(n['topic'] == topic for n in data['human_facts'])


def test_store_lock_is_not_held_while_model_runs(ws):
    store, _, model, new_worker = ws
    lead, _ = add_real_fixture(store)
    w = new_worker()
    observed = []

    def independent_reader():
        def read():
            with store.lock:
                observed.append(queries.query_leads(store, Query())['total'])
        thread = threading.Thread(target=read)
        thread.start()
        thread.join(timeout=1)
        assert not thread.is_alive(), 'Model invocation held the CRM lock.'
    model.before_return = independent_reader
    assert w.tick()
    assert observed == [1]
    assert assessment(store, lead['id'])['potential'] == 'strong'


def test_duplicate_events_remain_deduplicated_beyond_historical_100_event_window(ws):
    store, _, _, _ = ws
    _, call = add_real_fixture(store)
    before = evidence.metadata(store, call['id'])['revision']
    for n in range(110):
        store.transcript(call['id'], {'type': 'session.input_transcript.delta', 'event_id': f'long-{n}', 'delta': f'item{n}'})
    store.transcript(call['id'], {'type': 'session.input_transcript.delta', 'event_id': 'e1', 'delta': TEXT[:19]})
    assert evidence.metadata(store, call['id'])['revision'] == before + 110
    assert evidence.metadata(store, call['id'])['segment_count'] == 112


def test_revised_fragments_keep_logical_order_and_operator_revision_wins(ws):
    store, _, _, _ = ws
    lead, call = add_real_fixture(store)
    original = evidence.segments(store, call['id'])[0]
    corrected = redaction.correct(store, original['id'], revision=evidence.metadata(store, call['id'])['revision'],
                                  text='Human correction before the second fragment. ', reason='Verified source correction')
    active = evidence.segments(store, call['id'])
    assert active[0]['id'] == corrected['segment_id']
    assert active[1]['text'] == TEXT[19:]
    store.transcript(call['id'], {'type': 'session.input_transcript.delta', 'event_id': 'e1', 'delta': 'Later provider disagreement'})
    assert evidence.segments(store, call['id'])[0]['id'] == corrected['segment_id']
    assert 'provider_revision_conflicts_with_human_correction' in evidence.metadata(store, call['id'])['flags']
    assert len(evidence.segments(store, call['id'], include_replaced=True)) == 4
    assert redaction.source(store, original['id'], lead_id=lead['id'])['active'] == 0


@pytest.mark.parametrize('event', [
    {'event_id': 'bad-time', 'start_ms': -1, 'end_ms': 4},
    {'event_id': 'missing-time'},
    {'event_id': 'reverse-time', 'start_ms': 10, 'end_ms': 2},
])
def test_missing_or_invalid_timing_is_not_invented(ws, event):
    store, _, _, _ = ws
    _, call = add_real_fixture(store, text='')
    store.transcript(call['id'], dict(type='session.input_transcript.delta', delta='source', **event))
    source = evidence.segments(store, call['id'])[0]
    assert source['start_ms'] is None
    assert evidence.metadata(store, call['id'])['complete'] is False
    assert evidence.metadata(store, call['id'])['flags']


def test_capture_limit_is_explicit_and_duplicate_at_cap_is_not_dropped(ws):
    store, _, _, _ = ws
    _, call = add_real_fixture(store, text='')
    event = {'type': 'session.input_transcript.delta', 'event_id': 'bounded', 'delta': 'captured'}
    evidence.append(store, call['id'], event, max_segments=1)
    evidence.append(store, call['id'], event, max_segments=1)
    evidence.append(store, call['id'], dict(event, event_id='extra', delta='not stored'), max_segments=1)
    cap = evidence.metadata(store, call['id'])
    assert cap['segment_count'] == 1 and cap['dropped'] == 1
    assert cap['status'] == 'truncated' and cap['complete'] is False


def test_reference_matching_rejects_cross_lead_practice_and_fabricated_quotes(ws):
    store, _, _, _ = ws
    lead, call = add_real_fixture(store)
    another, practice = add_real_fixture(store, phone='+12025550143', kind='browser')
    source = next(evidence.readable_sources(store, call['id']))[0]
    ref = {'source_id': source['source_id'], 'quote': TEXT[:38]}
    with pytest.raises(ValueError):
        evidence.resolve_reference(ref, {source['source_id']: source}, lead_id=another['id'], store=store)
    with pytest.raises(ValueError):
        evidence.resolve_reference(dict(ref, quote='invented quote'), {source['source_id']: source}, lead_id=lead['id'], store=store)
    source = next(evidence.readable_sources(store, practice['id']))[0]
    with pytest.raises(ValueError):
        evidence.resolve_reference({'source_id': source['source_id'], 'quote': TEXT[:38]},
                                   {source['source_id']: source}, lead_id=another['id'], store=store)


def test_real_redaction_purges_source_revisions_derivations_cache_and_tool_copies(ws):
    store, _, _, new_worker = ws
    lead, call = add_real_fixture(store)
    w = new_worker()
    assert w.tick()
    source = evidence.segments(store, call['id'])[1]
    store.patch('calls', call['id'], summary=source['text'], requests=[{'type': 'meeting', 'details': source['text']}])
    store.remember_tool(call['id'] + ':fixture-tool', {'detail': source['text']})
    store.enqueue(store.get('calls', call['id']))
    result = redaction.redact(store, source['id'], revision=evidence.metadata(store, call['id'])['revision'],
                              reason='Operator-requested test redaction', confirm=True)
    assert result['status'] == 'redacted'
    assert queries.lead_detail(store, lead['id'])['assessment'] is None
    assert store.conn.execute('SELECT count(*) FROM ws_extractions').fetchone()[0] == 0
    assert store.tool_result(call['id'] + ':fixture-tool') is None
    assert store.get('outbox', call['id'])['payload']['summary'] == ''
    assert redaction.source(store, source['id'])['text'] == ''
    assert redaction.source(store, source['id'])['raw'] == '{}'
    assert store.transcript(call['id'], {'type': 'session.input_transcript.delta', 'event_id': 'e2', 'delta': source['text']}) is None
    assert all(t['data']['source_active'] is False for t in queries.lead_detail(store, lead['id'])['tasks'])
    w.cleanup_checkpoints()
    assert store.conn.execute('SELECT count(*) FROM ws_checkpoint_purge').fetchone()[0] == 0


def test_practice_redaction_does_not_touch_real_intelligence_or_generations(ws):
    store, _, _, new_worker = ws
    lead, _ = add_real_fixture(store)
    w = new_worker()
    assert w.tick()
    old = queries.lead_detail(store, lead['id'])
    practice, _ = store.new_call('browser', lead['id'])
    store.transcript(practice['id'], {'type': 'session.input_transcript.delta', 'event_id': 'practice', 'delta': 'Practice source only.'})
    store.patch('calls', practice['id'], status='completed')
    source = evidence.segments(store, practice['id'])[0]
    redaction.redact(store, source['id'], revision=evidence.metadata(store, practice['id'])['revision'],
                     reason='Practice-only redaction test', confirm=True)
    new = queries.lead_detail(store, lead['id'])
    assert new['head']['generation'] == old['head']['generation']
    assert new['assessment']['id'] == old['assessment']['id']
    assert new['tasks'] == old['tasks']
    assert queries.calls_for_query(store, Query(scope='practice'))['items'][0]['call_id'] == practice['id']
    assert queries.tasks_for_query(store, Query(scope='practice'))['total'] == 0
    assert queries.query_leads(store, Query(scope='practice'))['total'] == 0


def test_nested_publication_failure_rolls_back_every_write(ws):
    store, _, _, _ = ws
    state = presentation.current(store)
    op = {'op': 'edit_view', 'view_id': 'today', 'name': 'Do not persist'}
    with pytest.raises(RuntimeError), store.lock, store.conn:
        change(store, op)
        store.setting('temporary_setting', True)
        raise RuntimeError('Injected commit-stage failure')
    assert presentation.current(store) == state
    assert store.get_setting('temporary_setting') is None


def test_invalid_second_operation_publishes_nothing(ws):
    store, _, _, _ = ws
    before = presentation.current(store)
    with pytest.raises(ValueError):
        change(store, {'op': 'edit_view', 'view_id': 'today', 'name': 'Must not persist'},
               {'op': 'delete_view', 'view_id': 'all'})
    assert presentation.current(store) == before


def test_stale_manual_writes_fail_without_overwriting(ws):
    store, _, _, _ = ws
    old = presentation.current(store)['version']
    change(store, {'op': 'edit_view', 'view_id': 'today', 'name': 'Newer operator edit'})
    with pytest.raises(presentation.Conflict):
        change(store, {'op': 'edit_view', 'view_id': 'today', 'name': 'Stale edit'}, version=old)
    assert presentation.view_by_id(presentation.current(store)['spec'], 'today')['name'] == 'Newer operator edit'


def test_ai_manual_pin_reload_ai_cannot_overwrite(ws):
    store, _, _, _ = ws
    view = presentation.view_by_id(presentation.current(store)['spec'], 'today')
    change(store, {'op': 'edit_view', 'view_id': 'today', 'name': 'AI organized queue'}, actor='agent')
    layouts = copy.deepcopy(view['layouts'])
    for bp in layouts:
        for g in layouts[bp]:
            g['y'] += 2
    widget_id = view['widgets'][0]
    change(store, {'op': 'set_layout', 'view_id': 'today', 'layouts': layouts},
           {'op': 'pin_widget', 'view_id': 'today', 'widget_id': widget_id, 'pinned': True})
    saved = presentation.current(store)
    other = Store(store.conn.execute('PRAGMA database_list').fetchone()[2])
    assert presentation.current(other) == saved
    other.close()
    with pytest.raises(presentation.Locked):
        change(store, {'op': 'set_layout', 'view_id': 'today', 'layouts': view['layouts']}, actor='agent')
    assert presentation.current(store) == saved


@pytest.mark.parametrize('op', [
    {'op': 'preferences', 'mode': 'adaptive', 'default_view': 'all', 'allow_structural_auto': True},
    {'op': 'lock_view', 'view_id': 'today', 'locked': False},
])
def test_model_cannot_grant_itself_authority(ws, op):
    store, _, _, _ = ws
    with pytest.raises(presentation.Locked):
        change(store, op, actor='agent')


@pytest.mark.parametrize('mode', ['manual', 'suggest', 'adaptive'])
def test_structural_changes_require_proposal_unless_explicitly_allowed(ws, mode):
    store, _, _, _ = ws
    change(store, {'op': 'preferences', 'mode': mode, 'default_view': 'today', 'allow_structural_auto': False})
    result = change(store, {'op': 'create_view', 'view_id': 'custom_test', 'name': 'Custom reviewed view',
                            'query': Query().model_dump(), 'duplicate_from': 'all'}, actor='agent')
    assert result['status'] == 'proposed'
    assert not any(v['id'] == 'custom_test' for v in presentation.current(store)['spec']['views'])
    approved = presentation.approve_proposal(store, result['proposal_id'], approve=True, base_version=result['version'])
    assert approved['status'] == 'applied'
    assert any(v['id'] == 'custom_test' for v in approved['spec']['views'])


def test_stale_proposal_does_not_replace_manual_change(ws):
    store, _, _, _ = ws
    result = change(store, {'op': 'create_view', 'view_id': 'custom_test', 'name': 'Proposal candidate',
                            'query': Query().model_dump(), 'duplicate_from': 'all'}, actor='agent')
    change(store, {'op': 'edit_view', 'view_id': 'today', 'name': 'Operator changed this'})
    with pytest.raises(presentation.Conflict):
        presentation.approve_proposal(store, result['proposal_id'], approve=True, base_version=result['version'])
    assert presentation.view_by_id(presentation.current(store)['spec'], 'today')['name'] == 'Operator changed this'


def test_locked_view_rejects_geometry_configuration_and_indirect_edits(ws):
    store, _, _, _ = ws
    change(store, {'op': 'lock_view', 'view_id': 'today', 'locked': True})
    state = presentation.current(store)
    view = presentation.view_by_id(state['spec'], 'today')
    widget = dict(state['spec']['widgets'][view['widgets'][0]], title='Not allowed')
    with pytest.raises(presentation.Locked):
        change(store, {'op': 'configure_widget', 'view_id': 'today', 'widget': widget}, actor='agent')
    assert presentation.current(store) == state


def test_overlap_and_mobile_overflow_rejected(ws):
    store, _, _, _ = ws
    view = presentation.view_by_id(presentation.current(store)['spec'], 'all')
    layouts = copy.deepcopy(view['layouts'])
    layouts['sm'][1]['y'] = layouts['sm'][0]['y']
    with pytest.raises(ValidationError):
        change(store, {'op': 'set_layout', 'view_id': 'all', 'layouts': layouts})
    layouts = copy.deepcopy(view['layouts'])
    layouts['sm'][0]['w'] = 12
    with pytest.raises(ValidationError):
        change(store, {'op': 'set_layout', 'view_id': 'all', 'layouts': layouts})


def test_restore_changes_only_presentation_not_leads_or_evidence(ws):
    store, _, _, new_worker = ws
    lead, call = add_real_fixture(store)
    run_all(new_worker(), store)
    before = (store.get('leads', lead['id']), store.get('calls', call['id']), assessment(store, lead['id']))
    change(store, {'op': 'edit_view', 'view_id': 'today', 'name': 'Temporary custom name'})
    presentation.restore(store, presentation.current(store)['version'], 1)
    after = (store.get('leads', lead['id']), store.get('calls', call['id']), assessment(store, lead['id']))
    assert before == after
    assert presentation.view_by_id(presentation.current(store)['spec'], 'today')['name'] == 'Today'


@pytest.mark.parametrize('typ,value,bad', [('text', 'test', 17), ('number', 12.5, True),
    ('boolean', False, 'false'), ('date', '2026-09-18', '2026-02-30'), ('select', 'a', 'c')])
def test_typed_custom_fields_unknown_values_and_compare_and_swap(ws, typ, value, bad):
    store, _, _, _ = ws
    lead, _ = add_real_fixture(store)
    field = FieldDefinition(id='cf_test', name='Acceptance field', type=typ, options=['a','b'] if typ == 'select' else [])
    presentation.define_field(store, field)
    assert 'cf_test' not in queries.query_leads(store, Query())['items'][0]
    assert presentation.field_value(store, lead['id'], 'cf_test', value, 0)['version'] == 1
    with pytest.raises(ValueError):
        presentation.field_value(store, lead['id'], 'cf_test', bad, 1)
    with pytest.raises(presentation.Conflict):
        presentation.field_value(store, lead['id'], 'cf_test', value, 0)
    assert queries.query_leads(store, Query(filters=[{'field':'cf_test','op':'eq','value':str(value) if typ=='text' else value}]))['total'] == 1


@pytest.mark.parametrize('payload', [
    {'op': 'run_sql', 'query':'DROP TABLE leads'}, {'op': 'dial', 'number':'+12025550141'},
    {'op': 'set_consent', 'lead_id':'x', 'consent':True}, {'op': 'set_html', 'html':'<script>alert(1)</script>'},
    {'op': 'edit_view', 'view_id':'all', 'data':[{'name':'Fabricated lead'}]},
    {'op': 'preferences', 'mode':'adaptive', 'default_view':'all', 'allow_structural_auto':True, 'api_key':'bad'},
])
def test_unknown_capabilities_and_model_authored_records_rejected(payload):
    with pytest.raises(ValidationError):
        Plan.model_validate({'reason':'Malicious payload rejection test', 'operations':[payload]})


def test_query_injection_literal_text_and_unknown_field(ws):
    store, _, _, _ = ws
    add_real_fixture(store)
    assert queries.query_leads(store, Query(search="%' OR 1=1 --"))['total'] == 0
    with pytest.raises(ValidationError):
        Query(filters=[{'field':'phone); DROP TABLE leads;--','value':'x'}])
    with pytest.raises(ValueError):
        queries.query_leads(store, Query(filters=[{'field':'cf_fake','value':'x'}]))
    assert len(store.all('leads')) == 1


def test_suppression_changes_eligibility_not_commercial_evidence(ws):
    store, _, _, new_worker = ws
    lead, _ = add_real_fixture(store)
    run_all(new_worker(), store)
    data = queries.lead_detail(store, lead['id'])
    store.suppress(lead['phone'], 'Operator suppression test')
    after = queries.lead_detail(store, lead['id'])
    assert after['eligibility'] == 'suppressed'
    assert after['assessment']['id'] == data['assessment']['id']
    assert after['assessment']['data']['potential'] == 'strong'
    assert after['priority'] == 'none'
    assert queries.aggregates(store, Query())['suppressed'] == 1


@pytest.mark.parametrize('phrase,anchor,zone,expected', [
    ('tomorrow at 10:00', '2026-09-17T23:30:00+00:00', 'Asia/Tokyo', '2026-09-19T01:00:00+00:00'),
    ('2026-11-01 at 01:30', '2026-10-30T12:00:00+00:00', 'America/New_York', None),
    ('2026-03-08 at 02:30', '2026-03-01T12:00:00+00:00', 'America/New_York', None),
    ('next Friday', '2026-09-17T12:00:00+00:00', 'UTC', None),
    ('tomorrow', '2026-09-17T12:00:00+00:00', 'UTC', None),
    ('tomorrow at 10:00', '2026-09-17T12:00:00', 'UTC', None),
    ('tomorrow at 10:00', '2026-09-17T12:00:00+00:00', None, None),
    ('tomorrow at 13:30 pm', '2026-09-17T12:00:00+00:00', 'UTC', None),
])
def test_dates_only_resolve_from_supported_call_time_and_timezone(phrase, anchor, zone, expected):
    assert intelligence.resolve_due(phrase, anchor, zone)[0] == expected


def test_task_state_survives_reanalysis_and_request_is_never_a_booking(ws):
    store, _, _, new_worker = ws
    lead, call = add_real_fixture(store)
    store.patch('calls', call['id'], requests=[{'type':'meeting','details':'Requested meeting, not booked','tool_call_id':'request-1'}])
    w = new_worker()
    assert w.tick()
    tasks = queries.lead_detail(store, lead['id'])['tasks']
    request = next(t for t in tasks if t['kind'] == 'meeting_request')
    assert request['status'] == 'needs_review'
    assert request['data']['nature'] == 'request_not_confirmed'
    task = next(t for t in tasks if t['kind'] == 'callback')
    intelligence.update_task(store, task['id'], version=1, status='done')
    head = queries.lead_detail(store, lead['id'])['head']
    intelligence.add_note(store, lead['id'], text='Additional unconfirmed operator context.', generation=head['generation'])
    assert w.tick()
    task_after = next(t for t in queries.lead_detail(store, lead['id'])['tasks'] if t['id'] == task['id'])
    assert task_after['status'] == 'done' and task_after['version'] == 2
    assert len(queries.lead_detail(store, lead['id'])['tasks']) == 2
    assert store.all('outbox') == []


def test_model_failure_retries_without_destroying_last_valid_workspace(ws):
    store, _, model, new_worker = ws
    lead, _ = add_real_fixture(store)
    def fail(*args):
        raise ModelFailure('Injected provider timeout')
    model.generate = fail
    w = new_worker()
    before = presentation.current(store)
    for _ in range(5):
        force_ready(store)
        w.tick()
    assert store.conn.execute('SELECT status FROM ws_jobs').fetchone()[0] == 'failed'
    assert queries.lead_detail(store, lead['id'])['assessment'] is None
    assert presentation.current(store) == before


def test_missing_key_and_daily_budget_keep_workspace_manual(ws):
    store, _, model, new_worker = ws
    add_real_fixture(store)
    model.available = False
    w = new_worker()
    assert w.tick()
    assert store.conn.execute('SELECT status FROM ws_jobs').fetchone()[0] == 'waiting_configuration'
    change(store, {'op':'edit_view','view_id':'today','name':'Still editable without model'})
    assert not model.requests
    model.available = True
    w.close()
    w = new_worker(workspace_daily_tokens=1)
    assert w.tick()
    assert store.conn.execute('SELECT status FROM ws_jobs').fetchone()[0] == 'retry'
    assert not model.requests


def test_restart_after_commit_before_finish_does_not_duplicate_intelligence(ws):
    store, _, _, new_worker = ws
    lead, _ = add_real_fixture(store)
    w = new_worker()
    assert w.tick()
    with store.lock, store.conn:
        store.conn.execute("UPDATE ws_jobs SET status='running'")
    w.close()
    w = new_worker()
    force_ready(store)
    w.tick()
    assert len(queries.lead_detail(store, lead['id'])['history']) == 1
    assert len(queries.lead_detail(store, lead['id'])['tasks']) == 1


def test_provider_schema_contract_is_closed_and_has_no_unsupported_oneof():
    for model in (Extraction, Plan):
        schema = strict_schema(model)
        def walk(node):
            if isinstance(node, dict):
                assert 'oneOf' not in node and 'discriminator' not in node and 'default' not in node
                if 'properties' in node:
                    assert node['additionalProperties'] is False
                    assert set(node['required']) == set(node['properties'])
                for value in node.values(): walk(value)
            elif isinstance(node, list):
                for value in node: walk(value)
        walk(schema)


@pytest.mark.parametrize('status,result,exception', [
    (401, {}, ModelUnavailable), (429, {}, ModelFailure),
    (200, {'status':'incomplete','output':[]}, ModelFailure),
    (200, {'status':'completed','output':[{'type':'message','content':[{'type':'refusal','refusal':'No'}]}]}, ModelFailure),
    (200, {'status':'completed','output':[{'type':'message','content':[{'type':'output_text','text':'{"reason":"x","operations":[],"dial":true}'}]}]}, ModelFailure),
])
def test_provider_failure_and_refusal_are_not_partial_writes(ws, status, result, exception):
    _, config, _, _ = ws
    captured = []
    def handler(request):
        captured.append(json.loads(request.content))
        assert str(request.url) == 'https://api.openai.com/v1/responses'
        return httpx.Response(status, json=result)
    model = ResponsesModel(replace(config, workspace_key='mock-key'), transport=httpx.MockTransport(handler))
    with pytest.raises(exception):
        model.generate('plan', {'operator_command':'test'}, Plan)
    assert captured[0]['store'] is False
    assert 'tools' not in captured[0] and 'stream' not in captured[0]
    assert captured[0]['text']['format']['strict'] is True


def test_provider_oversized_reply_is_bounded(ws):
    _, config, _, _ = ws
    transport = httpx.MockTransport(lambda _: httpx.Response(200, content=b'X'*520000))
    with pytest.raises(ModelFailure, match='limit'):
        ResponsesModel(replace(config, workspace_key='mock-key'), transport=transport).generate('plan', {}, Plan)


def test_http_auth_scope_and_protected_fields(tmp_path):
    c = Config(data_dir=tmp_path, admin_token=TOKEN, workspace_enabled=False)
    app = create_app(c)
    with TestClient(app, base_url='http://localhost:8080') as client:
        assert client.get('/api/workspace').status_code == 401
        client.headers['Authorization'] = f'Bearer {TOKEN}'
        state = client.get('/api/workspace').json()
        assert state['orchestrator']['configured'] is False
        assert client.post('/api/workspace/query', json={'view_id':'all','page_size':101}).status_code == 422
        assert client.post('/api/workspace/query', json={'view_id':'all','query':{'scope':'practice'}}).status_code == 422
        assert client.post('/api/workspace/changes', json={'base_version':1,'reason':'Injection test','operations':[], 'enable_outbound':True}).status_code == 422
        assert client.post('/api/workspace/commands', json={'text':'Do not call anyone','view_id':'all','base_version':1}).status_code == 503
        assert app.state.config.enable_outbound is False if hasattr(app.state, 'config') else c.enable_outbound is False


def test_segment_http_scope_revision_and_lookup_offset(tmp_path):
    app = create_app(Config(data_dir=tmp_path, admin_token=TOKEN))
    store = app.state.store
    lead, call = add_real_fixture(store)
    source = evidence.segments(store, call['id'])[0]
    other, _ = add_real_fixture(store, phone='+12025550143')
    with TestClient(app, base_url='http://localhost:8080', headers={'Authorization':f'Bearer {TOKEN}'}) as client:
        assert client.get(f"/api/workspace/segments/{source['id']}?lead_id={other['id']}").status_code == 404
        url = f"/api/workspace/segments/{source['id']}?lead_id={lead['id']}&call_id={call['id']}"
        result = client.get(url)
        assert result.status_code == 200 and result.json()['page_offset'] == 0
        stale = client.post(f"/api/workspace/segments/{source['id']}/correct", json={'revision':0,'text':'Stale correction','reason':'Operator test'})
        assert stale.status_code == 409
        assert client.post(f"/api/workspace/segments/{source['id']}/redact", json={'revision':2,'reason':'Operator test','confirm':False}).status_code == 422


def test_legacy_six_table_migration_is_idempotent_and_preserves_protected_records(tmp_path):
    path = tmp_path / 'legacy.sqlite3'
    conn = sqlite3.connect(path)
    conn.executescript('''CREATE TABLE leads(id TEXT PRIMARY KEY, phone TEXT UNIQUE, data TEXT NOT NULL);
        CREATE TABLE calls(id TEXT PRIMARY KEY, request_id TEXT UNIQUE, data TEXT NOT NULL);
        CREATE TABLE settings(key TEXT PRIMARY KEY,data TEXT NOT NULL);
        CREATE TABLE suppression(phone TEXT PRIMARY KEY,data TEXT NOT NULL);
        CREATE TABLE tools(key TEXT PRIMARY KEY,data TEXT NOT NULL);
        CREATE TABLE outbox(id TEXT PRIMARY KEY,data TEXT NOT NULL);''')
    lead = {'id':'lead_old','name':'Legacy fixture','phone':'+12025550144','company':'Legacy test','timezone':'UTC',
            'notes':'Existing human context','sample':False,'consent':True,'consent_note':'Existing assertion',
            'created_at':now_iso(),'status':'new','opted_out':True}
    call = {'id':'call_old','lead_id':lead['id'],'kind':'twilio','status':'completed','created_at':now_iso(),
            'ended_at':now_iso(),'requests':[{'type':'meeting','details':'Request only'}],
            'transcript':[{'role':'lead','text':'legacy','event_id':'legacy1'}], 'summary':'Existing summary'}
    conn.execute('INSERT INTO leads VALUES(?,?,?)', (lead['id'],lead['phone'],json.dumps(lead)))
    conn.execute('INSERT INTO calls VALUES(?,?,?)', (call['id'],'request_old',json.dumps(call)))
    conn.execute('INSERT INTO suppression VALUES(?,?)', (lead['phone'],json.dumps({'phone':lead['phone'],'reason':'Existing permanent suppression'})))
    conn.execute('INSERT INTO tools VALUES(?,?)', ('tool_old',json.dumps({'status':'recorded'})))
    conn.execute('INSERT INTO outbox VALUES(?,?)', ('outbox_old',json.dumps({'id':'outbox_old','status':'pending_review'})))
    conn.commit(); conn.close()
    store = Store(path)
    assert store.get('leads', lead['id']) == lead
    assert store.get('calls', call['id'])['summary'] == 'Existing summary'
    assert store.get('calls', call['id'])['transcript'][0]['text'] == 'legacy'
    assert store.suppressed(lead['phone'])
    assert store.tool_result('tool_old') == {'status':'recorded'}
    assert store.get('outbox','outbox_old')['status'] == 'pending_review'
    assert evidence.metadata(store, call['id'])['status'] == 'legacy_unverified'
    assert store.all('calls')[0]['transcript'] == []
    assert json.loads(store.conn.execute('SELECT data FROM calls').fetchone()[0])['transcript'] == []
    before = evidence.metadata(store, call['id'])
    migrations.migrate(store)
    assert evidence.metadata(store, call['id']) == before
    assert len(queries.lead_detail(store, lead['id'])['notes']) == 1
    store.close()
