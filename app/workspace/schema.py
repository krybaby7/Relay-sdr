"""The shared, closed vocabulary for manual and agent workspace edits.

There is intentionally no model-authored data/state, executable code, URL, SQL,
HTML, arbitrary JSON patch, or permission field in this document.
"""
from __future__ import annotations

from typing import Annotated, Literal, Union
from pydantic import BaseModel, ConfigDict, Field, model_validator

ID = Annotated[str, Field(pattern=r'^[a-zA-Z][a-zA-Z0-9_-]{0,63}$')]
Title = Annotated[str, Field(min_length=1, max_length=100)]
Kind = Literal['PriorityQueue', 'LeadsTable', 'PipelineBoard', 'Commitments',
               'CallTimeline', 'EvidencePanel', 'Questions', 'RecentChanges', 'Objections']
KINDS = list(Kind.__args__)
COLUMNS = ['name', 'company', 'potential', 'priority', 'confidence', 'eligibility',
           'stage', 'next_action', 'assessment_at']
SORTS = ['name', 'company', 'potential', 'priority', 'stage', 'created_at', 'assessment_at']
FILTERS = set(COLUMNS + ['status', 'needs_review', 'awaiting_proposal', 'procurement',
                        'needs_decision', 'has_tasks', 'due_today', 'unknowns', 'objection'])
COLS = {'lg': 12, 'md': 8, 'sm': 4}


class Closed(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)


class Filter(Closed):
    field: Annotated[str, Field(max_length=64)]
    op: Literal['eq', 'contains', 'in', 'unknown'] = 'eq'
    value: str | bool | int | list[str] | None = None

    @model_validator(mode='after')
    def bounded(self):
        if self.field not in FILTERS and not self.field.startswith('cf_'):
            raise ValueError('Unsupported filter field.')
        if self.op == 'in' and (not isinstance(self.value, list) or len(self.value) > 20):
            raise ValueError('in needs at most 20 strings.')
        if isinstance(self.value, str) and len(self.value) > 200:
            raise ValueError('Filter value is too long.')
        if isinstance(self.value, list) and any(len(v) > 100 for v in self.value):
            raise ValueError('Filter item is too long.')
        return self


class Query(Closed):
    scope: Literal['real', 'practice'] = 'real'
    search: Annotated[str, Field(max_length=160)] = ''
    filters: Annotated[list[Filter], Field(max_length=10)] = Field(default_factory=list)
    sort: Literal['name', 'company', 'potential', 'priority', 'stage', 'created_at', 'assessment_at'] = 'priority'
    direction: Literal['asc', 'desc'] = 'desc'
    group: Literal['none', 'potential', 'priority', 'stage', 'eligibility', 'company'] = 'none'


class Column(Closed):
    field: Annotated[str, Field(max_length=64)]
    width: Annotated[int, Field(ge=80, le=500)] = 160
    visible: bool = True

    @model_validator(mode='after')
    def allowed(self):
        if self.field not in COLUMNS and not self.field.startswith('cf_'):
            raise ValueError('Unsupported column.')
        return self


class Widget(Closed):
    id: ID
    kind: Kind
    title: Title
    binding: Literal['view', 'selected_lead', 'activity'] = 'view'
    pinned: bool = False
    columns: Annotated[list[Column], Field(max_length=25)] = Field(default_factory=lambda: [
        Column(field=f) for f in COLUMNS[:6]])
    limit: Annotated[int, Field(ge=5, le=50)] = 20

    @model_validator(mode='after')
    def binding_allowed(self):
        expected = {'EvidencePanel': 'selected_lead', 'Questions': 'selected_lead',
                    'RecentChanges': 'activity'}.get(self.kind, 'view')
        if self.binding != expected:
            raise ValueError(f'{self.kind} must bind to {expected}.')
        if len({c.field for c in self.columns}) != len(self.columns):
            raise ValueError('Duplicate columns.')
        return self


class Geometry(Closed):
    i: ID
    x: Annotated[int, Field(ge=0, le=11)] = 0
    y: Annotated[int, Field(ge=0, le=500)] = 0
    w: Annotated[int, Field(ge=2, le=12)] = 6
    h: Annotated[int, Field(ge=4, le=30)] = 8


class Layouts(Closed):
    lg: Annotated[list[Geometry], Field(max_length=16)]
    md: Annotated[list[Geometry], Field(max_length=16)]
    sm: Annotated[list[Geometry], Field(max_length=16)]


