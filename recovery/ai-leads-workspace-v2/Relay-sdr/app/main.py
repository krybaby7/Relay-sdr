from __future__ import annotations
import asyncio, contextlib, csv, hashlib, hmac, io, json, re, secrets, time
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from pathlib import Path
from urllib.parse import parse_qs, urlparse
from xml.etree.ElementTree import Element, SubElement, tostring
import httpx
from fastapi import FastAPI, Depends, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
from .config import Config
from .db import Store, now_iso
from .models import LeadInput, Playbook, DialInput, VoiceInput
from .policy import ACTIVE, TERMINAL, dial_blockers
from .telephony import Twilio, validate_signature
from .live import run_bridge

WEB = Path(__file__).resolve().parent.parent / 'web'
PROVIDER_TERMINAL = {'completed', 'failed', 'busy', 'no-answer', 'canceled'}
PROVIDER_STATUS = PROVIDER_TERMINAL | {'queued', 'initiated', 'ringing', 'in-progress'}

def equal(a, b):
    return bool(a and b and hmac.compare_digest(a.encode(), b.encode()))

class BodyLimit:
    """Bound HTTP request memory even when Content-Length is omitted."""
    def __init__(self, app, limit=262144): self.app = app; self.limit = limit
    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http': return await self.app(scope, receive, send)
        parts = []; size = 0
        while True:
            message = await receive()
            if message['type'] == 'http.disconnect': return
            size += len(message.get('body', b''))
            if size > self.limit:
                return await JSONResponse({'detail': 'Request body exceeds 256 KiB.'}, status_code=413)(scope, receive, send)
            parts.append(message)
            if not message.get('more_body'): break
        async def replay():
            if parts: return parts.pop(0)
            return await receive()
        await self.app(scope, replay, send)

