"""Scoped, bounded, parameterized queries. No model-supplied SQL or record arrays."""
from __future__ import annotations

import json
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
from .schema import Query, SORTS
from .intelligence import eligibility, priority
from .presentation import current, view_by_id
from .evidence import metadata, segments

PAGE_LIMIT = 100


def json_rows(rows):
    return [dict(r) | {'data': json.loads(r['data'])} for r in rows]


def effective_query(store, view_id, override=None):
    view = view_by_id(current(store)['spec'], view_id)
    return Query.model_validate(override if override is not None else view['query'])


def compile_query(store, query: Query):
    """Return a fixed SQL projection, predicates, and bound arguments.

    Day boundaries are in the operator workspace timezone (Africa/Cairo by
    default), while due_at values are UTC. Permission recorded is not preflight.
    """
    tz = ZoneInfo(store.get_setting('ws_timezone') or 'UTC')
    now = datetime.now(timezone.utc)
    tomorrow = (now.astimezone(tz).replace(hour=0, minute=0, second=0, microsecond=0)
                + timedelta(days=1)).astimezone(timezone.utc).isoformat()
    now_text = now.isoformat()
    base = '''
    WITH base AS (
      SELECT l.id,l.data,li.name,li.company,li.sample,li.status,li.created_at,
        h.generation,h.assessed_generation,h.status AS analysis_status,
        a.data AS assessment,a.id AS assessment_version,
        CASE WHEN li.sample=1 THEN 'practice_only'
             WHEN s.phone IS NOT NULL OR json_extract(l.data,'$.opted_out')=1 THEN 'suppressed'
             WHEN li.consent=0 OR coalesce(json_extract(l.data,'$.consent_note'),'')='' THEN 'permission_missing'
             ELSE 'permission_recorded' END AS eligibility
      FROM leads l JOIN ws_lead_index li ON li.lead_id=l.id
      LEFT JOIN suppression s ON s.phone=li.phone
      LEFT JOIN ws_heads h ON h.lead_id=l.id
      LEFT JOIN ws_assessments a ON a.id=h.assessment_version
      WHERE li.sample=?
    ), scored AS (
      SELECT base.*,
        coalesce(json_extract(assessment,'$.potential'),'unassessed') AS potential,
        coalesce(json_extract(assessment,'$.confidence'),'unknown') AS confidence,
        coalesce(json_extract(assessment,'$.stage'),'unassessed') AS stage,
        json_extract(assessment,'$.assessed_at') AS assessment_at,
        coalesce(json_extract(assessment,'$.awaiting_proposal'),0) AS awaiting_proposal,
        coalesce(json_extract(assessment,'$.procurement'),0) AS procurement,
        coalesce(json_extract(assessment,'$.needs_decision'),0) AS needs_decision,
        EXISTS(SELECT 1 FROM ws_tasks t WHERE t.lead_id=base.id AND t.status IN ('open','waiting','needs_review','proposed')) AS has_tasks,
        CASE WHEN EXISTS(SELECT 1 FROM ws_tasks t WHERE t.lead_id=base.id AND t.status IN ('open','waiting','needs_review','proposed')
                AND t.due_at IS NOT NULL AND t.due_at < ? AND (t.kind!='callback' OR base.eligibility='permission_recorded')) THEN 'overdue'
             WHEN EXISTS(SELECT 1 FROM ws_tasks t WHERE t.lead_id=base.id AND t.status IN ('open','waiting','needs_review','proposed')
                AND t.due_at IS NOT NULL AND t.due_at < ? AND (t.kind!='callback' OR base.eligibility='permission_recorded')) THEN 'today'
             WHEN json_array_length(json_extract(assessment,'$.conflicts'))>0 OR json_extract(assessment,'$.needs_decision')=1
                OR EXISTS(SELECT 1 FROM ws_tasks t WHERE t.lead_id=base.id AND t.status IN ('needs_review','proposed')
                AND (t.kind!='callback' OR base.eligibility='permission_recorded')) THEN 'review'
             WHEN EXISTS(SELECT 1 FROM ws_tasks t WHERE t.lead_id=base.id AND t.status IN ('open','waiting') AND t.due_at IS NOT NULL
                AND (t.kind!='callback' OR base.eligibility='permission_recorded')) THEN 'later'
             WHEN base.eligibility='permission_recorded' AND (assessment IS NULL OR json_extract(assessment,'$.potential')='unassessed') THEN 'qualify'
             ELSE 'none' END AS priority,
        CASE WHEN analysis_status IN ('failed','waiting_configuration') OR generation>assessed_generation AND assessment IS NOT NULL
             OR json_array_length(json_extract(assessment,'$.conflicts'))>0
             OR json_extract(assessment,'$.coverage.all_chunks_processed')=0 THEN 1 ELSE 0 END AS needs_review,
        coalesce(json_extract(assessment,'$.unknowns'),'[]') AS unknowns,
        coalesce(json_extract(assessment,'$.objections'),'[]') AS objection,
        coalesce((SELECT json_extract(t.data,'$.wording') FROM ws_tasks t WHERE t.lead_id=base.id
          AND t.status IN ('open','waiting','needs_review','proposed') ORDER BY t.due_at IS NULL,t.due_at,t.created_at LIMIT 1),'') AS next_action
      FROM base
    ), projected AS (
      SELECT scored.*,
        CASE potential WHEN 'strong' THEN 4 WHEN 'promising' THEN 3 WHEN 'developing' THEN 2 WHEN 'limited' THEN 1 ELSE 0 END AS potential_rank,
        CASE priority WHEN 'overdue' THEN 5 WHEN 'today' THEN 4 WHEN 'review' THEN 3 WHEN 'qualify' THEN 2 WHEN 'later' THEN 1 ELSE 0 END AS priority_rank,
        priority IN ('overdue','today','review') AS due_today
      FROM scored
    )
    '''
    params = [int(query.scope == 'practice'), now_text, tomorrow]
    conditions = []
    fields = {'name', 'company', 'potential', 'priority', 'confidence', 'eligibility', 'stage',
              'assessment_at', 'next_action', 'status', 'needs_review', 'awaiting_proposal',
              'procurement', 'needs_decision', 'has_tasks', 'due_today', 'unknowns', 'objection'}
    if query.search:
        conditions.append("(name LIKE ? ESCAPE '\\' OR company LIKE ? ESCAPE '\\' OR json_extract(data,'$.phone') LIKE ? ESCAPE '\\')")
        params.extend([like(query.search)] * 3)
    for item in query.filters:
        if item.field in fields:
            expr = item.field
        elif item.field.startswith('cf_'):
            if not store.conn.execute('SELECT 1 FROM ws_fields WHERE id=?', (item.field,)).fetchone():
                raise ValueError('Unknown custom field.')
            expr = '(SELECT json_extract(v.data,\'$\') FROM ws_values v WHERE v.lead_id=projected.id AND v.field_id=?)'
            params.append(item.field)
        else:
            raise ValueError('Unsupported filter.')
        if item.op == 'unknown':
            conditions.append(f"({expr} IS NULL OR {expr} IN ('','unknown','unassessed'))")
            if item.field.startswith('cf_'):
                params.append(item.field)
        elif item.op == 'in':
            values = item.value
            if not values:
                conditions.append('0')
                if item.field.startswith('cf_'):
                    params.pop()
            else:
                conditions.append(f'{expr} IN ({",".join("?" for _ in values)})')
                params.extend(values)
        elif item.op == 'contains':
            if not isinstance(item.value, str):
                raise ValueError('contains requires text.')
            conditions.append(f"{expr} LIKE ? ESCAPE '\\'")
            params.append(like(item.value))
        elif item.value is None:
            conditions.append(f'{expr} IS NULL')
        else:
            if isinstance(item.value, list):
                raise ValueError('eq requires a scalar.')
            conditions.append(f'{expr}=?')
            params.append(item.value)
    where = ' WHERE ' + ' AND '.join(conditions) if conditions else ''
    return base, where, params