class View(Closed):
    id: ID
    name: Title
    query: Query = Field(default_factory=Query)
    widgets: Annotated[list[ID], Field(max_length=16)] = Field(default_factory=list)
    layouts: Layouts
    locked: bool = False
    origin: Literal['system', 'human', 'agent'] = 'human'
    emphasis: Literal['overview', 'pricing', 'decision_process', 'timing', 'conflicts'] = 'overview'


class Workspace(Closed):
    schema_version: Literal[1] = 1
    mode: Literal['manual', 'suggest', 'adaptive'] = 'adaptive'
    default_view: ID = 'today'
    allow_structural_auto: bool = False
    views: Annotated[list[View], Field(min_length=1, max_length=20)]
    widgets: dict[ID, Widget]

    @model_validator(mode='after')
    def references(self):
        ids = [v.id for v in self.views]
        if len(set(ids)) != len(ids) or self.default_view not in ids:
            raise ValueError('Duplicate view or missing default view.')
        if len(self.widgets) > 100 or any(k != v.id for k, v in self.widgets.items()):
            raise ValueError('Invalid widget catalog.')
        referenced = set()
        for v in self.views:
            if len(set(v.widgets)) != len(v.widgets):
                raise ValueError('Duplicate widget in view.')
            referenced.update(v.widgets)
            if any(w not in self.widgets for w in v.widgets):
                raise ValueError('Unknown widget reference.')
            for bp, geometries in v.layouts.model_dump().items():
                if {g['i'] for g in geometries} != set(v.widgets) or len(geometries) != len(v.widgets):
                    raise ValueError('Each breakpoint must cover exactly this view’s widgets.')
                for g in geometries:
                    if g['x'] + g['w'] > COLS[bp] or g['w'] < min(4, COLS[bp]):
                        raise ValueError('Geometry is outside breakpoint or too narrow.')
        if referenced != set(self.widgets):
            raise ValueError('Orphan widget.')
        if 'all' not in ids or 'practice' not in ids:
            raise ValueError('All records and practice navigation must remain available.')
        all_view = next(v for v in self.views if v.id == 'all')
        if all_view.query.filters or all_view.query.search or all_view.query.scope != 'real':
            raise ValueError('All leads must remain unfiltered; duplicate it to filter.')
        practice = next(v for v in self.views if v.id == 'practice')
        if practice.query.scope != 'practice':
            raise ValueError('Practice navigation must remain isolated from real leads.')
        return self


class EditView(Closed):
    op: Literal['edit_view']
    view_id: ID
    name: Title | None = None
    query: Query | None = None
    emphasis: Literal['overview', 'pricing', 'decision_process', 'timing', 'conflicts'] | None = None


class CreateView(Closed):
    op: Literal['create_view']
    view_id: ID
    name: Title
    query: Query
    duplicate_from: ID = 'all'


class DeleteView(Closed):
    op: Literal['delete_view']
    view_id: ID


class AddWidget(Closed):
    op: Literal['add_widget']
    view_id: ID
    widget: Widget


class RemoveWidget(Closed):
    op: Literal['remove_widget']
    view_id: ID
    widget_id: ID


class ConfigureWidget(Closed):
    op: Literal['configure_widget']
    view_id: ID
    widget: Widget


class SetLayout(Closed):
    op: Literal['set_layout']
    view_id: ID
    layouts: Layouts


class Pin(Closed):
    op: Literal['pin_widget']
    view_id: ID
    widget_id: ID
    pinned: bool


class Lock(Closed):
    op: Literal['lock_view']
    view_id: ID
    locked: bool


class Preferences(Closed):
    op: Literal['preferences']
    mode: Literal['manual', 'suggest', 'adaptive']
    default_view: ID
    allow_structural_auto: bool


Operation = Annotated[Union[EditView, CreateView, DeleteView, AddWidget, RemoveWidget,
                            ConfigureWidget, SetLayout, Pin, Lock, Preferences], Field(discriminator='op')]


class ChangeSet(Closed):
    base_version: Annotated[int, Field(ge=1)]
    reason: Annotated[str, Field(min_length=1, max_length=500)]
    operations: Annotated[list[Operation], Field(min_length=1, max_length=12)]


class Plan(Closed):
    reason: Annotated[str, Field(min_length=1, max_length=500)]
    operations: Annotated[list[Operation], Field(max_length=12)]


