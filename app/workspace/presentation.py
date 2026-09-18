"""Atomic, version-checked presentation operations shared by humans and the agent."""
from __future__ import annotations

import copy
import json
from ..db import now_iso, uid
from .schema import (Workspace, ChangeSet, FieldDefinition, default_workspace, COLS,
                     Query, Widget, View, Layouts)


class Conflict(ValueError):
    """The caller must refresh; no changes were published."""


class Locked(ValueError):
    pass


def audit(store, actor, kind, subject, summary, data=None):
    store.conn.execute('INSERT INTO ws_audit(created_at,actor,kind,subject,summary,data) VALUES(?,?,?,?,?,?)',
                       (now_iso(), actor, kind, subject, summary[:500], json.dumps(data or {})))


def initialize(store):
    with store.lock, store.conn:
        if not store.conn.execute('SELECT 1 FROM ws_workspace').fetchone():
            spec = default_workspace().model_dump_json()
            store.conn.execute('INSERT INTO ws_workspace VALUES(1,1,?)', (spec,))
            store.conn.execute('INSERT INTO ws_revisions VALUES(1,?,?,?,?)',
                               ('system', 'Initial workspace', now_iso(), spec))
        if store.get_setting('ws_rubric') is None:
            store.setting('ws_rubric', {'version': 1, 'approved': False,
                                      'criteria': {'need': 3, 'fit': 3, 'intent': 2, 'authority': 2},
                                      'description': 'Evidence of a problem, approved product fit, explicit buying intent, '
                                                     'and access to the decision maker. Not a closing probability.'})
        if store.get_setting('ws_paused') is None:
            store.setting('ws_paused', False)


def current(store):
    row = store.conn.execute('SELECT version,data FROM ws_workspace WHERE singleton=1').fetchone()
    return {'version': row['version'], 'spec': json.loads(row['data'])}


def view_by_id(spec, ident):
    for view in spec['views']:
        if view['id'] == ident:
            return view
    raise ValueError('View does not exist.')


def validate_fields(store, spec):
    known = {r['id'] for r in store.conn.execute('SELECT id FROM ws_fields')}
    for view in spec['views']:
        for filt in view['query']['filters']:
            if filt['field'].startswith('cf_') and filt['field'] not in known:
                raise ValueError('Custom filter field does not exist.')
    for widget in spec['widgets'].values():
        for column in widget['columns']:
            if column['field'].startswith('cf_') and column['field'] not in known:
                raise ValueError('Custom column field does not exist.')


def validate_layout_lock(old, new):
    """Pinned widgets cannot change geometry, contents, or membership under an AI patch."""
    for view in old['views']:
        if view['locked']:
            if view_by_id(new, view['id']) != view or any(new['widgets'].get(k) != old['widgets'][k] for k in view['widgets']):
                raise Locked('A locked view and all of its widget configurations are protected.')
    for key, widget in old['widgets'].items():
        if not widget['pinned']:
            continue
        if new['widgets'].get(key) != widget:
            raise Locked('Pinned widget cannot be changed by the agent.')
        for view in old['views']:
            if key not in view['widgets']:
                continue
            after = view_by_id(new, view['id'])
            if key not in after['widgets']:
                raise Locked('Pinned widget cannot be removed from a view.')
            for bp in COLS:
                before_g = next(g for g in view['layouts'][bp] if g['i'] == key)
                after_g = next(g for g in after['layouts'][bp] if g['i'] == key)
                if before_g != after_g:
                    raise Locked('Pinned widget geometry must remain unchanged.')


