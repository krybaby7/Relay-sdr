from __future__ import annotations
import os
import secrets
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlparse

@dataclass
class Config:
    data_dir: Path = field(default_factory=lambda: Path('.data'))
    admin_token: str = ''
    openai_key: str = ''
    live_model: str = 'gpt-live-1'
    backend_model: str = 'gpt-5.6-terra'
    enable_outbound: bool = False
    public_url: str = ''
    twilio_sid: str = ''
    twilio_token: str = ''
    twilio_from: str = ''
    allowed_numbers: set[str] = field(default_factory=set)
    max_seconds: int = 180
    max_daily: int = 10
    max_concurrent: int = 1
    inbound_token: str = ''
    outcome_url: str = ''
    outcome_secret: str = ''
    port: int = 8080
    workspace_enabled: bool = False
    workspace_key: str = ''
    workspace_model: str = ''
    workspace_poll_seconds: float = 1.0
    workspace_settle_seconds: float = 3.0
    workspace_chunk_chars: int = 24000
    workspace_max_chunks: int = 4
    workspace_timeout: float = 45.0
    workspace_output_tokens: int = 6000
    workspace_daily_requests: int = 100
    workspace_daily_tokens: int = 1500000
    workspace_timezone: str = 'UTC'

    @classmethod
    def from_env(cls) -> 'Config':
        path = Path(os.getenv('DATA_DIR', '.data'))
        path.mkdir(parents=True, exist_ok=True, mode=0o700)
        token = os.getenv('ADMIN_TOKEN', '').strip()
        if not token:
            token_file = path / 'admin-token'
            if token_file.exists():
                token = token_file.read_text().strip()
            else:
                token = secrets.token_urlsafe(32)
                fd = os.open(token_file, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
                with os.fdopen(fd, 'w') as f: f.write(token)
        if len(token) < 24:
            raise ValueError('ADMIN_TOKEN must contain at least 24 characters.')
        c = cls(data_dir=path, admin_token=token,
            openai_key=os.getenv('OPENAI_API_KEY', '').strip(),
            live_model=os.getenv('LIVE_MODEL', 'gpt-live-1'),
            backend_model=os.getenv('BACKEND_MODEL', 'gpt-5.6-terra'),
            enable_outbound=os.getenv('ENABLE_OUTBOUND', 'false').lower() == 'true',
            public_url=os.getenv('PUBLIC_BASE_URL', '').rstrip('/'),
            twilio_sid=os.getenv('TWILIO_ACCOUNT_SID', ''),
            twilio_token=os.getenv('TWILIO_AUTH_TOKEN', ''),
            twilio_from=os.getenv('TWILIO_FROM_NUMBER', ''),
            allowed_numbers={n.strip() for n in os.getenv('ALLOWED_NUMBERS', '').split(',') if n.strip()},
            max_seconds=int(os.getenv('MAX_CALL_SECONDS', '180')),
            max_daily=int(os.getenv('MAX_DAILY_CALLS', '10')),
            max_concurrent=int(os.getenv('MAX_CONCURRENT_CALLS', '1')),
            inbound_token=os.getenv('INBOUND_LEAD_TOKEN', ''),
            outcome_url=os.getenv('OUTCOME_WEBHOOK_URL', ''),
            outcome_secret=os.getenv('OUTCOME_WEBHOOK_SECRET', ''),
            port=int(os.getenv('PORT', '8080')),
            workspace_enabled=os.getenv('WORKSPACE_ENABLED', 'false').lower() == 'true',
            workspace_key=os.getenv('WORKSPACE_API_KEY', '').strip(),
            workspace_model=os.getenv('WORKSPACE_MODEL', '').strip(),
            workspace_poll_seconds=float(os.getenv('WORKSPACE_POLL_SECONDS', '1')),
            workspace_settle_seconds=float(os.getenv('WORKSPACE_SETTLE_SECONDS', '3')),
            workspace_chunk_chars=int(os.getenv('WORKSPACE_CHUNK_CHARS', '24000')),
            workspace_max_chunks=int(os.getenv('WORKSPACE_MAX_CHUNKS', '4')),
            workspace_timeout=float(os.getenv('WORKSPACE_TIMEOUT', '45')),
            workspace_output_tokens=int(os.getenv('WORKSPACE_OUTPUT_TOKENS', '6000')),
            workspace_daily_requests=int(os.getenv('WORKSPACE_DAILY_REQUESTS', '100')),
            workspace_daily_tokens=int(os.getenv('WORKSPACE_DAILY_TOKENS', '1500000')),
            workspace_timezone=os.getenv('WORKSPACE_TIMEZONE', 'UTC'))
        from zoneinfo import ZoneInfo
        ZoneInfo(c.workspace_timezone)
        for field_name, low, high in (
            ('workspace_poll_seconds', 0.2, 30), ('workspace_settle_seconds', 1, 60),
            ('workspace_chunk_chars', 4000, 48000), ('workspace_max_chunks', 1, 20),
            ('workspace_timeout', 5, 120), ('workspace_output_tokens', 1000, 16000),
            ('workspace_daily_requests', 1, 10000), ('workspace_daily_tokens', 10000, 100000000)):
            if not low <= getattr(c, field_name) <= high:
                raise ValueError(f'{field_name} must be {low}–{high}.')
        if not 30 <= c.max_seconds <= 600: raise ValueError('MAX_CALL_SECONDS must be 30–600.')
        if not 1 <= c.max_daily <= 100: raise ValueError('MAX_DAILY_CALLS must be 1–100 for this pilot.')
        if not 1 <= c.max_concurrent <= 5: raise ValueError('MAX_CONCURRENT_CALLS must be 1–5.')
        for name, url in [('PUBLIC_BASE_URL', c.public_url), ('OUTCOME_WEBHOOK_URL', c.outcome_url)]:
            if url and (urlparse(url).scheme != 'https' or not urlparse(url).hostname or urlparse(url).username):
                raise ValueError(f'{name} must be a full HTTPS URL without embedded credentials.')
        if c.public_url and (urlparse(c.public_url).path not in ('', '/') or urlparse(c.public_url).query):
            raise ValueError('PUBLIC_BASE_URL must be an origin, with no path or query.')
        return c

    def allowed_origins(self) -> set[str]:
        return {f'http://localhost:{self.port}', f'http://127.0.0.1:{self.port}', self.public_url} - {''}

    def connectors(self) -> list[dict]:
        phone_ready = all([self.openai_key, self.twilio_sid, self.twilio_token, self.twilio_from, self.public_url])
        return [
            {'id': 'browser', 'name': 'Browser voice lab', 'kind': 'Voice', 'configured': bool(self.openai_key),
             'detail': 'GPT-Live through your microphone. No telephone call.'},
            {'id': 'twilio', 'name': 'Twilio Voice', 'kind': 'Calling', 'configured': phone_ready,
             'detail': 'Outbound telephone calls via signed Media Streams. Live-account test required.'},
            {'id': 'inbound', 'name': 'Lead intake API', 'kind': 'CRM input', 'configured': bool(self.inbound_token),
             'detail': 'Scoped, authenticated HTTP endpoint for your CRM or automation tool.'},
            {'id': 'outcome', 'name': 'Outcome webhook', 'kind': 'CRM output',
             'configured': bool(self.outcome_url and self.outcome_secret),
             'detail': 'Manually approved, signed event delivery. A webhook is not a voice connection.'}]
