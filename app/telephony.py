"""Small, fixed-origin Twilio adapter; no model-selected URLs or phone destinations."""
from __future__ import annotations
import base64, hashlib, hmac, re
from urllib.parse import urlencode
import httpx
from .config import Config

def twilio_signature(token: str, url: str, parameters: dict[str, list[str]]) -> str:
    body = url + ''.join(k + v for k in sorted(parameters) for v in sorted(set(parameters[k])))
    return base64.b64encode(hmac.new(token.encode(), body.encode(), hashlib.sha1).digest()).decode()

def validate_signature(token: str, url: str, parameters: dict[str, list[str]], supplied: str) -> bool:
    return bool(token and supplied and hmac.compare_digest(twilio_signature(token, url, parameters), supplied))

class Twilio:
    def __init__(self, config: Config): self.config = config
    async def request(self, method, suffix='', data=None):
        c = self.config
        if not re.fullmatch(r'AC[0-9a-fA-F]{32}', c.twilio_sid):
            raise ValueError('Set a valid TWILIO_ACCOUNT_SID.')
        url = f'https://api.twilio.com/2010-04-01/Accounts/{c.twilio_sid}/Calls{suffix}.json'
        async with httpx.AsyncClient(timeout=15, follow_redirects=False) as client:
            r = await client.request(method, url, auth=(c.twilio_sid, c.twilio_token),
                content=urlencode(data, doseq=True) if data is not None else None,
                headers={'Content-Type': 'application/x-www-form-urlencoded'})
            r.raise_for_status()
            return r.json()
    async def dial(self, call_id: str, phone: str):
        c = self.config
        return await self.request('POST', data={
            'To': phone, 'From': c.twilio_from, 'Url': f'{c.public_url}/twilio/voice/{call_id}',
            'Method': 'POST', 'Timeout': '25', 'TimeLimit': str(c.max_seconds), 'Record': 'false',
            'StatusCallback': f'{c.public_url}/twilio/status/{call_id}', 'StatusCallbackMethod': 'POST',
            'StatusCallbackEvent': ['initiated', 'ringing', 'answered', 'completed']})
    async def fetch_call(self, sid):
        self._check_sid(sid); return await self.request('GET', '/' + sid)
    async def hangup(self, sid):
        self._check_sid(sid)
        return await self.request('POST', '/' + sid, data={'Status': 'completed'})
    @staticmethod
    def _check_sid(sid):
        if not re.fullmatch(r'CA[0-9a-fA-F]{32}', sid or ''): raise ValueError('Invalid provider call ID.')
