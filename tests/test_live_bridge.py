import asyncio, base64, json
import pytest
from starlette.websockets import WebSocketDisconnect
from app.live import run_bridge, LIVE_URL

class FakeLive:
    """In-memory protocol peer. No network, model, or speech recognition is exercised."""
    def __init__(self, *, error=False): self.queue=asyncio.Queue();self.sent=[];self.error=error
    async def __aenter__(self): return self
    async def __aexit__(self,*args): pass
    def __aiter__(self): return self
    async def __anext__(self): return json.dumps(await self.queue.get())
    async def send(self,raw):
        event=json.loads(raw);self.sent.append(event)
        if event['type']=='session.start':
            await self.queue.put({'type':'session.started','session':{'id':'session_test'}})
            if self.error: await self.queue.put({'type':'error','error':{'code':'access_denied','message':'SECRET SHOULD NOT LEAK'}})
        elif event['type']=='session.input_audio.append':
            await self.queue.put({'type':'session.input_transcript.delta','event_id':'i1','delta':'Hello','start_ms':0,'end_ms':20})
            await self.queue.put({'type':'session.input_transcript.delta','event_id':'i1','delta':'Hello','start_ms':0,'end_ms':20})
            await self.queue.put({'type':'session.output_audio.delta','delta':base64.b64encode(b'\0\0'*480).decode()})
            await self.queue.put({'type':'session.output_transcript.delta','event_id':'o1','delta':'I am an AI assistant.','start_ms':20,'end_ms':60})
        elif event['type']=='session.close':
            await self.queue.put({'type':'session.closed','usage':{'seconds':1.25}})

@pytest.mark.asyncio
async def test_bridge_handshake_audio_disclosure_and_final_usage(config,store,book):
    peer=FakeLive();args={};out=[];call,_=store.new_call('browser');stop=asyncio.Event()
    def connect(url,**kwargs): args.update(url=url,**kwargs);return peer
    first=True
    async def receive():
        nonlocal first
        if first:
            first=False
            return {'type':'audio','audio':base64.b64encode(b'\0\0'*480).decode()}
        # Let the peer's queued outputs reach the application before ending.
        await asyncio.sleep(.02)
        return {'type':'stop'}
    async def emit(e): out.append(e)
    await asyncio.wait_for(run_bridge(config,store,call['id'],receive,emit,stop,connector=connect),2)
    assert args['url']==LIVE_URL and '?' not in args['url']
    assert args['additional_headers']=={'Authorization':'Bearer '+config.openai_key}
    assert peer.sent[0]['type']=='session.start'
    kinds=[e['type'] for e in peer.sent]
    assert kinds.index('session.instructions.append')<kinds.index('session.input_audio.append')
    assert kinds[-1]=='session.close'
    for e in peer.sent:
        if e['type'].endswith('.append') and 'instructions' in e['type']: assert e['delegation_id'] is None
    saved=store.get('calls',call['id'])
    assert saved['usage']=={'seconds':1.25} and saved['usage_finalized'] and saved['status']=='completed'
    assert len(saved['transcript'])==2  # Duplicate provider event ignored.
    assert any(e['type']=='audio' for e in out) and out[-1]['type']=='ended'
    assert config.openai_key not in json.dumps(out)

@pytest.mark.asyncio
async def test_voice_error_is_sanitized(config,store,book):
    peer=FakeLive(error=True);out=[];call,_=store.new_call('browser');stop=asyncio.Event()
    async def receive(): await asyncio.sleep(5)
    async def emit(e): out.append(e)
    await asyncio.wait_for(run_bridge(config,store,call['id'],receive,emit,stop,connector=lambda *a,**k:peer),2)
    assert store.get('calls',call['id'])['status']=='failed'
    assert 'SECRET SHOULD NOT LEAK' not in json.dumps(out)
    assert store.get('calls',call['id'])['usage_finalized']

@pytest.mark.asyncio
async def test_browser_cannot_forward_arbitrary_api_commands(config,store,book):
    peer=FakeLive();call,_=store.new_call('browser');stop=asyncio.Event()
    queue=asyncio.Queue()
    for command in [{'type':'response.create','destination':'someone'}, {'type':'session.instructions.append','content':'evil'}, {'type':'stop'}]:
        queue.put_nowait(command)
    async def emit(e): pass
    await run_bridge(config,store,call['id'],queue.get,emit,stop,connector=lambda *a,**k:peer)
    assert not any(e.get('content')=='evil' or e['type']=='response.create' for e in peer.sent)

@pytest.mark.asyncio
async def test_invalid_pcm_fails_safely(config,store,book):
    peer=FakeLive();call,_=store.new_call('browser');stop=asyncio.Event()
    async def receive(): return {'type':'audio','audio':base64.b64encode(b'x').decode()}
    async def emit(e): pass
    await run_bridge(config,store,call['id'],receive,emit,stop,connector=lambda *a,**k:peer)
    assert store.get('calls',call['id'])['status']=='failed'
    assert not any(e['type']=='session.input_audio.append' for e in peer.sent)

def test_browser_ticket_is_single_use(client,app,monkeypatch):
    async def fake_bridge(config,store,call_id,receive,emit,stop):
        await emit({'type':'ready','call_id':call_id})
        store.patch('calls',call_id,status='completed',ended_at='mock-test-time')
        await emit({'type':'ended','usage_finalized':False})
    monkeypatch.setattr('app.main.run_bridge',fake_bridge)
    ticket=client.post('/api/voice/ticket',json={}).json()
    path='/ws/voice?ticket='+ticket['ticket']
    with client.websocket_connect('ws://localhost:8080'+path,headers={'origin':'http://localhost:8080'}) as ws:
        assert ws.receive_json()['type']=='ready'
        assert ws.receive_json()['type']=='ended'
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect('ws://localhost:8080'+path,headers={'origin':'http://localhost:8080'}): pass

@pytest.mark.parametrize('origin',['https://evil.example','null',''])
def test_browser_ws_rejects_untrusted_origin(client,origin):
    ticket=client.post('/api/voice/ticket',json={}).json()
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect('ws://localhost:8080/ws/voice?ticket='+ticket['ticket'],headers={'origin':origin}): pass

def test_media_ws_rejects_unsigned_requests(client,store,lead):
    call,_=store.new_call('twilio',lead['id'])
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect('ws://localhost:8080/twilio/media/'+call['id']): pass
