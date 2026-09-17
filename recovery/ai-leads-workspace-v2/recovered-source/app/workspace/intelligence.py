"""Evidence validation and reproducible ranking. The model does not supply scores."""
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from ..db import now_iso, uid
from .evidence import resolve_reference, dirty_lead
from .presentation import audit, Conflict
from .schema import Extraction

RUBRIC_TOPICS = ('need', 'fit', 'intent', 'authority')
POTENTIAL_ORDER = {'unassessed': 0, 'limited': 1, 'developing': 2, 'promising': 3, 'strong': 4}
PRIORITY_ORDER = {'none': 0, 'later': 1, 'qualify': 2, 'review': 3, 'today': 4, 'overdue': 5}
OPEN_TASKS = ('open', 'needs_review', 'waiting', 'proposed')


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def validate_extraction(store, lead_id, call_id, revision, result, sources):
    """Exact matching provides provenance, not proof that semantic interpretation is correct."""
    parsed = Extraction.model_validate(result).model_dump()
    source_map = {s['source_id']: s for s in sources}
    claims, commitments = [], []
    if not parsed['conversation'] and (parsed['claims'] or parsed['commitments']):
        raise ValueError('No-conversation extraction cannot contain qualification or commitments.')
    for claim in parsed['claims']:
        refs = [resolve_reference(ref, source_map, lead_id=lead_id, store=store) for ref in claim['references']]
        claim['references'] = refs
        claim['call_id'] = call_id
        claim['source_revision'] = revision
        claim['id'] = 'fact_' + digest({'call_id': call_id, 'topic': claim['topic'], 'value': claim['value'],
                                      'references': refs, 'text': claim['text']})[:32]
        claims.append(claim)
    for commitment in parsed['commitments']:
        ref = resolve_reference(commitment['reference'], source_map, lead_id=lead_id, store=store)
        if commitment['wording'] not in commitment['reference']['quote']:
            raise ValueError('Commitment wording must be an exact supported quote.')
        if commitment['date_phrase'] and commitment['date_phrase'].casefold() not in commitment['reference']['quote'].casefold():
            raise ValueError('Date phrase must appear in the supporting quote.')
        commitment['reference'] = ref
        commitment['call_id'] = call_id
        commitments.append(commitment)
    return {'conversation': parsed['conversation'], 'claims': claims, 'commitments': commitments,
            'questions': [{'text': q[:500], 'status': 'recommended_question_not_source'} for q in parsed['questions']]}


def resolve_due(phrase: str, call_time: str | None, zone: str | None):
    """Conservative dates: ISO dates and today/tomorrow with an explicit clock time.

    No guessing next Friday, next week, ambiguous numeric dates, DST folds, or a
    timezone from the server. Date-only phrases require clarification rather than
    inventing a time of day. Human task edits can resolve the ambiguity.
    """
    if not phrase:
        return None, 'unspecified'
    if not call_time or not zone:
        return None, 'timezone_or_call_time_missing'
    try:
        tz = ZoneInfo(zone)
        anchor = datetime.fromisoformat(call_time)
        if anchor.tzinfo is None:
            return None, 'call_time_has_no_offset'
        local = anchor.astimezone(tz)
        normalized = phrase.strip().casefold()
        match = re.fullmatch(r'(today|tomorrow|\d{4}-\d{2}-\d{2})(?: at)? (\d{1,2}):(\d{2})(?:\s*(am|pm))?', normalized)
        if not match:
            return None, 'ambiguous_date_requires_review'
        day, hours, minutes, period = match.groups()
        if day in ('today', 'tomorrow'):
            day_value = local.date() + timedelta(days=day == 'tomorrow')
        else:
            day_value = datetime.strptime(day, '%Y-%m-%d').date()
        hour, minute = int(hours), int(minutes)
        if period:
            if not 1 <= hour <= 12:
                return None, 'invalid_clock_time'
            hour = hour % 12 + (12 if period == 'pm' else 0)
        candidate = datetime(day_value.year, day_value.month, day_value.day, hour, minute, tzinfo=tz)
        if candidate.replace(fold=0).utcoffset() != candidate.replace(fold=1).utcoffset():
            return None, 'ambiguous_daylight_saving_time'
        if candidate.astimezone(timezone.utc).astimezone(tz).replace(tzinfo=None) != candidate.replace(tzinfo=None):
            return None, 'nonexistent_local_time'
        return candidate.astimezone(timezone.utc).isoformat(), 'resolved_from_source'
    except (ValueError, ZoneInfoNotFoundError):
        return None, 'invalid_date_or_timezone'


