from __future__ import annotations
from typing import Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from pydantic import BaseModel, Field, ConfigDict, field_validator, model_validator
import re

class StrictModel(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)

class LeadInput(StrictModel):
    name: str = Field(min_length=1, max_length=120)
    company: str = Field(default='', max_length=160)
    phone: str = Field(min_length=8, max_length=20)
    timezone: str = 'Africa/Cairo'
    language: str = Field(default='English', max_length=100)
    notes: str = Field(default='', max_length=5000)
    consent: bool = False
    consent_note: str = Field(default='', max_length=1000)
    @field_validator('phone')
    @classmethod
    def phone_e164(cls, value: str) -> str:
        # Remove only presentation characters; never infer a country code.
        value = re.sub(r'[\s().-]', '', value)
        if not re.fullmatch(r'\+[1-9]\d{7,14}', value):
            raise ValueError('Use an international number with + and country code (E.164).')
        return value
    @field_validator('timezone')
    @classmethod
    def valid_timezone(cls, value: str) -> str:
        try: ZoneInfo(value)
        except (ZoneInfoNotFoundError, ValueError): raise ValueError('Use a valid IANA timezone.')
        return value
    @model_validator(mode='after')
    def evidence(self):
        if self.consent and len(self.consent_note) < 8:
            raise ValueError('Record the source/date/scope of permission for AI sales calling.')
        return self

class Playbook(StrictModel):
    company: str = Field(default='Your company', min_length=1, max_length=160)
    agent_name: str = Field(default='Alex', min_length=1, max_length=60)
    product: str = Field(default='Describe your product here before a live call.', max_length=5000)
    customer_profile: str = Field(default='Describe the customers you can genuinely help.', max_length=3000)
    qualification: str = Field(default='Ask about their current process, main problem, decision-maker, and timing. Ask one question at a time.', max_length=3000)
    facts: str = Field(default='No pricing, guarantees, or product claims have been approved yet. Do not invent them.', max_length=10000)
    goal: str = Field(default='Qualify interest and collect a meeting request for human confirmation.', max_length=1500)
    language: str = Field(default='English', max_length=100)
    tone: str = Field(default='Warm, professional, brief, and never pushy.', max_length=1000)
    voice: Literal['marin', 'cedar'] = 'marin'
    start_hour: int = Field(default=9, ge=0, le=23)
    end_hour: int = Field(default=17, ge=1, le=24)
    weekdays: list[int] = Field(default_factory=lambda: [0, 1, 2, 3, 4], min_length=1, max_length=7)
    approved: bool = False
    @field_validator('weekdays')
    @classmethod
    def days(cls, value):
        if any(d < 0 or d > 6 for d in value): raise ValueError('Weekdays use Monday=0 through Sunday=6.')
        return sorted(set(value))
    @model_validator(mode='after')
    def window(self):
        if self.end_hour <= self.start_hour: raise ValueError('End hour must be after start hour.')
        if self.approved and (self.company == 'Your company' or len(self.product) < 20 or self.product == 'Describe your product here before a live call.'):
            raise ValueError('Add your real company and a useful product description before approving.')
        return self

class DialInput(StrictModel):
    lead_id: str
    confirm: bool = False
    request_id: str = Field(min_length=16, max_length=100, pattern=r'^[a-zA-Z0-9_-]+$')

class VoiceInput(StrictModel):
    lead_id: str | None = None

class OutcomeArgs(StrictModel):
    outcome: Literal['qualified', 'not_interested', 'callback', 'wrong_number', 'unqualified']
    summary: str = Field(min_length=1, max_length=2000)
    next_step: str = Field(default='', max_length=1000)

class RequestArgs(StrictModel):
    details: str = Field(min_length=1, max_length=2000)

class OptOutArgs(StrictModel):
    reason: str = Field(min_length=1, max_length=1000)