def create_app(config: Config | None = None, *, provider=None):
    c = config or Config.from_env()
    c.data_dir.mkdir(parents=True, exist_ok=True)
    store = Store(c.data_dir / 'relay.sqlite3')
    twilio = provider or Twilio(c)
    sessions: dict[str, asyncio.Event] = {}
    tickets: dict[str, dict] = {}; media_tokens: dict[str, dict] = {}
    tasks: set[asyncio.Task] = set()
    timers: set[asyncio.Task] = set()
    dial_lock = asyncio.Lock(); outbox_lock = asyncio.Lock()
    failures = defaultdict(deque); limits = defaultdict(deque)
    # On restart never assume a potentially billable provider call has ended.
    for old in store.all('calls'):
        if old['status'] in ACTIVE:
            store.patch('calls', old['id'], status='unknown' if old['kind'] == 'twilio' else 'interrupted',
                ended_at=None if old['kind'] == 'twilio' else now_iso(),
                error='Server restarted. Reconcile provider state before another real call.' if old['kind'] == 'twilio' else 'Browser session interrupted by a server restart.')

    for old in store.all('outbox'):
        if old['status'] == 'sending':
            store.patch('outbox', old['id'], status='delivery_uncertain',
                last_error='Server restarted during delivery. Check the receiver before retrying with the same event ID.')

    def spawn(coro, *, timer=False):
        task = asyncio.create_task(coro); tasks.add(task); task.add_done_callback(tasks.discard)
        if timer:
            timers.add(task); task.add_done_callback(timers.discard)
        return task

    @asynccontextmanager
    async def lifespan(app):
        yield
        for stop in sessions.values(): stop.set()
        # Sleeping expiry watchdogs are not work to finish during shutdown.
        for task in list(timers): task.cancel()
        if timers: await asyncio.gather(*list(timers), return_exceptions=True)
        active_phone = [x for x in store.all('calls') if x['kind'] == 'twilio' and x['status'] in ACTIVE]
        if active_phone:
            with contextlib.suppress(asyncio.TimeoutError):
                await asyncio.wait_for(asyncio.gather(*(stop_phone(x['id']) for x in active_phone)), 16)
        if tasks:
            done, pending = await asyncio.wait(list(tasks), timeout=12)
            for task in pending: task.cancel()
            await asyncio.gather(*pending, return_exceptions=True)
        store.close()

    app = FastAPI(title='Relay SDR', version='0.1.0', lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)
    app.state.store = store; app.state.config = c; app.state.sessions = sessions; app.state.tickets = tickets
    app.add_middleware(BodyLimit)
    hosts = {'localhost', '127.0.0.1'}
    if c.public_url: hosts.add(urlparse(c.public_url).hostname)
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=list(hosts))

    def limit(request, key, maximum=120):
        address = request.client.host if request.client else 'unknown'
        bucket = limits[(key, address)]; now = time.monotonic()
        while bucket and bucket[0] < now-60: bucket.popleft()
        if len(bucket) >= maximum: raise HTTPException(429, 'Too many requests. Try again in a minute.')
        bucket.append(now)

    async def admin(request: Request):
        limit(request, 'admin', 180)
        origin = request.headers.get('origin')
        if origin and origin not in c.allowed_origins(): raise HTTPException(403, 'Origin is not allowed.')
        value = request.headers.get('authorization', '')
        if not equal(value, 'Bearer ' + c.admin_token):
            limit(request, 'bad_auth', 12)
            raise HTTPException(401, 'Use the workspace token printed by the server.')

    @app.middleware('http')
    async def headers(request, call_next):
        response = await call_next(request)
        response.headers.update({
            'X-Content-Type-Options': 'nosniff', 'Referrer-Policy': 'no-referrer',
            'X-Frame-Options': 'DENY', 'Cache-Control': 'no-store',
            'Content-Security-Policy': "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; connect-src 'self'; img-src 'self' data:; media-src 'self' blob:; object-src 'none'; base-uri 'none'; frame-ancestors 'none'",
            'Permissions-Policy': 'camera=(), microphone=(self), geolocation=()'})
        return response

    @app.exception_handler(json.JSONDecodeError)
    async def invalid_json(request, exc):
        return JSONResponse({'detail': 'Malformed JSON body.'}, status_code=400)

    @app.exception_handler(RequestValidationError)
    async def validation_error(request, exc):
        # Pydantic context may include exception objects; never echo secret-bearing input.
        errors = [{'field': '.'.join(str(i) for i in e['loc']), 'message': e['msg']} for e in exc.errors()]
        return JSONResponse({'detail': errors}, status_code=422)

    def get(table, id):
        obj = store.get(table, id)
        if not obj: raise HTTPException(404, 'Record not found.')
        return obj

    def complete(call_id, status, **changes):
        call = store.patch('calls', call_id, status=status, **changes)
        if status in PROVIDER_TERMINAL:
            call = store.patch('calls', call_id, ended_at=call['ended_at'] or now_iso())
            if call_id in sessions: sessions[call_id].set()
            else: store.enqueue(call)
        return call

    def bind_sid(call, sid):
        if not re.fullmatch(r'CA[0-9a-fA-F]{32}', sid or ''): raise HTTPException(400, 'Invalid call identifier.')
        if call['provider_sid'] and not equal(call['provider_sid'], sid): raise HTTPException(403, 'Call identifier does not match.')
        if not call['provider_sid']: store.patch('calls', call['id'], provider_sid=sid)

    async def stop_phone(call_id):
        call = get('calls', call_id)
        if call['status'] in PROVIDER_TERMINAL: return call
        if call_id in sessions: sessions[call_id].set()
        sid = call.get('provider_sid')
        if not sid:
            return store.patch('calls', call_id, status='unknown', error='No provider ID. Inspect Twilio before retrying; a call may exist.')
        try:
            result = await twilio.hangup(sid)
            status = result.get('status')
            if status not in PROVIDER_STATUS: raise ValueError('Unexpected provider status.')
            return complete(call_id, status)
        except Exception:
            latest = get('calls', call_id)
            if latest['status'] in PROVIDER_TERMINAL: return latest
            return store.patch('calls', call_id, status='unknown', error='Could not confirm provider hangup. Check Twilio and reconcile.')

    async def expire_call(call_id, seconds, ticket=None):
        await asyncio.sleep(seconds)
        call = store.get('calls', call_id)
        if ticket:
            if ticket not in tickets: return  # Already consumed by a browser connection.
            tickets.pop(ticket, None)
        if not call or call['status'] not in ACTIVE: return
        if call_id in sessions: sessions[call_id].set()
        elif call['kind'] == 'twilio': await stop_phone(call_id)
        else: store.patch('calls', call_id, status='interrupted', ended_at=now_iso(), error='Browser connection ticket expired.')

    @app.get('/health')
    async def health(): return {'status': 'ok'}

    @app.get('/api/state', dependencies=[Depends(admin)])
    async def state():
        leads = store.all('leads'); calls = store.all('calls')
        # Transcripts are fetched only on demand; the dashboard has no invented activity.
        overview = [{k: v for k, v in item.items() if k != 'transcript'} | {'transcript_fragments': len(item['transcript'])} for item in calls]
        return dict(leads=leads, calls=overview, playbook=store.get_setting('playbook'),
            connectors=c.connectors(), outbox=store.all('outbox'),
            config={'outbound_enabled': c.enable_outbound, 'max_seconds': c.max_seconds, 'max_daily': c.max_daily,
                    'max_concurrent': c.max_concurrent, 'live_model': c.live_model, 'backend_model': c.backend_model,
                    'allowlist_count': len(c.allowed_numbers)})

    @app.post('/api/leads', dependencies=[Depends(admin)])
    async def add_lead(data: LeadInput):
        lead, created = store.add_lead(data.model_dump())
        return {'lead': lead, 'created': created}

    @app.put('/api/leads/{id}', dependencies=[Depends(admin)])
    async def edit_lead(id: str, data: LeadInput):
        lead = get('leads', id)
        if data.phone != lead['phone']: raise HTTPException(409, 'Telephone identity is immutable; add a separate lead instead.')
        changes = data.model_dump()
        if store.suppressed(lead['phone']): changes['consent'] = False
        if changes['consent'] and (not lead['consent'] or changes['consent_note'] != lead['consent_note']):
            changes['consent_recorded_at'] = now_iso()
        return store.patch('leads', id, **changes)

    @app.post('/api/leads/{id}/suppress', dependencies=[Depends(admin)])
    async def suppress(id: str):
        lead = get('leads', id); store.suppress(lead['phone'], 'Operator marked do not call.')
        for call in store.all('calls'):
            if call['lead_id'] == id and call['kind'] == 'twilio' and call['status'] in ACTIVE:
                spawn(stop_phone(call['id']))
        return {'lead': get('leads', id)}

    @app.post('/api/leads/import', dependencies=[Depends(admin)])
    async def import_csv(request: Request):
        data = await request.json(); raw = data.get('csv', '') if isinstance(data, dict) else ''
        if not isinstance(raw, str) or not raw.strip(): raise HTTPException(422, 'Send a nonempty CSV string.')
        reader = csv.DictReader(io.StringIO(raw.lstrip('\ufeff')))
        if not reader.fieldnames or not {'name', 'phone'}.issubset(reader.fieldnames):
            raise HTTPException(422, 'CSV requires name and phone columns.')
        added = 0; duplicates = 0; errors = []
        for i, row in enumerate(reader, start=2):
            if i > 1001:
                errors.append({'row': i, 'error': 'Pilot imports are limited to 1,000 rows; remaining rows were not imported.'}); break
            try:
                if None in row: raise ValueError('More values than CSV columns.')
                row = {k: v for k, v in row.items() if v not in ('', None)}
                consent = str(row.get('consent', 'false')).lower()
                if consent not in ('true', 'false', '1', '0', 'yes', 'no'): raise ValueError('Consent must be true or false.')
                row['consent'] = consent in ('true', '1', 'yes')
                validated = LeadInput.model_validate(row)
                _, created = store.add_lead(validated.model_dump())
                added += int(created); duplicates += int(not created)
            except (ValidationError, ValueError) as exc:
                errors.append({'row': i, 'error': '; '.join(e['msg'] for e in exc.errors()) if isinstance(exc, ValidationError) else str(exc)})
        return dict(added=added, duplicates=duplicates, errors=errors)

    @app.post('/api/sample-leads', dependencies=[Depends(admin)])
    async def samples():
        names = [('Maya Hassan', 'Northstar Studio'), ('Omar Adel', 'Cedar Learning'), ('Lina Samir', 'Atlas Logistics')]
        added = 0
        for i, (name, company) in enumerate(names):
            _, created = store.add_lead(LeadInput(name=name, company=company, phone=f'+1202555010{i+1}',
                notes='Fictional demo lead. Never dial. Use only to explore the interface.').model_dump(), sample=True)
            added += created
        return {'added': added}

    @app.put('/api/playbook', dependencies=[Depends(admin)])
    async def playbook(data: Playbook):
        store.setting('playbook', data.model_dump()); return data.model_dump()

    @app.get('/api/leads/{id}/preflight', dependencies=[Depends(admin)])
    async def preflight(id: str):
        lead = get('leads', id)
        reasons = dial_blockers(c, store, lead, store.get_setting('playbook'))
        return {'allowed': not reasons, 'reasons': reasons, 'lead': lead,
                'maximum_seconds': c.max_seconds, 'disclosure': 'The agent identifies itself as AI and says conversation notes are kept.'}

    @app.post('/api/calls/dial', dependencies=[Depends(admin)])
    async def dial(data: DialInput):
        if not data.confirm: raise HTTPException(422, 'Explicit confirmation is required for each real call.')
        async with dial_lock:
            old = store.by_request(data.request_id)
            if old:
                if old['lead_id'] != data.lead_id: raise HTTPException(409, 'Idempotency key belongs to another lead.')
                return {'call': old, 'reused': True}
            lead = get('leads', data.lead_id)
            reasons = dial_blockers(c, store, lead, store.get_setting('playbook'))
            if reasons: raise HTTPException(409, reasons)
            call, _ = store.new_call('twilio', lead['id'], data.request_id)
            store.patch('calls', call['id'], status='dialing', playbook_snapshot=store.get_setting('playbook'))
        try:
            result = await twilio.dial(call['id'], lead['phone'])
            bind_sid(get('calls', call['id']), result.get('sid'))
            latest = get('calls', call['id'])
            # An earlier signed callback is more recent than the create response.
            if latest['status'] in ('created', 'dialing'):
                status = result.get('status', 'queued')
                if status not in PROVIDER_STATUS: raise ValueError('Unknown provider status.')
                complete(call['id'], status)
            spawn(expire_call(call['id'], c.max_seconds + 40), timer=True)
        except httpx.HTTPStatusError as exc:
            code = exc.response.status_code
            # A 5xx may occur after creation; do not automatically retry.
            complete(call['id'], 'failed' if 400 <= code < 500 else 'unknown',
                     error=f'Twilio returned HTTP {code}. ' + ('Review configuration.' if code < 500 else 'Reconcile provider state; do not redial.'))
        except Exception:
            latest = get('calls', call['id'])
            if latest['status'] not in PROVIDER_TERMINAL:
                store.patch('calls', call['id'], status='unknown', error='Call creation result is uncertain. Inspect Twilio and reconcile before retrying.')
        return {'call': get('calls', call['id']), 'reused': False}

    @app.get('/api/calls/{id}', dependencies=[Depends(admin)])
    async def call_detail(id: str): return get('calls', id)

    @app.post('/api/calls/{id}/stop', dependencies=[Depends(admin)])
    async def stop_call(id: str):
        call = get('calls', id)
        if call['kind'] == 'twilio': return await stop_phone(id)
        if id in sessions: sessions[id].set()
        elif call['status'] in ACTIVE: store.patch('calls', id, status='interrupted', ended_at=now_iso())
        return get('calls', id)

    @app.post('/api/calls/{id}/reconcile', dependencies=[Depends(admin)])
    async def reconcile(id: str):
        call = get('calls', id)
        if call['kind'] != 'twilio' or not call.get('provider_sid'):
            raise HTTPException(409, 'No bound provider ID. Inspect the Twilio console; do not blindly retry.')
        try:
            result = await twilio.fetch_call(call['provider_sid'])
            if result.get('sid') != call['provider_sid'] or result.get('status') not in PROVIDER_STATUS: raise ValueError()
            lead = get('leads', call['lead_id'])
            if result.get('to') != lead['phone'] or result.get('from') != c.twilio_from: raise ValueError()
            return complete(id, result['status'], error=None)
        except Exception: raise HTTPException(502, 'Provider reconciliation failed. Call state has not been cleared.')

    @app.post('/api/voice/ticket', dependencies=[Depends(admin)])
    async def voice_ticket(data: VoiceInput):
        if not c.openai_key: raise HTTPException(409, 'Set OPENAI_API_KEY on the server first.')
        if data.lead_id: get('leads', data.lead_id)
        if sum(x['status'] in ACTIVE for x in store.all('calls')) >= c.max_concurrent:
            raise HTTPException(409, 'The concurrent-session limit has been reached.')
        token = secrets.token_urlsafe(32); call, _ = store.new_call('browser', data.lead_id)
        store.patch('calls', call['id'], playbook_snapshot=store.get_setting('playbook'))
        tickets[token] = {'call_id': call['id'], 'expires': time.monotonic()+45}
        spawn(expire_call(call['id'], 45, token), timer=True)
        return {'ticket': token, 'call_id': call['id'], 'path': '/ws/voice'}

    @app.websocket('/ws/voice')
    async def voice(ws: WebSocket):
        if ws.headers.get('origin') not in c.allowed_origins(): return await ws.close(code=1008)
        ticket = tickets.pop(ws.query_params.get('ticket', ''), None)
        if not ticket or ticket['expires'] < time.monotonic(): return await ws.close(code=1008)
        call_id = ticket['call_id']
        if get('calls', call_id)['status'] not in ACTIVE: return await ws.close(code=1008)
        await ws.accept(); stop = asyncio.Event(); sessions[call_id] = stop
        async def receive():
            try:
                value = await ws.receive_json()
                if not isinstance(value, dict): return None
                return value
            except (WebSocketDisconnect, ValueError): return None
        try: await run_bridge(c, store, call_id, receive, ws.send_json, stop)
        finally:
            sessions.pop(call_id, None)
            with contextlib.suppress(Exception): await ws.close()

    @app.post('/api/demo', dependencies=[Depends(admin)])
    async def demo():
        call, _ = store.new_call('simulation')
        lines = [
            ('agent', 'Hi, I’m Alex, an AI sales assistant for the fictional Northstar team. We keep conversation notes. Is now a good time for a brief chat?'),
            ('lead', 'Sure. What is this about?'),
            ('agent', 'This is a scripted preview of an SDR qualification call. How does your team currently follow up with new inquiries?'),
            ('lead', 'We do it manually. Sometimes it takes a day to reply.'),
            ('agent', 'What would a faster response change for your team?'),
            ('lead', 'We could speak to more people while they are still interested.'),
            ('agent', 'Would you like me to record a request for a short conversation with a human specialist?'),
            ('lead', 'Yes, next week in the afternoon. Cairo time.'),
            ('agent', 'I’ve recorded your request. A human would need to confirm a specific time; nothing has been booked. Thanks for your time.')]
        for i, (role, text) in enumerate(lines):
            store.transcript(call['id'], {'type': 'session.input_transcript.delta' if role == 'lead' else 'session.output_transcript.delta',
                'delta': text, 'start_ms': i*4000, 'end_ms': (i+1)*4000, 'event_id': f'demo_{i}'})
        store.patch('calls', call['id'], status='completed', ended_at=now_iso(), outcome='qualified',
            summary='SCRIPTED DEMO — fictional lead wants faster follow-up. No AI request, telephone call, or external action occurred.',
            next_step='Human confirmation would be required.', requests=[{'type': 'meeting', 'details': 'Fictional example: next week, afternoon, Africa/Cairo.', 'status': 'needs_human_confirmation', 'created_at': now_iso()}])
        return get('calls', call['id'])

    @app.post('/api/outbox/{id}/deliver', dependencies=[Depends(admin)])
    async def deliver(id: str, request: Request):
        body = await request.json()
        if not isinstance(body, dict) or body.get('confirm') is not True: raise HTTPException(422, 'Confirm external delivery.')
        if not c.outcome_url or not c.outcome_secret: raise HTTPException(409, 'Set the fixed outcome webhook URL and secret on the server.')
        async with outbox_lock:
            event = get('outbox', id)
            if event['status'] == 'sent': return event
            call = get('calls', id)
            if call['kind'] != 'twilio' or call['status'] not in PROVIDER_TERMINAL or id in sessions:
                raise HTTPException(409, 'Wait for the real call to finish before sharing its outcome.')
            payload = {'id': event['id'], 'type': 'call.completed', 'data': event['payload']}
            raw = json.dumps(payload, ensure_ascii=False, separators=(',', ':')).encode()
            timestamp = str(int(time.time()))
            signature = hmac.new(c.outcome_secret.encode(), timestamp.encode()+b'.'+raw, hashlib.sha256).hexdigest()
            store.patch('outbox', id, status='sending', attempts=event['attempts']+1)
            try:
                async with httpx.AsyncClient(timeout=12, follow_redirects=False) as client:
                    r = await client.post(c.outcome_url, content=raw, headers={
                        'Content-Type': 'application/json', 'X-Relay-Event-Id': id,
                        'X-Relay-Timestamp': timestamp, 'X-Relay-Signature': 'sha256='+signature})
                    r.raise_for_status()
                return store.patch('outbox', id, status='sent', sent_at=now_iso(), last_error=None)
            except Exception:
                return store.patch('outbox', id, status='delivery_uncertain',
                    last_error='No success confirmation. The receiver may have processed it; check before manually retrying with the same event ID.')

    @app.post('/integrations/leads')
    async def intake(request: Request, data: LeadInput):
        limit(request, 'intake', 60)
        if not c.inbound_token or not equal(request.headers.get('authorization', ''), 'Bearer '+c.inbound_token):
            raise HTTPException(401, 'Invalid lead-intake credentials.')
        lead, created = store.add_lead(data.model_dump())
        return {'id': lead['id'], 'created': created, 'dialed': False}

    async def signed_form(request):
        if not c.public_url or not c.twilio_token: raise HTTPException(403, 'Telephony is not configured.')
        raw = await request.body()
        if 'application/x-www-form-urlencoded' not in request.headers.get('content-type', ''): raise HTTPException(415, 'Expected a form webhook.')
        try: params = parse_qs(raw.decode('utf-8'), keep_blank_values=True, max_num_fields=150)
        except (ValueError, UnicodeError): raise HTTPException(400, 'Malformed webhook.')
        # Canonical URL is operator-controlled, never derived from forwarded Host headers.
        public = urlparse(c.public_url)
        url = 'https://' + public.hostname + request.url.path
        if request.url.query: url += '?' + request.url.query
        if not validate_signature(c.twilio_token, url, params, request.headers.get('x-twilio-signature', '')):
            raise HTTPException(403, 'Invalid provider signature.')
        return {k: vals[-1] for k, vals in params.items()}

    def signed_call(id, form):
        call = get('calls', id)
        if call['kind'] != 'twilio': raise HTTPException(403, 'Not a telephone call.')
        lead = get('leads', call['lead_id'])
        if form.get('AccountSid') != c.twilio_sid or form.get('To') != lead['phone'] or form.get('From') != c.twilio_from:
            raise HTTPException(403, 'Provider call context does not match.')
        bind_sid(call, form.get('CallSid')); return get('calls', id)

    @app.post('/twilio/voice/{id}')
    async def twiml(id: str, request: Request):
        form = await signed_form(request); call = signed_call(id, form)
        lead = get('leads', call['lead_id'])
        root = Element('Response')
        if call['status'] in PROVIDER_TERMINAL or store.suppressed(lead['phone']):
            SubElement(root, 'Hangup')
        else:
            token = media_tokens.setdefault(id, {'token': secrets.token_urlsafe(32), 'used': False, 'expires': time.monotonic()+c.max_seconds+45})
            stream = SubElement(SubElement(root, 'Connect'), 'Stream', {'url': c.public_url.replace('https://', 'wss://', 1)+'/twilio/media/'+id})
            SubElement(stream, 'Parameter', {'name': 'relayToken', 'value': token['token']})
            SubElement(root, 'Hangup')
        return Response(tostring(root, encoding='unicode'), media_type='application/xml')

    @app.post('/twilio/status/{id}')
    async def status_callback(id: str, request: Request):
        form = await signed_form(request); call = signed_call(id, form)
        status = form.get('CallStatus')
        if status not in PROVIDER_STATUS: raise HTTPException(400, 'Unknown provider status.')
        try: sequence = int(form['SequenceNumber'])
        except (KeyError, ValueError): raise HTTPException(400, 'Missing callback sequence.')
        if sequence <= call.get('provider_sequence', -1) or call['status'] in PROVIDER_TERMINAL:
            return Response(status_code=204)
        complete(id, status, provider_sequence=sequence)
        return Response(status_code=204)

    @app.websocket('/twilio/media/{id}')
    async def media(ws: WebSocket, id: str):
        # Permit documented HTTPS/WSS handshake canonicalizations, only for this exact trusted path.
        path = '/twilio/media/'+id
        origins = {c.public_url, c.public_url.replace('https://', 'wss://', 1)} if c.public_url else set()
        signature = ws.headers.get('x-twilio-signature', '')
        valid = any(validate_signature(c.twilio_token, origin+path+suffix, {}, signature) for origin in origins for suffix in ('', '/'))
        call = store.get('calls', id); token = media_tokens.get(id)
        if not valid or not call or call['kind'] != 'twilio' or not token or token['used'] or token['expires'] < time.monotonic() or call['status'] in PROVIDER_TERMINAL:
            return await ws.close(code=1008)
        await ws.accept(); stop = asyncio.Event(); started = False
        try:
            async with asyncio.timeout(8):
                while True:
                    message = await ws.receive_json()
                    if message.get('event') == 'start': break
                    if message.get('event') != 'connected': raise ValueError('Expected stream start.')
            start = message['start']
            if start.get('accountSid') != c.twilio_sid or start.get('callSid') != call['provider_sid'] or not equal(start.get('customParameters', {}).get('relayToken', ''), token['token']):
                raise ValueError('Stream binding failed.')
            fmt = start.get('mediaFormat', {})
            if fmt != {'encoding': 'audio/x-mulaw', 'sampleRate': 8000, 'channels': 1}: raise ValueError('Unsupported codec.')
            sid = start.get('streamSid')
            if not re.fullmatch(r'MZ[0-9a-fA-F]{32}', sid or ''): raise ValueError('Invalid stream identifier.')
            # Recheck after the start handshake so two handshakes cannot consume the same token.
            if token['used'] or get('calls', id)['status'] in PROVIDER_TERMINAL: raise ValueError('Stream token is no longer active.')
            token['used'] = True; sessions[id] = stop; started = True
            async def receive():
                try:
                    while True:
                        message = await ws.receive_json()
                        if message.get('event') == 'stop': return None
                        if message.get('event') == 'media':
                            if message.get('streamSid') != sid: raise ValueError('Stream changed.')
                            if message.get('media', {}).get('track', 'inbound') == 'inbound':
                                return {'type': 'audio', 'audio': message['media']['payload']}
                except WebSocketDisconnect: return None
            async def emit(event):
                if event['type'] == 'audio':
                    await ws.send_json({'event': 'media', 'streamSid': sid, 'media': {'payload': event['audio']}})
            await run_bridge(c, store, id, receive, emit, stop)
        except (WebSocketDisconnect, ValueError, KeyError, asyncio.TimeoutError):
            if started: store.patch('calls', id, error='Telephone media stream disconnected or was invalid.')
        finally:
            if started:
                await stop_phone(id)
                sessions.pop(id, None)
                latest = get('calls', id)
                if latest['status'] in PROVIDER_TERMINAL: store.enqueue(latest)
            with contextlib.suppress(Exception): await ws.close()

    app.mount('/assets', StaticFiles(directory=WEB), name='assets')
    @app.get('/')
    async def index(): return FileResponse(WEB/'index.html')
    return app