def compute_assessment(claims, notes, rubric, *, usable_calls, coverage, previous=None):
    criteria, conflicts, refs = {}, [], []
    for topic in RUBRIC_TOPICS:
        related = [c for c in claims if c['topic'] == topic]
        explicit = {c['value'] for c in related if c['interpretation'] == 'explicit' and c['value'] != 'unknown'}
        overrides = [n for n in notes if n['confirmed'] and n['topic'] == topic and n['active']]
        override = overrides[-1] if overrides else None
        if override:
            value = override['value']
            if explicit - {value}:
                conflicts.append({'topic': topic, 'reason': 'New evidence conflicts with a confirmed human correction.',
                                  'human_note_id': override['id'], 'claim_ids': [c['id'] for c in related]})
            source = 'human_confirmed'
        elif len(explicit) > 1:
            value, source = 'unknown', 'conflicting_evidence'
            conflicts.append({'topic': topic, 'reason': 'Contradictory evidence retained; clarification required.',
                              'claim_ids': [c['id'] for c in related]})
        else:
            value = next(iter(explicit), 'unknown')
            source = 'extracted_evidence' if explicit else 'unknown'
        criteria[topic] = {'value': value, 'source': source, 'claim_ids': [c['id'] for c in related],
                           'human_note_id': override['id'] if override else None}
        refs.extend(c['id'] for c in related)
    known = sum(c['value'] != 'unknown' for c in criteria.values())
    points = sum(rubric['criteria'][k] for k, c in criteria.items() if c['value'] == 'yes')
    approved = rubric['approved']
    if not approved or usable_calls == 0 or known < 2:
        potential = 'unassessed'
    elif criteria['fit']['value'] == 'no':
        potential = 'limited'
    elif criteria['need']['value'] == criteria['fit']['value'] == 'yes':
        potential = 'strong' if criteria['intent']['value'] == criteria['authority']['value'] == 'yes' else 'promising'
    else:
        potential = 'developing'
    confidence = 'unknown' if not claims else ('well_supported' if known == 4 and not conflicts and coverage['all_chunks_processed']
                                              else 'partial' if known > 1 else 'limited')
    unknowns = [f'{k.replace("_", " ").capitalize()} is unknown' for k, c in criteria.items() if c['value'] == 'unknown']
    if not any(c['topic'] == 'budget' and c['value'] != 'unknown' for c in claims):
        unknowns.append('Budget is unknown; it is not zero')
    if not approved:
        unknowns.insert(0, 'Sales rubric needs operator approval; potential remains unassessed')
    if not coverage['all_chunks_processed']:
        unknowns.insert(0, 'Analysis coverage is partial; some captured text has not been analyzed')
    if not coverage['transcript_certified_complete']:
        unknowns.append('Capture is not a certified complete transcript of everything spoken')
    yes_topics = {c['topic'] for c in claims if c['value'] == 'yes' and c['interpretation'] == 'explicit'}
    stage = 'unassessed' if not claims else ('proposal' if 'proposal' in yes_topics else
             'decision' if 'decision_needed' in yes_topics else 'engaged' if 'intent' in yes_topics else 'qualification')
    return {'potential': potential, 'evidence_points': points, 'points_label': 'Rubric evidence points, not win probability',
            'criteria': criteria, 'confidence': confidence, 'coverage': coverage, 'stage': stage,
            'conflicts': conflicts, 'unknowns': unknowns, 'claim_ids': list(dict.fromkeys(refs)),
            'awaiting_proposal': 'proposal' in yes_topics, 'procurement': 'procurement' in yes_topics,
            'needs_decision': 'decision_needed' in yes_topics,
            'objections': [c for c in claims if c['topic'] == 'objection'],
            'claims': claims, 'previous_assessment_id': previous, 'rubric_version': rubric['version'],
            'rubric_approved': approved, 'assessed_at': now_iso()}