def like(text):
    return '%' + text.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_') + '%'


def query_leads(store, query: Query, *, page=1, page_size=25):
    if page < 1 or not 1 <= page_size <= PAGE_LIMIT or page > 100000:
        raise ValueError('Invalid page bounds.')
    base, where, params = compile_query(store, query)
    total = store.conn.execute(base + 'SELECT count(*) FROM projected' + where, params).fetchone()[0]
    order = {'potential': 'potential_rank', 'priority': 'priority_rank'}.get(query.sort, query.sort)
    if query.sort not in SORTS:
        raise ValueError('Unsupported ordering.')
    prefix = f'{query.group} ASC,' if query.group != 'none' else ''
    rows = store.conn.execute(base + 'SELECT * FROM projected' + where +
                              f' ORDER BY {prefix}{order} {query.direction},id ASC LIMIT ? OFFSET ?',
                              (*params, page_size, (page - 1) * page_size)).fetchall()
    result = []
    for row in rows:
        obj = {key: row[key] for key in ('id', 'name', 'company', 'potential', 'priority', 'confidence', 'eligibility',
                                        'stage', 'assessment_at', 'next_action', 'analysis_status', 'needs_review',
                                        'assessment_version', 'generation', 'assessed_generation')}
        obj['stale'] = row['assessment'] is not None and row['generation'] > row['assessed_generation']
        custom = store.conn.execute('SELECT field_id,data FROM ws_values WHERE lead_id=?', (row['id'],)).fetchall()
        obj.update({v['field_id']: json.loads(v['data']) for v in custom})
        result.append(obj)
    return {'items': result, 'total': total, 'page': page, 'page_size': page_size,
            'has_more': page * page_size < total, 'definition': query.model_dump(), 'scope': query.scope}


