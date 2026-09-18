"""Fictional data and deterministic mocked Responses provider. Never dials."""
from app.db import now_iso
from app.models import LeadInput
from app.workspace import evidence

TEXT = ('We need to reduce manual follow-up work. '
        'Your approved workflow product fits our process. '
        'We want to evaluate a paid pilot. '
        'I make the purchasing decision. '
        'Procurement must review the contract. '
        'Please send a proposal. '
        'Please call me tomorrow at 10:00.')


class FixtureModel:
    available = True

    def __init__(self):
        self.requests = []
        self.plan = {'reason': 'The current organization is useful; no layout change needed.', 'operations': []}
        self.before_return = None

    def generate(self, stage, payload, output_model):
        self.requests.append((stage, payload))
        if stage == 'plan':
            return {'data': self.plan, 'total_tokens': 12}
        sources = payload['sources']
        claims, commitments = [], []
        mappings = [('need', 'We need to reduce manual follow-up work.'),
                    ('fit', 'Your approved workflow product fits our process.'),
                    ('intent', 'We want to evaluate a paid pilot.'),
                    ('authority', 'I make the purchasing decision.'),
                    ('procurement', 'Procurement must review the contract.'),
                    ('proposal', 'Please send a proposal.')]
        for source in sources:
            for topic, quote in mappings:
                if quote in source['text']:
                    claims.append({'topic': topic, 'text': quote, 'value': 'yes', 'interpretation': 'explicit',
                                   'references': [{'source_id': source['source_id'], 'quote': quote}]})
            quote = 'Please call me tomorrow at 10:00.'
            if quote in source['text']:
                commitments.append({'wording': quote, 'party': 'operator', 'kind': 'callback',
                                    'date_phrase': 'tomorrow at 10:00',
                                    'reference': {'source_id': source['source_id'], 'quote': quote}})
        if self.before_return:
            callback, self.before_return = self.before_return, None
            callback()
        return {'data': {'conversation': bool(claims), 'claims': claims, 'commitments': commitments,
                         'questions': []}, 'total_tokens': 100}


def add_real_fixture(store, *, phone='+12025550141', name='Fictional buyer', text=TEXT, kind='twilio', sample=False):
    lead, _ = store.add_lead(LeadInput(name=name, company='Fictional Example Ltd', phone=phone,
                                      timezone='UTC', consent=True,
                                      consent_note='Fictional fixture permission assertion. Never contact.').model_dump(), sample=sample)
    call, _ = store.new_call(kind, lead['id'])
    if text:
        split = 19
        store.transcript(call['id'], {'type': 'session.input_transcript.delta', 'event_id': 'e1', 'delta': text[:split]})
        store.transcript(call['id'], {'type': 'session.input_transcript.delta', 'event_id': 'e2', 'delta': text[split:]})
        evidence.flag(store, call['id'], None, close_observed=True)
    store.patch('calls', call['id'], status='completed' if text else 'no-answer', ended_at=now_iso())
    return lead, call