def eligibility(store, lead):
    if lead.get('sample'):
        return 'practice_only'
    if lead.get('opted_out') or store.suppressed(lead['phone']):
        return 'suppressed'
    if not lead.get('consent') or not lead.get('consent_note'):
        return 'permission_missing'
    return 'permission_recorded'  # NOT a preflight result or authorization to dial.


def priority(tasks, eligible, assessment, *, now=None):
    now = now or datetime.now(timezone.utc)
    active = [t for t in tasks if t['status'] in OPEN_TASKS]
    actionable = [t for t in active if t['kind'] != 'callback' or eligible == 'permission_recorded']
    overdue, today, future = [], [], []
    for task in actionable:
        if task.get('due_at'):
            due = datetime.fromisoformat(task['due_at'])
            if due < now:
                overdue.append(task)
            elif due.date() == now.date():
                today.append(task)
            else:
                future.append(task)
    if overdue:
        return 'overdue', 'A recorded internal commitment is overdue; no outreach has been performed.'
    if today:
        return 'today', 'A recorded internal commitment is due today (UTC display reference).'
    if assessment and (assessment.get('conflicts') or assessment.get('needs_decision')):
        return 'review', 'A human decision or evidence conflict needs review.'
    if any(t['status'] in ('needs_review', 'proposed') for t in actionable):
        return 'review', 'A date or recommended action requires human review.'
    if future:
        return 'later', 'Future commitments are not immediately due.'
    if eligible in ('suppressed', 'permission_missing', 'practice_only'):
        return 'none', 'No permitted callback is actionable; contact eligibility remains separate from potential.'
    if not assessment or assessment['potential'] == 'unassessed':
        return 'qualify', 'Not enough supported information to assess this lead.'
    return 'none', 'No immediate recorded commitment.'


def upsert_tasks(store, lead, commitments, calls, *, questions):
    """Model may create internal work, never complete it or execute communications."""
    now = now_iso()
    for item in commitments:
        call = calls.get(item['call_id'], {})
        reference = item['reference']
        key = 'commitment:' + digest({'call_id': item['call_id'], 'quote': reference['quote'],
                                      'party': item['party'], 'kind': item['kind']})
        due, resolution = resolve_due(item['date_phrase'], call.get('created_at'), call.get('lead_timezone'))
        status = 'open' if due else 'needs_review'
        data = {'wording': item['wording'], 'reference': reference, 'date_phrase': item['date_phrase'],
                'date_resolution': resolution, 'nature': 'extracted_commitment',
                'review_note': 'Source-backed extraction; verify agreement in context.',
                'execution': 'internal_only', 'source_active': True}
        ident = 'task_' + digest(key)[:32]
        store.conn.execute('INSERT OR IGNORE INTO ws_tasks VALUES(?,?,?,?,?,?,?,?,?,?,?,1)',
                           (ident, lead['id'], item['call_id'], key, item['kind'], item['party'], status,
                            due, now, now, json.dumps(data)))
    for call_id, call in calls.items():
        for n, request in enumerate(call.get('requests', [])):
            key = f"request:{call_id}:{request.get('tool_call_id', n)}"
            data = {'wording': request.get('details', ''), 'nature': 'request_not_confirmed',
                    'reference': {'call_id': call_id, 'request_id': request.get('tool_call_id', str(n))},
                    'date_phrase': '', 'date_resolution': 'needs_human_confirmation', 'execution': 'internal_only',
                    'source_active': True}
            kind = 'meeting_request' if request.get('type') == 'meeting' else 'callback'
            store.conn.execute('INSERT OR IGNORE INTO ws_tasks VALUES(?,?,?,?,?,?,?,?,?,?,?,1)',
                               ('task_' + digest(key)[:32], lead['id'], call_id, key, kind, 'operator', 'needs_review',
                                None, now, now, json.dumps(data)))
    if questions:
        key = f"recommendation:{lead['id']}:qualification"
        data = {'wording': 'Review unresolved questions before planning further contact.',
                'nature': 'recommendation_not_agreement', 'reference': None,
                'date_phrase': '', 'date_resolution': 'unspecified', 'execution': 'internal_only',
                'source_active': True}
        store.conn.execute('INSERT OR IGNORE INTO ws_tasks VALUES(?,?,?,?,?,?,?,?,?,?,?,1)',
                           ('task_' + digest(key)[:32], lead['id'], None, key, 'information', 'operator', 'proposed',
                            None, now, now, json.dumps(data)))