def aggregates(store, query):
    base, where, params = compile_query(store, query)
    row = store.conn.execute(base + '''SELECT count(*) AS total,
        coalesce(sum(potential IN ('promising','strong')),0) AS promising,
        coalesce(sum(priority IN ('today','overdue')),0) AS due,
        coalesce(sum(needs_review),0) AS review,
        coalesce(sum(eligibility='suppressed'),0) AS suppressed,
        coalesce(sum(potential='unassessed'),0) AS unassessed FROM projected''' + where, params).fetchone()
    stages = store.conn.execute(base + 'SELECT stage,count(*) AS count FROM projected' + where + ' GROUP BY stage', params).fetchall()
    objections = store.conn.execute(base + '''SELECT j.value ->> '$.text' AS text, count(*) AS count
        FROM projected,json_each(projected.objection) j''' + where +
        ''' GROUP BY text ORDER BY count DESC LIMIT 10''', params).fetchall()
    return dict(row) | {'stages': [dict(r) for r in stages], 'objections': [dict(r) for r in objections],
                        'scope': query.scope, 'source': 'authorized_database_query'}


def tasks_for_query(store, query, *, page=1, page_size=50):
    if not 1 <= page <= 100000 or not 1 <= page_size <= PAGE_LIMIT:
        raise ValueError('Invalid page bounds.')
    base, where, params = compile_query(store, query)
    filtered = base + ', selected AS (SELECT * FROM projected' + where + ') '
    rows = store.conn.execute(filtered + '''SELECT t.*,p.name,p.company,p.eligibility FROM ws_tasks t
      JOIN selected p ON p.id=t.lead_id ORDER BY t.status IN ('done','cancelled'),t.due_at IS NULL,t.due_at,t.created_at DESC
      LIMIT ? OFFSET ?''', (*params, page_size, (page - 1) * page_size)).fetchall()
    total = store.conn.execute(filtered + 'SELECT count(*) FROM ws_tasks t JOIN selected p ON p.id=t.lead_id', params).fetchone()[0]
    return {'items': json_rows(rows), 'total': total, 'has_more': page * page_size < total}


def calls_for_query(store, query, *, page=1, page_size=25):
    if not 1 <= page <= 100000 or not 1 <= page_size <= PAGE_LIMIT:
        raise ValueError('Invalid page bounds.')
    if query.scope == 'practice':
        params = []
        predicate = "ci.kind!='twilio'"
        if query.search:
            predicate += " AND (coalesce(li.name,'') LIKE ? ESCAPE '\\' OR coalesce(li.company,'') LIKE ? ESCAPE '\\')"
            params += [like(query.search)] * 2
        # Practice has no real commercial assessment. Only supported practice record filters apply.
        if query.filters:
            base, where, filter_params = compile_query(store, query)
            prefix = base + ', selected AS (SELECT * FROM projected' + where + ') '
            predicate += ' AND ci.lead_id IN (SELECT id FROM selected)'
            params = filter_params + params
        else:
            prefix = ''
        rows = store.conn.execute(prefix + '''SELECT ci.*,li.name,li.company,cap.segment_count,cap.dropped,cap.close_observed
          FROM ws_call_index ci LEFT JOIN ws_lead_index li ON li.lead_id=ci.lead_id
          JOIN ws_capture cap ON cap.call_id=ci.call_id WHERE ''' + predicate +
          ' ORDER BY ci.created_at DESC,ci.call_id LIMIT ? OFFSET ?', (*params, page_size + 1, (page-1)*page_size)).fetchall()
        return {'items': [dict(r) for r in rows[:page_size]], 'page': page, 'has_more': len(rows) > page_size}
    base, where, params = compile_query(store, query)
    filtered = base + ', selected AS (SELECT * FROM projected' + where + ') '
    scope = "ci.kind!='twilio'" if query.scope == 'practice' else "ci.kind='twilio'"
    extra = " OR ci.lead_id IS NULL AND ci.kind!='twilio'" if query.scope == 'practice' and not query.search and not query.filters else ''
    rows = store.conn.execute(filtered + f'''SELECT ci.*,p.name,p.company,cap.segment_count,cap.dropped,cap.close_observed
      FROM ws_call_index ci LEFT JOIN selected p ON p.id=ci.lead_id JOIN ws_capture cap ON cap.call_id=ci.call_id
      WHERE (p.id IS NOT NULL AND {scope}){extra} ORDER BY ci.created_at DESC LIMIT ? OFFSET ?''',
      (*params, page_size, (page - 1) * page_size)).fetchall()
    return {'items': [dict(r) for r in rows], 'page': page, 'has_more': len(rows) == page_size}


