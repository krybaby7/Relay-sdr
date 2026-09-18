"""Run against an isolated, no-API-key local instance. Requires Playwright + Chromium.
RELAY_TEST_URL and RELAY_TEST_TOKEN select the instance. This never enables dialing.
"""
import json,os,re
import httpx
from pathlib import Path
from playwright.sync_api import sync_playwright

URL=os.getenv('RELAY_TEST_URL','http://localhost:8765')
TOKEN=os.environ['RELAY_TEST_TOKEN']
OUT=Path(os.getenv('RELAY_SCREENSHOTS','/mnt/data/relay-screenshots'));OUT.mkdir(exist_ok=True,parents=True)
errors=[];checks=[]
OFFLINE=os.getenv('RELAY_OFFLINE_BROWSER')=='true'
with sync_playwright() as p:
    browser=p.chromium.launch(executable_path=os.getenv('CHROMIUM_PATH','/usr/bin/chromium'),headless=True,args=['--no-sandbox'])
    page=browser.new_page(viewport={'width':1440,'height':1040},device_scale_factor=1)
    page.on('pageerror',lambda e:errors.append(str(e)))
    if OFFLINE:
        # Managed Chromium blocks navigation, so render owned local assets without changing
        # browser policy. An explicit Python bridge sends only this test app's relative API
        # requests to the isolated localhost server. This does NOT test browser networking,
        # CORS, microphone capture, WebSockets, or actual browser file downloads.
        root=Path(__file__).resolve().parent.parent/'web'
        html=(root/'index.html').read_text()
        html=re.sub(r'<link[^>]+>|<script[^>]*>.*?</script>','',html,flags=re.S)
        page.set_content(html)
        page.add_style_tag(content=(root/'styles.css').read_text())
        def test_fetch(args):
            path,options=args
            assert path.startswith('/api/'), 'Only this local app API is exposed to the DOM test.'
            response=httpx.request(options.get('method','GET'),URL+path,headers=options.get('headers'),content=options.get('body'))
            return {'status':response.status_code,'body':response.json()}
        page.expose_function('__testFetch',test_fetch)
        page.add_script_tag(content="""
          const testStorage=new Map();
          Object.defineProperty(window,'sessionStorage',{value:{getItem:k=>testStorage.get(k)||null,setItem:(k,v)=>testStorage.set(k,v),removeItem:k=>testStorage.delete(k)}});
          window.fetch=async(path,options={})=>{const r=await window.__testFetch([path,options]);return {ok:r.status>=200&&r.status<300,status:r.status,json:async()=>r.body};};
          if(!crypto.randomUUID)crypto.randomUUID=()=>Array.from(crypto.getRandomValues(new Uint8Array(24))).map(x=>x.toString(16).padStart(2,'0')).join('');
          const makeURL=URL.createObjectURL.bind(URL);URL.createObjectURL=blob=>{window.__lastExport=blob;return makeURL(blob);};
          document.addEventListener('click',e=>{if(e.target.closest('a[download]'))e.preventDefault();});
        """)
        page.add_script_tag(content=(root/'app.js').read_text())
    else:
        page.goto(URL)
    page.locator('#token').fill(TOKEN);page.get_by_role('button',name='Open workspace').click()
    page.wait_for_selector('#workspace:not(.hidden)')
    page.locator('h1').filter(has_text='A better conversation').wait_for()
    assert page.get_by_text('OUTBOUND OFF',exact=True).is_visible();checks.append('Token login and safe default status')
    page.screenshot(path=str(OUT/'01-overview-empty-desktop.png'),full_page=True)
    page.locator('.nav-item[href="#leads"]').click()
    page.get_by_role('button',name='Load fictional samples').click()
    page.get_by_text('Maya Hassan',exact=True).wait_for();checks.append('Sample import renders three labeled contacts')
    page.locator('button[data-action="preflight"]').first.click()
    page.locator('#dialog[open]').wait_for()
    assert page.get_by_role('button',name='Confirm real call').is_disabled()
    assert page.get_by_text('Sample leads can never receive real calls. Add your own test lead.').is_visible();checks.append('Preflight blocks fictional contacts')
    page.get_by_role('button',name='Cancel',exact=True).click()
    page.get_by_role('button',name='Add lead',exact=True).click()
    page.locator('#lead-name').fill('<img src=x onerror=alert(1)>')
    page.locator('#lead-company').fill('Escaping test')
    page.locator('#lead-phone').fill('+12025550131')
    page.get_by_role('button',name='Save contact',exact=True).click()
    page.get_by_text('<img src=x onerror=alert(1)>',exact=True).wait_for()
    assert page.locator('#content img').count()==0;checks.append('Lead form, persistence, and HTML escaping')
    page.get_by_role('button',name='Import CSV').click()
    page.locator('#csv-text').fill('name,phone,company,consent\nCSV Lead,+12025550132,CSV Company,false\nInvalid,123,Oops,false')
    page.get_by_role('button',name='Import contacts',exact=True).click()
    page.get_by_text('1 added · 0 duplicates preserved · 1 row errors',exact=True).wait_for();checks.append('CSV partial success and row error feedback')
    page.get_by_role('button',name='Close dialog').click()
    page.locator('.nav-item[href="#lab"]').click()
    page.get_by_role('heading', name='Teach both AIs in one place.').wait_for()
    page.locator('#pb-company').fill('Demo Workspace')
    page.locator('#pb-product').fill('A fictional demonstration product used only for a user-interface test. No real sales claims.')
    page.get_by_role('button', name='Save playbook').click()
    page.get_by_text('Playbook saved. Active calls keep their original playbook snapshot.', exact=True).wait_for()
    assert page.locator('#pb-company').input_value()=='Demo Workspace';checks.append('Lab playbook save and round-trip values')
    assert page.get_by_text('GPT-Live', exact=False).first.is_visible()
    assert page.get_by_text('Grok 4.6', exact=False).first.is_visible()
    assert page.get_by_role('button', name='Start voice test').is_disabled();checks.append('Real voice disabled without server key')
    page.get_by_role('button', name='Run scripted preview', exact=True).click()
    page.get_by_text('A conversation, with a next step.',exact=True).wait_for()
    assert page.locator('#transcript .utterance').count()==9;checks.append('Scripted preview appears and remains labeled')
    page.evaluate("window.scrollTo(0,0);document.querySelector('#toast').classList.remove('visible')")
    page.wait_for_timeout(250)
    page.screenshot(path=str(OUT/'02-voice-lab-desktop.png'),full_page=True)
    page.locator('.nav-item[href="#calls"]').click()
    page.get_by_role('button',name='Review',exact=False).first.click()
    page.locator('#dialog[open]').wait_for()
    assert page.get_by_text('MEETING · REQUEST ONLY',exact=True).is_visible();checks.append('Call review marks meeting as request only')
    if OFFLINE:
        page.get_by_role('button',name='Export JSON',exact=True).click()
        export=json.loads(page.evaluate('window.__lastExport.text()'))
    else:
        with page.expect_download() as download:
            page.get_by_role('button',name='Export JSON',exact=True).click()
        path=download.value.path();export=json.loads(Path(path).read_text())
    assert export['kind']=='simulation';checks.append('Call JSON export payload generation')
    page.get_by_role('button',name='Close dialog').click()
    page.locator('.nav-item[href="#connections"]').click()
    page.get_by_text('No real-call outcomes waiting.',exact=True).wait_for();checks.append('Simulation does not enter external outbox')
    page.screenshot(path=str(OUT/'03-connections-desktop.png'),full_page=True)
    page.locator('.nav-item[href="#overview"]').click();page.locator('.nav-item.active[href="#overview"]').wait_for();page.evaluate('window.scrollTo(0,0)');page.screenshot(path=str(OUT/'04-overview-with-preview-desktop.png'),full_page=True)
    # Check all views at a narrow phone viewport; horizontal tables may scroll within their own containers.
    page.set_viewport_size({'width':390,'height':844})
    for tab in ['overview','leads','lab','calls','connections']:
        if OFFLINE:
            page.evaluate('(tab)=>{location.hash=tab}',tab)
            page.locator('.nav-item.active[href="#'+tab+'"]').wait_for()
        else: page.goto(URL+'/#'+tab)
        page.wait_for_selector('#workspace:not(.hidden)')
        page.wait_for_function("document.querySelector('#content').children.length > 0")
        dimensions=page.evaluate('({width:innerWidth,scroll:document.documentElement.scrollWidth})')
        assert dimensions['scroll']<=dimensions['width'],(tab,dimensions)
        checks.append('No page-wide overflow on mobile: '+tab)
        page.evaluate("window.scrollTo(0,0);document.querySelector('#toast').classList.remove('visible')")
        page.wait_for_timeout(250)
        if tab in ('overview','lab'):page.screenshot(path=str(OUT/f'05-mobile-{tab}.png'),full_page=True)
    page.locator('.avatar[data-action="lock-workspace"]').click()
    page.wait_for_selector('#login:not(.hidden)')
    assert not page.locator('#workspace').is_visible();checks.append('Mobile-accessible workspace lock clears the UI session')
    assert not errors,errors
    checks.append('No browser JavaScript exceptions during the exercised flows')
    browser.close()
(OUT/'ui-results.json').write_text(json.dumps({'mode':'offline DOM with local HTTP API bridge' if OFFLINE else 'browser end-to-end','checks':checks,'errors':errors},indent=2))
print(json.dumps({'checks_passed':len(checks),'errors':errors,'screenshots':str(OUT)},indent=2))