def transform(store, before, changes: ChangeSet, actor):
    """Pure candidate construction. Publication happens only after full validation."""
    spec = copy.deepcopy(before)
    for operation in changes.operations:
        op = operation.model_dump(exclude_none=True)
        typ = op['op']
        if actor == 'agent' and typ in ('preferences', 'lock_view'):
            raise Locked('The agent cannot change autonomy or locks.')
        if typ == 'preferences':
            spec.update({k: op[k] for k in ('mode', 'default_view', 'allow_structural_auto')})
            continue
        if typ == 'create_view':
            if any(v['id'] == op['view_id'] for v in spec['views']):
                raise ValueError('View ID already exists; edit it instead.')
            if any(v['name'].casefold() == op['name'].casefold() for v in spec['views']):
                raise ValueError('A view with that name already exists.')
            if actor == 'agent' and sum(v['origin'] == 'agent' for v in spec['views']) >= 3:
                raise ValueError('At most three agent-created views; reuse an existing view.')
            source = view_by_id(spec, op['duplicate_from'])
            view = copy.deepcopy(source)
            view.update(id=op['view_id'], name=op['name'], query=op['query'], origin=actor, locked=False)
            mapping = {key: f"{op['view_id']}_w{n + 1}" for n, key in enumerate(view['widgets'])}
            for old, new in mapping.items():
                if new in spec['widgets']:
                    raise ValueError('Duplicate widget ID.')
                widget = copy.deepcopy(spec['widgets'][old])
                widget.update(id=new, pinned=False)
                spec['widgets'][new] = widget
            view['widgets'] = list(mapping.values())
            for bp in COLS:
                for g in view['layouts'][bp]:
                    g['i'] = mapping[g['i']]
            spec['views'].append(view)
            continue
        view = view_by_id(spec, op['view_id'])
        if view['locked'] and typ != 'lock_view':
            raise Locked('Unlock the view before modifying it.')
        if typ == 'lock_view':
            view['locked'] = op['locked']
        elif typ == 'edit_view':
            view.update({k: op[k] for k in ('name', 'query', 'emphasis') if k in op})
        elif typ == 'delete_view':
            if view['id'] in ('all', 'practice'):
                raise Locked('All records and practice views cannot be deleted.')
            spec['views'].remove(view)
            for key in view['widgets']:
                if not any(key in v['widgets'] for v in spec['views']):
                    spec['widgets'].pop(key)
            if spec['default_view'] == view['id']:
                spec['default_view'] = 'all'
        elif typ == 'add_widget':
            widget = op['widget']
            if widget['id'] in spec['widgets']:
                raise ValueError('Widget ID already exists.')
            spec['widgets'][widget['id']] = widget
            view['widgets'].append(widget['id'])
            for bp, cols in COLS.items():
                bottom = max((g['y'] + g['h'] for g in view['layouts'][bp]), default=0)
                view['layouts'][bp].append(dict(i=widget['id'], x=0, y=bottom, w=cols, h=10))
        elif typ in ('configure_widget', 'pin_widget', 'remove_widget'):
            key = op.get('widget_id') or op['widget']['id']
            if key not in view['widgets']:
                raise ValueError('Widget is not in this view.')
            if typ == 'configure_widget':
                if any(v['locked'] and key in v['widgets'] for v in spec['views']):
                    raise Locked('Unlock every view sharing this widget before changing its configuration.')
                if op['widget']['kind'] != spec['widgets'][key]['kind']:
                    raise ValueError('Remove and add to change widget type.')
                spec['widgets'][key] = op['widget']
            elif typ == 'pin_widget':
                spec['widgets'][key]['pinned'] = op['pinned']
            else:
                view['widgets'].remove(key)
                for bp in COLS:
                    view['layouts'][bp] = [g for g in view['layouts'][bp] if g['i'] != key]
                if not any(key in v['widgets'] for v in spec['views']):
                    spec['widgets'].pop(key)
        elif typ == 'set_layout':
            view['layouts'] = op['layouts']
        else:
            raise ValueError('Unsupported operation.')
    validated = Workspace.model_validate(spec).model_dump()
    validate_fields(store, validated)
    if actor == 'agent':
        validate_layout_lock(before, validated)
    return validated


def publish(store, changes: ChangeSet, *, actor='human', force_approval=False, job_id=None):
    with store.lock, store.conn:
        state = current(store)
        if state['version'] != changes.base_version:
            raise Conflict('Workspace changed. Refresh before applying these changes.')
        candidate = transform(store, state['spec'], changes, actor)
        structural = any(o.op in ('create_view', 'delete_view', 'add_widget', 'remove_widget') for o in changes.operations)
        if actor == 'agent' and not force_approval and (
            state['spec']['mode'] != 'adaptive' or len(changes.operations) > 4 or
                (structural and not state['spec']['allow_structural_auto'])):
            ident = uid('proposal')
            store.conn.execute('INSERT INTO ws_proposals VALUES(?,?,\'pending\',?,?,?)',
                               (ident, state['version'], now_iso(), changes.model_dump_json(), job_id))
            audit(store, actor, 'proposal', ident, changes.reason, {'base_version': state['version']})
            return {'status': 'proposed', 'proposal_id': ident, 'version': state['version']}
        version = state['version'] + 1
        encoded = json.dumps(candidate)
        affected = store.conn.execute('UPDATE ws_workspace SET version=?,data=? WHERE singleton=1 AND version=?',
                                      (version, encoded, changes.base_version))
        if affected.rowcount != 1:
            raise Conflict('Workspace version conflict.')
        store.conn.execute('INSERT INTO ws_revisions VALUES(?,?,?,?,?)',
                           (version, actor, changes.reason, now_iso(), encoded))
        audit(store, actor, 'workspace', str(version), changes.reason, {'base_version': changes.base_version})
        return {'status': 'applied', 'version': version, 'spec': candidate}