def lead_detail(store, lead_id):
    lead = store.get('leads', lead_id)
    if not lead:
        raise KeyError(lead_id)
    head = dict(store.conn.execute('SELECT * FROM ws_heads WHERE lead_id=?', (lead_id,)).fetchone())
    row = store.conn.execute('SELECT * FROM ws_assessments WHERE id=?', (head['assessment_version'],)).fetchone()
    assessment = dict(row) | {'data': json.loads(row['data'])} if row else None
    notes = [dict(r) for r in store.conn.execute('SELECT * FROM ws_notes WHERE lead_id=? ORDER BY created_at', (lead_id,))]
    tasks = json_rows(store.conn.execute('SELECT * FROM ws_tasks WHERE lead_id=? ORDER BY created_at DESC LIMIT 200', (lead_id,)))
    eligible = eligibility(store, lead)
    rank, reason = priority(tasks, eligible, assessment['data'] if assessment else None, zone=store.get_setting('ws_timezone') or 'UTC')
    calls = [dict(r) for r in store.conn.execute('SELECT ci.*,cap.segment_count,cap.dropped,cap.close_observed '
              'FROM ws_call_index ci JOIN ws_capture cap ON ci.call_id=cap.call_id '
              'WHERE ci.lead_id=? ORDER BY ci.created_at DESC LIMIT 50', (lead_id,))]
    history = [dict(r) for r in store.conn.execute("SELECT id,generation,created_at,model,rubric_version,"
             "json_extract(data,'$.potential') AS potential FROM ws_assessments WHERE lead_id=? ORDER BY id DESC LIMIT 20", (lead_id,))]
    values = {r['field_id']: {'version': r['version'], 'value': json.loads(r['data'])} for r in store.conn.execute(
        'SELECT * FROM ws_values WHERE lead_id=?', (lead_id,))}
    return {'lead': lead, 'head': head, 'assessment': assessment, 'notes': notes, 'tasks': tasks,
            'task_limit': 200, 'calls': calls, 'call_limit': 50, 'history': history,
            'eligibility': eligible, 'priority': rank, 'priority_reason': reason,
            'custom_values': values, 'stale': bool(assessment and head['generation'] != head['assessed_generation'])}


def call_detail(store, call_id, *, offset=0, limit=100, include_replaced=False):
    call = store.get('calls', call_id, include_transcript=False)
    if not call:
        raise KeyError(call_id)
    call.pop('transcript', None)
    cap = metadata(store, call_id)
    items = segments(store, call_id, offset=offset, limit=limit, include_replaced=include_replaced)
    tools = [dict(r) | {'data': json.loads(r['data'])} for r in store.conn.execute(
        "SELECT created_at,kind,summary,data FROM ws_audit WHERE subject=? AND kind='tool_result' ORDER BY id LIMIT 200", (call_id,))]
    count = store.conn.execute('SELECT count(*) FROM ws_segments WHERE call_id=?' +
                              ('' if include_replaced else ' AND active=1'), (call_id,)).fetchone()[0]
    return {'call': call, 'capture': cap, 'segments': items, 'total_segments': count,
            'offset': offset, 'has_more': offset + len(items) < count, 'tool_results': tools,
            'readable_note': 'Consecutive channel fragments, not verified turns. Unknown timing stays unknown.'}