class FieldDefinition(Closed):
    id: Annotated[str, Field(pattern=r'^cf_[a-z][a-z0-9_]{0,39}$')]
    name: Annotated[str, Field(min_length=1, max_length=60)]
    type: Literal['text', 'number', 'boolean', 'date', 'select']
    options: Annotated[list[str], Field(max_length=30)] = Field(default_factory=list)


class Ref(Closed):
    source_id: Annotated[str, Field(max_length=100)]
    quote: Annotated[str, Field(min_length=1, max_length=1000)]


Topic = Literal['need', 'fit', 'intent', 'authority', 'budget', 'objection', 'decision_process',
                'timing', 'commitment', 'question', 'proposal', 'procurement', 'decision_needed']


class Claim(Closed):
    topic: Topic
    text: Annotated[str, Field(min_length=1, max_length=700)]
    value: Literal['yes', 'no', 'unknown']
    interpretation: Literal['explicit', 'inference']
    references: Annotated[list[Ref], Field(min_length=1, max_length=5)]


class Commitment(Closed):
    wording: Annotated[str, Field(min_length=1, max_length=700)]
    party: Literal['lead', 'operator', 'both']
    kind: Literal['callback', 'proposal', 'information', 'decision', 'meeting_request', 'other']
    date_phrase: Annotated[str, Field(max_length=120)]
    reference: Ref


class Extraction(Closed):
    conversation: bool
    claims: Annotated[list[Claim], Field(max_length=40)]
    commitments: Annotated[list[Commitment], Field(max_length=15)]
    questions: Annotated[list[Annotated[str, Field(max_length=500)]], Field(max_length=20)]


def default_workspace() -> Workspace:
    definitions = [
        ('today', 'Today', [Filter(field='due_today', value=True)], 'PriorityQueue', 'Commitments'),
        ('all', 'All leads', [], 'LeadsTable', 'PipelineBoard'),
        ('potential', 'Highest potential', [Filter(field='potential', op='in', value=['promising', 'strong'])], 'LeadsTable', 'EvidencePanel'),
        ('followups', 'Follow-ups', [Filter(field='has_tasks', value=True)], 'Commitments', 'CallTimeline'),
        ('qualification', 'Needs qualification', [Filter(field='potential', value='unassessed')], 'LeadsTable', 'Questions'),
        ('review', 'Needs review', [Filter(field='needs_review', value=True)], 'PriorityQueue', 'EvidencePanel'),
        ('dnc', 'Do not call', [Filter(field='eligibility', value='suppressed')], 'LeadsTable', 'CallTimeline'),
        ('practice', 'Practice / demo', [], 'LeadsTable', 'CallTimeline'),
    ]
    views, widgets = [], {}
    for ident, name, filters, first, second in definitions:
        kinds = [first, second, 'RecentChanges']
        keys = []
        for n, kind in enumerate(kinds):
            key = f'{ident}_w{n + 1}'
            keys.append(key)
            widgets[key] = Widget(id=key, kind=kind, title={
                'PriorityQueue': 'Where attention matters', 'LeadsTable': 'Lead directory',
                'PipelineBoard': 'Pipeline by stage', 'Commitments': 'Commitments & follow-ups',
                'CallTimeline': 'Call history', 'EvidencePanel': 'Evidence & assessment',
                'Questions': 'Open questions', 'RecentChanges': 'Recent changes',
            }[kind], binding={'EvidencePanel': 'selected_lead', 'Questions': 'selected_lead',
                             'RecentChanges': 'activity'}.get(kind, 'view'))
        layouts = {bp: [Geometry(i=key, x=0 if bp == 'sm' or n != 1 else 8,
                                 y=n * 10 if bp == 'sm' else (0 if n < 2 else 12),
                                 w=width if bp != 'lg' or n == 2 else (8 if n == 0 else 4),
                                 h=10 if n < 2 else 6)
                        for n, key in enumerate(keys)] for bp, width in COLS.items()}
        layouts['md'] = [Geometry(i=key, x=0, y=n * 10, w=8, h=10 if n < 2 else 6)
                         for n, key in enumerate(keys)]
        query = Query(scope='practice' if ident == 'practice' else 'real', filters=filters,
                      sort='potential' if ident == 'potential' else 'priority')
        views.append(View(id=ident, name=name, query=query, widgets=keys,
                          layouts=Layouts(**layouts), origin='system'))
    return Workspace(views=views, widgets=widgets)