def restore(store, base_version, target_version=None):
    with store.lock, store.conn:
        state = current(store)
        if state['version'] != base_version:
            raise Conflict('Workspace changed before restore.')
        if target_version is None:
            candidate = default_workspace().model_dump()
            candidate['mode'] = state['spec']['mode']
            reason = 'Reset presentation to default. Lead records and evidence retained.'
        else:
            row = store.conn.execute('SELECT data FROM ws_revisions WHERE version=?', (target_version,)).fetchone()
            if not row:
                raise ValueError('Revision does not exist.')
            candidate = Workspace.model_validate_json(row['data']).model_dump()
            reason = f'Restored workspace revision {target_version}. Lead records retained.'
        validate_fields(store, candidate)
        version = base_version + 1
        data = json.dumps(candidate)
        store.conn.execute('UPDATE ws_workspace SET version=?,data=? WHERE singleton=1', (version, data))
        store.conn.execute('INSERT INTO ws_revisions VALUES(?,?,?,?,?)', (version, 'human', reason, now_iso(), data))
        audit(store, 'human', 'workspace', str(version), reason)
        return {'version': version, 'spec': candidate, 'status': 'applied'}


def approve_proposal(store, ident, *, approve, base_version):
    with store.lock, store.conn:
        row = store.conn.execute('SELECT * FROM ws_proposals WHERE id=?', (ident,)).fetchone()
        if not row or row['status'] != 'pending':
            raise ValueError('Pending proposal not found.')
        if approve:
            if row['base_version'] != base_version:
                raise Conflict('Proposal was based on a different workspace version.')
            result = publish(store, ChangeSet.model_validate_json(row['data']), actor='agent', force_approval=True)
        else:
            result = {'status': 'rejected'}
        store.conn.execute('UPDATE ws_proposals SET status=? WHERE id=?',
                           ('approved' if approve else 'rejected', ident))
        audit(store, 'human', 'proposal_review', ident, 'Approved proposal' if approve else 'Rejected proposal')
        return result


def define_field(store, definition: FieldDefinition):
    with store.lock, store.conn:
        if store.conn.execute('SELECT 1 FROM ws_fields WHERE id=?', (definition.id,)).fetchone():
            raise Conflict('Field ID already exists. Field types are stable.')
        if store.conn.execute('SELECT count(*) FROM ws_fields').fetchone()[0] >= 30:
            raise ValueError('At most 30 custom fields.')
        if definition.type == 'select' and (not definition.options or len(set(definition.options)) != len(definition.options)):
            raise ValueError('Select fields require unique options.')
        if any(len(option) > 100 for option in definition.options):
            raise ValueError('Option is too long.')
        store.conn.execute('INSERT INTO ws_fields VALUES(?,1,?)', (definition.id, definition.model_dump_json()))
        audit(store, 'human', 'field', definition.id, 'Created field definition; values remain unknown.')
        return definition.model_dump()


def field_value(store, lead_id, field_id, value, version):
    from datetime import date
    import math
    with store.lock, store.conn:
        if not store.conn.execute('SELECT 1 FROM leads WHERE id=?', (lead_id,)).fetchone():
            raise ValueError('Lead not found.')
        row = store.conn.execute('SELECT data FROM ws_fields WHERE id=?', (field_id,)).fetchone()
        if not row:
            raise ValueError('Unknown field definition.')
        field = json.loads(row['data'])
        if value is not None:
            typ = field['type']
            if typ in ('text', 'date', 'select') and (not isinstance(value, str) or len(value) > 1000):
                raise ValueError('Expected bounded text.')
            if typ == 'number' and (isinstance(value, bool) or not isinstance(value, (float, int)) or not math.isfinite(value)):
                raise ValueError('Expected a finite number.')
            if typ == 'boolean' and type(value) is not bool:
                raise ValueError('Expected boolean.')
            if typ == 'date':
                date.fromisoformat(value)
            if typ == 'select' and value not in field['options']:
                raise ValueError('Unknown option.')
        prior = store.conn.execute('SELECT version FROM ws_values WHERE lead_id=? AND field_id=?', (lead_id, field_id)).fetchone()
        existing_version = prior['version'] if prior else 0
        if version != existing_version:
            raise Conflict('Custom value changed; refresh before overwriting.')
        store.conn.execute('INSERT OR REPLACE INTO ws_values VALUES(?,?,?,?)',
                           (lead_id, field_id, version + 1, json.dumps(value)))
        audit(store, 'human', 'field_value', lead_id, 'Updated custom field', {'field_id': field_id})
        return {'version': version + 1, 'value': value}