def add_note(store, lead_id, *, text, topic='note', value='unknown', confirmed=False, supersedes=None, generation):
    if topic not in (*RUBRIC_TOPICS, 'note', 'timing', 'objection'):
        raise ValueError('Unsupported correction topic.')
    if value not in ('yes', 'no', 'unknown') or not isinstance(text, str) or not 1 <= len(text.strip()) <= 5000:
        raise ValueError('Invalid note.')
    with store.lock, store.conn:
        head = store.conn.execute('SELECT generation FROM ws_heads WHERE lead_id=?', (lead_id,)).fetchone()
        if not head:
            raise ValueError('Lead not found.')
        if head['generation'] != generation:
            raise Conflict('Lead evidence changed; refresh before recording a correction.')
        if supersedes:
            old = store.conn.execute('SELECT lead_id FROM ws_notes WHERE id=? AND active=1', (supersedes,)).fetchone()
            if not old or old['lead_id'] != lead_id:
                raise ValueError('Prior note does not belong to this lead.')
            store.conn.execute('UPDATE ws_notes SET active=0 WHERE id=?', (supersedes,))
        ident = uid('note')
        store.conn.execute('INSERT INTO ws_notes VALUES(?,?,?,?,?,?,?,?,1)',
                           (ident, lead_id, topic, value, text.strip(), bool(confirmed), now_iso(), supersedes))
        dirty_lead(store, lead_id)
        audit(store, 'human', 'correction' if confirmed else 'note', lead_id,
              'Confirmed human correction retained' if confirmed else 'Human note added', {'note_id': ident, 'topic': topic})
        return {'id': ident, 'generation': generation + 1}


def update_task(store, ident, *, version, status, due_at=None):
    if status not in ('open', 'needs_review', 'waiting', 'proposed', 'done', 'cancelled'):
        raise ValueError('Invalid task state.')
    if due_at:
        parsed = datetime.fromisoformat(due_at)
        if parsed.tzinfo is None:
            raise ValueError('Due date requires an explicit UTC offset.')
        due_at = parsed.astimezone(timezone.utc).isoformat()
    with store.lock, store.conn:
        row = store.conn.execute('SELECT * FROM ws_tasks WHERE id=?', (ident,)).fetchone()
        if not row:
            raise ValueError('Task not found.')
        if row['version'] != version:
            raise Conflict('Task changed; refresh first.')
        data = json.loads(row['data'])
        if due_at:
            data['date_resolution'] = 'human_confirmed'
        data['last_human_action'] = now_iso()
        store.conn.execute('UPDATE ws_tasks SET status=?,due_at=?,updated_at=?,data=?,version=version+1 WHERE id=?',
                           (status, due_at or row['due_at'], now_iso(), json.dumps(data), ident))
        audit(store, 'human', 'task', row['lead_id'], f'Internal task marked {status}; no message, booking, or call executed.',
              {'task_id': ident})
        return {'id': ident, 'version': version + 1, 'status': status}
