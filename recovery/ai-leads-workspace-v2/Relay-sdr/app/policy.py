from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from .config import Config
from .db import Store

ACTIVE = {'created', 'dialing', 'queued', 'initiated', 'ringing', 'in-progress', 'connected', 'ending'}
TERMINAL = {'completed', 'failed', 'busy', 'no-answer', 'canceled', 'interrupted', 'unknown'}

def dial_blockers(c: Config, store: Store, lead: dict, book: dict, now=None) -> list[str]:
    now = now or datetime.now(timezone.utc)
    reasons = []
    if not c.enable_outbound: reasons.append('Live outbound dialing is disabled on the server.')
    if not all([c.openai_key, c.twilio_sid, c.twilio_token, c.twilio_from, c.public_url]):
        reasons.append('OpenAI, Twilio, caller number, and public HTTPS configuration are required.')
    if lead.get('sample'): reasons.append('Sample leads can never receive real calls. Add your own test lead.')
    if not book.get('approved'): reasons.append('Review and approve your sales playbook first.')
    if not lead.get('consent') or not lead.get('consent_note'):
        reasons.append('Permission for AI sales calling and its evidence must be recorded.')
    if store.suppressed(lead['phone']) or lead.get('opted_out'):
        reasons.append('This number is on the do-not-call list.')
    if lead['phone'] not in c.allowed_numbers:
        reasons.append('This number is not in the server pilot allowlist.')
    local = now.astimezone(ZoneInfo(lead['timezone']))
    if local.weekday() not in book['weekdays'] or not book['start_hour'] <= local.hour < book['end_hour']:
        reasons.append('Outside the approved calling window in the lead’s timezone.')
    calls = store.all('calls')
    if any(x['kind'] == 'twilio' and x['status'] == 'unknown' for x in calls):
        reasons.append('A previous telephone attempt has an unknown state. Reconcile it before dialing again.')
    if any(x['lead_id'] == lead['id'] and x['status'] in ACTIVE for x in calls):
        reasons.append('A call to this lead is already active.')
    if sum(x['status'] in ACTIVE for x in calls) >= c.max_concurrent:
        reasons.append('The concurrent-session limit has been reached.')
    today = now.date().isoformat()
    if sum(x['kind'] == 'twilio' and x['created_at'][:10] == today for x in calls) >= c.max_daily:
        reasons.append('The daily telephone-attempt limit (UTC) has been reached.')
    return reasons
