const $ = (s, root=document) => root.querySelector(s);
const $$ = (s, root=document) => [...root.querySelectorAll(s)];
const esc = v => String(v ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const paths = {
 overview:'<rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/>',
 leads:'<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2m20 0v-2a4 4 0 0 0-3-3.87"/><circle cx="9" cy="7" r="4"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/>',
 lab:'<rect x="9" y="2" width="6" height="13" rx="3"/><path d="M5 10v2a7 7 0 0 0 14 0v-2m-7 9v3m-4 0h8"/>',
 playbook:'<path d="M4 3h6a3 3 0 0 1 3 3v15a4 4 0 0 0-4-3H4zM13 6a3 3 0 0 1 3-3h5v15h-4a4 4 0 0 0-4 3"/>',
 calls:'<path d="m5 3 4 1 1 5-3 2a15 15 0 0 0 6 6l2-3 5 1 1 4c0 1-1 2-2 2C9 21 3 15 3 5c0-1 1-2 2-2Z"/>',
 connections:'<path d="m9 15 6-6m-5-3 2-2a5 5 0 0 1 7 7l-2 2m-3 5-2 2a5 5 0 0 1-7-7l2-2"/>',
 shield:'<path d="m12 3 8 3v6c0 5-8 9-8 9s-8-4-8-9V6z"/><path d="m8 12 3 3 5-6"/>',
 arrow:'<path d="M5 12h14m-6-6 6 6-6 6"/>',
 check:'<path d="m5 12 4 4L19 6"/>',
 plus:'<path d="M12 4v16M4 12h16"/>',
 upload:'<path d="M4 16v4h16v-4M12 16V3m-5 5 5-5 5 5"/>',
 clock:'<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
 message:'<path d="M21 11a8 8 0 0 1-8 8H6l-4 3V5a3 3 0 0 1 3-3h11a5 5 0 0 1 5 5z"/><path d="M6 8h10M6 12h7"/>',
 stop:'<rect x="5" y="5" width="14" height="14" rx="2"/>',
 download:'<path d="M4 16v4h16v-4M12 3v13m-5-5 5 5 5-5"/>',
 circle:'<circle cx="12" cy="12" r="9"/><path d="m10 8 6 4-6 4z"/>',
};
const icon = name => `<svg viewBox="0 0 24 24" aria-hidden="true">${paths[name] || paths.connections}</svg>`;
const orb = () => '<span class="orbit-ring"></span><span class="orbit-ring second"></span><div class="orb"><span></span><span></span><span></span><span></span><span></span></div>';
const titles = {overview:'Overview',leads:'Leads',lab:'Voice lab',playbook:'Playbook',calls:'Call history',connections:'Connections'};
let token = sessionStorage.getItem('relay-token') || '';
let data = null, tab = 'overview', query = '', toastTimer, currentDetail = null;
let voice = {running:false, ready:false, muted:false, ws:null, stream:null, ctx:null, node:null, callId:null, nextTime:0, sources:new Set(), generation:0};
let labState = {label:'Ready for a conversation',message:'Practice your pitch, hear the agent, and refine your playbook before a real call.',fragments:[],kind:'idle'};

async function api(path, options={}) {
 const response = await fetch(path, {...options, headers:{'Authorization':`Bearer ${token}`,'Content-Type':'application/json',...options.headers}});
 let body; try { body=await response.json(); } catch { body={detail:'The server returned an unreadable response.'}; }
 if (!response.ok) {
   const detail=body.detail;
   const text=Array.isArray(detail)?detail.map(x=>typeof x==='string'?x:`${x.field || ''}: ${x.message || 'Invalid input'}`).join('\n'):detail || 'Request failed.';
   const e=new Error(text); e.status=response.status; throw e;
 }
 return body;
}
const post = (path, body={}) => api(path,{method:'POST',body:JSON.stringify(body)});
function toast(message) { clearTimeout(toastTimer); const t=$('#toast'); t.textContent=message; t.classList.add('visible'); toastTimer=setTimeout(()=>t.classList.remove('visible'),6500); }
function badge(status) {
 const labels={do_not_call:'Do not call',new:'New lead',not_interested:'Not interested',wrong_number:'Wrong number',no_answer:'No answer',in_progress:'In progress',pending_review:'Review needed',needs_human_confirmation:'Needs confirmation',delivery_uncertain:'Check delivery'};
 const key=String(status || 'unreviewed').replaceAll('-','_');
 const good=['qualified','sent','completed'].includes(key), bad=['do_not_call','failed','unknown','delivery_uncertain'].includes(key);
 const amber=['callback','pending_review','needs_human_confirmation','interrupted'].includes(key);
 return `<span class="chip ${good?'green':bad?'red':amber?'amber':''}">${esc(labels[key] || key.replaceAll('_',' '))}</span>`;
}
function date(value) { return value ? new Date(value).toLocaleString(undefined,{month:'short',day:'numeric',hour:'2-digit',minute:'2-digit'}) : '—'; }
function initials(name) { return String(name || 'Test').split(/\s+/).slice(0,2).map(s=>s[0]).join('').toUpperCase(); }
const leadName = call => data.leads.find(l=>l.id===call.lead_id)?.name || (call.kind==='simulation'?'Scripted preview':'Browser practice');
const kindLabel = kind => ({twilio:'Telephone',browser:'Browser · AI',simulation:'Scripted demo'}[kind] || kind);
const activeStatus = status => ['created','dialing','queued','initiated','ringing','in-progress','connected','ending'].includes(status);
function pageHead(title, subtitle, actions='', eyebrow='WORKSPACE') { return `<div class="page-head"><div><span class="eyebrow">${esc(eyebrow)}</span><h1>${esc(title)}</h1><p>${esc(subtitle)}</p></div><div class="row">${actions}</div></div>`; }
function empty(title, sub, action='', name='calls') { return `<div class="empty"><div class="empty-icon">${icon(name)}</div><strong>${esc(title)}</strong><p>${esc(sub)}</p>${action}</div>`; }
function renderNav(){
 $('#nav').innerHTML=Object.entries(titles).map(([id,title])=>`<a class="nav-item ${tab===id?'active':''}" href="#${id}" ${tab===id?'aria-current="page"':''}>${icon(id)}${esc(title)}${id==='leads'?`<span class="count">${data?.leads.length || 0}</span>`:''}</a>`).join('');
 $('#breadcrumb').textContent=titles[tab];
 $('#outbound-chip').textContent=data.config.outbound_enabled?'OUTBOUND ENABLED':'OUTBOUND OFF';
 $('#outbound-chip').className='chip '+(data.config.outbound_enabled?'amber':'');
}
async function refresh(renderPage=false) { data=await api('/api/state'); renderNav(); if(renderPage)render(); }
function render() { if(!data)return; renderNav(); $('#content').innerHTML=({overview,leads,lab,playbook,calls,connections}[tab])(); if(tab==='lab')renderTranscript(); }
function overview(){
 const phone=data.calls.filter(c=>c.kind==='twilio'), realLeads=data.leads.filter(l=>!l.sample), qualified=phone.filter(c=>c.outcome==='qualified');
 const requests=phone.reduce((n,c)=>n+c.requests.filter(r=>r.type==='meeting').length,0);
 const done=data.playbook.approved, voiceReady=data.connectors.find(c=>c.id==='browser').configured, twilioReady=data.connectors.find(c=>c.id==='twilio').configured;
 const stats=[['Leads in workspace',realLeads.length,`${data.leads.filter(l=>l.sample).length} sample leads excluded`,'leads'],['Telephone attempts',phone.length,'Practice sessions excluded','calls'],['Qualified calls',qualified.length,'Based on saved call outcomes','check'],['Meeting requests',requests,'Not confirmed calendar bookings','clock']];
 const steps=[['01','Shape your sales playbook','Product facts, qualification, and tone.',done,'playbook','Edit playbook'],['02','Test the conversation','Use your microphone or a scripted preview.',data.calls.some(c=>c.kind==='browser'),'lab','Open voice lab'],['03','Connect your calling provider','Twilio credentials + an approved test number.',twilioReady,'connections','View setup']];
 return pageHead('A better conversation starts here.','Your agent, leads, and next steps in one place.',`<button class="btn" data-action="add-lead">${icon('plus')} Add lead</button>`,'YOUR SALES WORKSPACE')+
 `<section class="hero"><div><span class="eyebrow">INTRODUCING YOUR VOICE AGENT</span><h2>Less chasing. More listening.</h2><p>Give your agent a clear playbook. Let it qualify interest, capture the details, and collect the next step.</p><div class="row"><button class="btn primary" data-nav="lab">${icon('lab')} Try your agent</button><button class="btn" data-nav="playbook">Edit playbook ${icon('arrow')}</button></div></div><div class="hero-visual">${orb()}<div class="floating-tag">✦ GPT-Live voice</div><div class="floating-tag bottom">A clear next step ↗</div></div></section>
 <div class="stats">${stats.map(([title,num,hint,i])=>`<section class="stat"><div class="stat-top"><span>${title}</span>${icon(i)}</div><strong>${num}</strong><p class="hint">${hint}</p></section>`).join('')}</div>
 <div class="grid-main"><section class="card"><div class="card-head"><div><h3>Recent conversations</h3><p>Actual workspace activity, including labeled practice.</p></div><button class="text-btn" data-nav="calls">View all ↗</button></div>${data.calls.length?callTable(data.calls.slice(0,4),true):empty('Your first conversation is ahead.','Explore a scripted preview. No API key, microphone, or telephone call needed.',`<button class="btn sm" data-action="demo">${icon('circle')} Run a preview</button>`)}<div class="safe-note">${icon('shield')}Telephone calls require your confirmation. New workspaces start with live dialing switched off.</div></section>
 <section class="card"><div class="card-head"><div><h3>Make it your agent</h3><p>Three steps to a controlled pilot.</p></div><span class="chip green">${[done,voiceReady,twilioReady].filter(Boolean).length} / 3 CONFIGURED</span></div><div class="card-content">${steps.map(([n,title,sub,checked,to,action])=>`<div class="step"><span class="step-number ${checked?'done':''}">${checked?'✓':n}</span><div class="step-text"><strong>${title}</strong><p>${sub}</p></div><button class="text-btn" data-nav="${to}">${action} ↗</button></div>`).join('')}</div></section></div>
 <section class="card pad section-space"><div class="row between wrap"><div><h3>One agent. Separate connections.</h3><p class="hint">A CRM brings the context. A calling provider carries the conversation.</p></div><button class="text-btn" data-nav="connections">Manage connections ↗</button></div><div class="flow section-space"><div class="flow-node"><strong>Your leads</strong><span>CSV · lead intake API</span></div><span class="flow-arrow">→</span><div class="flow-node"><strong>Relay SDR</strong><span>GPT-Live + sales tools</span></div><span class="flow-arrow">→</span><div class="flow-node"><strong>Calling channel</strong><span>Browser · Twilio</span></div><span class="flow-arrow">→</span><div class="flow-node"><strong>Next step</strong><span>Notes · human follow-up</span></div></div></section>`;
}
function callTable(items,compact=false){
 return `<div class="table-wrap"><table><thead><tr><th>CONVERSATION</th><th>STATUS</th>${compact?'':'<th>OUTCOME</th>'}<th></th></tr></thead><tbody>${items.map(c=>`<tr><td><div class="person"><span class="initials">${esc(initials(leadName(c)))}</span><div><strong>${esc(leadName(c))}</strong><p>${kindLabel(c.kind)} · ${date(c.created_at)}</p></div></div></td><td>${badge(c.status)}</td>${compact?'':`<td>${c.outcome?badge(c.outcome):'<span class="small">No outcome saved</span>'}</td>`}<td><button class="btn sm" data-action="call-detail" data-id="${c.id}">Review ↗</button></td></tr>`).join('')}</tbody></table></div>`;
}
function leads(){
 const filtered=data.leads.filter(l=>`${l.name} ${l.company} ${l.phone}`.toLowerCase().includes(query.toLowerCase()));
 return pageHead('The right conversation, with the right lead.','Bring your own contacts. Record permission before any live call.',`<button class="btn" data-action="import">${icon('upload')} Import CSV</button><button class="btn primary" data-action="add-lead">${icon('plus')} Add lead</button>`,'YOUR PIPELINE')+
 `<div class="toolbar"><input id="lead-search" placeholder="Search name, company, or number…" aria-label="Search leads" value="${esc(query)}"><span class="caption">${data.leads.length} contacts · ${data.leads.filter(l=>l.sample).length} fictional samples</span></div><section class="card">${filtered.length?`<div class="table-wrap"><table><thead><tr><th>CONTACT</th><th>NUMBER / TIMEZONE</th><th>PERMISSION</th><th>STATUS</th><th>ACTIONS</th></tr></thead><tbody>${filtered.map(l=>`<tr><td><div class="person"><span class="initials">${esc(initials(l.name))}</span><div><strong>${esc(l.name)}</strong><p>${esc(l.company || 'No company')} ${l.sample?'· FICTIONAL':''}</p></div></div></td><td>${esc(l.phone)}<p class="small">${esc(l.timezone)}</p></td><td>${l.sample?'<span class="chip blue">Sample only</span>':l.consent?'<span class="chip green">Recorded</span>':'<span class="chip amber">Not recorded</span>'}</td><td>${badge(l.status)}</td><td><div class="row"><button class="btn sm" data-action="edit-lead" data-id="${l.id}">Edit</button><button class="btn sm" data-action="preflight" data-id="${l.id}">${icon('calls')} Call</button></div></td></tr>`).join('')}</tbody></table></div>`:empty(query?'No matching contacts.':'Start with a small, approved list.','Add a contact manually, import a CSV, or explore fictional sample leads.',`<button class="btn sm" data-action="samples">Load fictional samples</button>`,'leads')}</section><div class="info-box section-space">Sample contacts cannot be dialed. Imported contacts are not treated as having permission unless both consent and its source, date, and scope are supplied. The number allowlist lives on your server.</div>`;
}
function lab(){
 const configured=data.connectors.find(c=>c.id==='browser').configured;
 return pageHead('Meet your agent. Before your leads do.','Practice the conversation without placing a telephone call.','', 'VOICE LAB')+
 `<div class="lab-grid"><div class="stack"><section class="card"><div class="voice-stage ${voice.ready?'live':''}" id="voice-stage"><span class="chip ${voice.ready?'green':''}" id="voice-chip">${voice.ready?'LIVE BROWSER SESSION':labState.kind==='demo'?'SCRIPTED PREVIEW':'BROWSER PRACTICE'}</span><div class="orbit">${orb()}</div><h2 id="voice-label">${esc(labState.label)}</h2><p id="voice-message">${esc(labState.message)}</p><div class="row" style="justify-content:center"><button class="btn primary ${voice.running?'hidden':''}" data-action="start-voice" id="start-voice" ${configured?'':'disabled'}>${icon('lab')} Start voice test</button><button class="btn ${!voice.running?'hidden':''}" data-action="mute-voice" id="mute-voice">${voice.muted?'Unmute':'Mute'}</button><button class="btn danger ${!voice.running?'hidden':''}" data-action="stop-voice" id="stop-voice">${icon('stop')} End test</button></div></div><div class="safe-note">${icon('shield')}Browser practice saves its own notes. It never calls, updates, or suppresses a real lead.</div></section>
 <section class="card pad"><label for="voice-lead">Optional lead context</label><select id="voice-lead" ${voice.running?'disabled':''}><option value="">Generic practice conversation</option>${data.leads.map(l=>`<option value="${l.id}">${esc(l.name)}${l.sample?' · sample':''}</option>`).join('')}</select><p class="hint">The context helps you rehearse. It is not permission to contact this person.</p><div class="form-section">NO KEY? EXPLORE THE FLOW.</div><button class="btn full" data-action="demo" ${voice.running?'disabled':''}>${icon('circle')} Run scripted preview</button><p class="hint">Text-only example. No model request, microphone access, chargeable session, or telephone call.</p></section>
 ${configured?'':`<div class="info-box amber">For an actual voice test, set <code>OPENAI_API_KEY</code> in the server’s <code>.env</code> file and restart. Your account must have access to the configured Live and backend models.</div>`}</div>
 <section class="card"><div class="card-head"><div><h3>The conversation</h3><p id="transcript-caption">${labState.kind==='demo'?'Scripted example · not AI-generated':'Transcript fragments appear as they arrive.'}</p></div>${icon('message')}</div><div id="transcript" class="transcript"></div><div class="safe-note">${icon('shield')}This app stores text notes, not audio recordings. A real voice test sends audio to OpenAI and uses billable API services.</div></section></div>`;
}
function renderTranscript(){
 const container=$('#transcript'); if(!container)return;
 if(!labState.fragments.length){container.innerHTML='<div class="transcript-empty">'+icon('message')+'<span>A space for the conversation.<br>Your transcript will appear here.</span></div>';return;}
 const groups=[];
 for(const f of labState.fragments){const last=groups.at(-1);if(last&&last.role===f.role)last.text+=f.text;else groups.push({...f});}
 container.innerHTML=groups.map(f=>`<div class="utterance ${f.role==='lead'?'lead':'agent'}"><span class="speaker">${f.role==='lead'?'You / lead':'AI agent'}</span><p>${esc(f.text)}</p></div>`).join('');
 container.scrollTop=container.scrollHeight;
}
function playbook(){
 const p=data.playbook;
 const field=(name,label,rows=3,hint='')=>`<div class="field wide"><label for="pb-${name}">${label}</label><textarea id="pb-${name}" name="${name}" rows="${rows}" required>${esc(p[name])}</textarea>${hint?`<p class="hint">${hint}</p>`:''}</div>`;
 return pageHead('Give your agent a point of view.','Define what it can say, what it should learn, and when it can call.',`<span class="chip ${p.approved?'green':'amber'}">${p.approved?'APPROVED PLAYBOOK':'DRAFT PLAYBOOK'}</span>`,'SALES PLAYBOOK')+
 `<form id="playbook-form" class="card pad"><div class="form-grid"><div class="field"><label for="pb-company">Company name</label><input id="pb-company" name="company" value="${esc(p.company)}" required maxlength="160"></div><div class="field"><label for="pb-agent">Agent name</label><input id="pb-agent" name="agent_name" value="${esc(p.agent_name)}" required maxlength="60"></div>${field('product','What are you offering?',3,'Explain your product, its real value, and its limits. The agent must not invent missing details.')}${field('customer_profile','Who is a good fit?',2)}${field('qualification','What should the agent find out?',3)}${field('facts','Approved facts, pricing, and boundaries',4,'Only put verified company information here. No pricing claims are approved in the default playbook.')}${field('goal','What is the next step?',2,'This pilot can save a meeting or human-callback request. It cannot book a time or transfer the call.')}</div>
 <div class="form-section">VOICE & CONVERSATION</div><div class="form-grid"><div class="field"><label for="pb-lang">Default language</label><input id="pb-lang" name="language" value="${esc(p.language)}" required></div><div class="field"><label for="pb-voice">Voice</label><select id="pb-voice" name="voice"><option value="marin" ${p.voice==='marin'?'selected':''}>Marin</option><option value="cedar" ${p.voice==='cedar'?'selected':''}>Cedar</option></select></div>${field('tone','Tone and speaking style',2)}</div>
 <div class="form-section">CALLING WINDOW · LEAD’S LOCAL TIMEZONE</div><div class="form-grid"><div class="field"><label for="start-hour">Start hour (inclusive)</label><input id="start-hour" name="start_hour" type="number" min="0" max="23" value="${p.start_hour}" required></div><div class="field"><label for="end-hour">End hour (exclusive)</label><input id="end-hour" name="end_hour" type="number" min="1" max="24" value="${p.end_hour}" required></div><div class="field wide"><label>Allowed days</label><div class="days">${['Mon','Tue','Wed','Thu','Fri','Sat','Sun'].map((d,i)=>`<label class="day"><input type="checkbox" name="weekdays" value="${i}" ${p.weekdays.includes(i)?'checked':''}><span>${d}</span></label>`).join('')}</div><p class="hint">Choose appropriate days and hours for your leads. These settings are not a legal-compliance determination.</p></div></div>
 <div class="form-footer"><label class="checkbox"><input type="checkbox" name="approved" ${p.approved?'checked':''}><span>I have reviewed these facts and approve this playbook for the pilot.<br><span class="hint">Consent, allowlist, and per-call confirmation are still required.</span></span></label><button class="btn primary" type="submit">Save playbook ${icon('check')}</button></div><p class="error" id="playbook-error" role="alert"></p></form>`;
}
function calls(){
 return pageHead('Every conversation, with its context.','Review qualification notes, transcript fragments, and requests that need a human.','', 'CALL HISTORY')+
 `<section class="card"><div class="card-head"><div><h3>Conversation log</h3><p>${data.calls.length} records · practice is labeled separately from telephone calls</p></div></div>${data.calls.length?callTable(data.calls):empty('Nothing to review yet.','Run a scripted preview, test your agent, or place an approved pilot call.',`<button class="btn sm" data-nav="lab">Open voice lab ↗</button>`)}</section><div class="info-box section-space">“Completed” describes a connection, not a successful sale. Meeting requests still need human confirmation. An “unknown” telephone state blocks further dialing until provider state is reconciled.</div>`;
}
function connections(){
 const keys={browser:['OPENAI_API_KEY','LIVE_MODEL','BACKEND_MODEL'],twilio:['TWILIO_ACCOUNT_SID','TWILIO_AUTH_TOKEN','TWILIO_FROM_NUMBER','PUBLIC_BASE_URL','ALLOWED_NUMBERS','ENABLE_OUTBOUND'],inbound:['INBOUND_LEAD_TOKEN'],outcome:['OUTCOME_WEBHOOK_URL','OUTCOME_WEBHOOK_SECRET']};
 const icons={browser:'lab',twilio:'calls',inbound:'leads',outcome:'connections'};
 return pageHead('Bring your tools. Keep the boundaries clear.','Voice connections and data connections do different jobs.','', 'CONNECTIONS')+
 `<div class="connector-grid">${data.connectors.map(c=>`<section class="card pad connector"><div class="row between"><span class="connector-icon">${icon(icons[c.id])}</span><span class="chip ${c.configured?'green':''}">${c.configured?'CONFIGURED · UNVERIFIED':'NOT CONFIGURED'}</span></div><h3>${esc(c.name)}</h3><p>${esc(c.detail)}</p><div class="config-keys"><span>SERVER ENVIRONMENT</span><div>${keys[c.id].map(k=>`<code>${k}</code>`).join(' ')}</div></div></section>`).join('')}</div>
 <div class="info-box section-space"><strong>Connecting a CRM does not give the agent access to its phone calls.</strong> The first implemented phone connector is Twilio. Another calling app needs a supported outbound-call and live-audio API plus a dedicated adapter. This version does not control arbitrary apps, WhatsApp, a phone’s SIM dialer, or an existing softphone.</div>
 <section class="card pad section-space"><h3>Lead intake, without automatic dialing</h3><p class="hint">A CRM or automation tool can submit a contact with the separate intake token. A duplicate number is preserved rather than overwritten.</p><pre>POST /integrations/leads\nAuthorization: Bearer YOUR_INBOUND_LEAD_TOKEN\nContent-Type: application/json\n\n{"name":"Test contact","phone":"+12025550101",\n "timezone":"Africa/Cairo","consent":false}</pre><p class="hint">A successful response includes <code>dialed: false</code>. To record permission, include <code>consent: true</code> and a factual <code>consent_note</code> with the source, date, and scope.</p></section>
 <section class="card pad section-space"><div class="row between"><div><h3>Outcome delivery outbox</h3><p class="hint">Review the real call’s notes before sharing them with your configured endpoint.</p></div><span class="chip">${data.outbox.filter(e=>e.status!=='sent').length} TO REVIEW</span></div>${data.outbox.length?data.outbox.map(e=>`<article class="outbox-item"><div class="row between wrap"><code>${esc(e.id)}</code>${badge(e.status)}</div><p>${esc(e.payload.summary || 'No conversation summary was saved.')}</p><div class="row wrap"><button class="btn sm" data-action="call-detail" data-id="${e.id}">Review call</button><button class="btn sm" data-action="deliver" data-id="${e.id}" ${e.status==='sent'?'disabled':''}>${e.status==='delivery_uncertain'?'Review retry':'Approve delivery'} ↗</button></div>${e.last_error?`<p class="error">${esc(e.last_error)}</p>`:''}</article>`).join(''):empty('No real-call outcomes waiting.','Browser tests and scripted previews never enter the external-delivery outbox.','','connections')}</section>
 <section class="card pad section-space"><h3>Pilot limits</h3><div class="call-meta"><div><span>Call duration cap</span>${data.config.max_seconds} seconds</div><div><span>Telephone attempts per UTC day</span>${data.config.max_daily}</div><div><span>Concurrent sessions</span>${data.config.max_concurrent}</div><div><span>Allowlisted numbers</span>${data.config.allowlist_count}</div></div><p class="hint">Keys are configured on the server, never in this page. Presence of credentials is not proof of account access or a successful integration test.</p></section>`;
}
function openDialog(title,sub,html){$('#dialog-content').innerHTML=`<div class="dialog-head"><h2>${esc(title)}</h2><button class="close-dialog" data-action="close-dialog" aria-label="Close dialog">×</button></div>${sub?`<p class="dialog-sub">${esc(sub)}</p>`:''}${html}`;if(!$('#dialog').open)$('#dialog').showModal();}
function leadDialog(id){
 const l=id?data.leads.find(x=>x.id===id):{name:'',company:'',phone:'',timezone:'Africa/Cairo',language:'English',notes:'',consent:false,consent_note:''};
 const input=(name,label,type='text')=>`<div class="field"><label for="lead-${name}">${label}</label><input id="lead-${name}" name="${name}" type="${type}" value="${esc(l[name])}" ${['name','phone','timezone','language'].includes(name)?'required':''} ${id&&name==='phone'?'readonly':''}></div>`;
 openDialog(id?'Contact details':'Add a lead','Use a number with its country code. Add your own test number first.',`<form id="lead-form" data-id="${id || ''}" class="dialog-form"><div class="form-grid">${input('name','Full name')}${input('company','Company')}${input('phone','Phone number (E.164)','tel')}${input('timezone','Timezone (IANA)')}${input('language','Conversation language')}<div class="field wide"><label for="lead-notes">Context notes</label><textarea id="lead-notes" name="notes">${esc(l.notes)}</textarea></div><div class="field wide"><label class="checkbox"><input type="checkbox" name="consent" ${l.consent?'checked':''} ${l.opted_out?'disabled':''}><span>Permission for AI sales calling has been recorded.</span></label>${l.opted_out?'<p class="error">This number is permanently suppressed in this workspace.</p>':''}</div><div class="field wide"><label for="consent-note">Permission evidence: source, date, and scope</label><textarea id="consent-note" name="consent_note" placeholder="Describe real permission, including whether AI sales calls are covered.">${esc(l.consent_note)}</textarea><p class="hint">Only record permission you actually have. This app does not verify the evidence or certify legal compliance.</p></div></div><p id="lead-error" class="error" role="alert"></p><div class="dialog-actions">${id&&!l.opted_out?`<button class="btn danger" type="button" data-action="suppress" data-id="${id}">Do not call</button>`:''}<button class="btn primary" type="submit">Save contact</button></div></form>`);
}
function importDialog(){
 openDialog('Import your contacts','UTF-8 CSV with name and phone columns. Up to 1,000 rows per import.',`<form id="import-form"><div class="row"><input type="file" id="csv-file" accept=".csv,text/csv" aria-label="Choose CSV file"></div><p class="hint">Optional columns: company, timezone, language, notes, consent, consent_note. Duplicates do not overwrite existing contacts.</p><label for="csv-text" style="margin-top:17px">CSV content</label><textarea id="csv-text" rows="9" required placeholder="name,phone,company,timezone,consent,consent_note"></textarea><p class="error" id="import-error" role="alert"></p><div id="import-result"></div><div class="dialog-actions"><button class="btn" type="button" data-action="csv-template">Get template</button><button class="btn primary" type="submit">Import contacts</button></div></form>`);
}
async function preflight(id){
 const p=await api(`/api/leads/${id}/preflight`);
 openDialog('Review before calling',`${p.lead.name} · ${p.lead.phone}`,`<div class="info-box">This is a real outbound telephone call. It may incur OpenAI and Twilio charges. The agent will disclose that it is AI and that notes are kept.</div>${p.reasons.length?`<ul class="check-list">${p.reasons.map(x=>`<li>${esc(x)}</li>`).join('')}</ul>`:`<p class="success-text small" style="margin-top:20px">All configured pilot gates passed. The server checks them again on confirmation.</p>`}<div class="call-meta"><div><span>Lead timezone</span>${esc(p.lead.timezone)}</div><div><span>Maximum connected duration</span>${p.maximum_seconds} seconds</div></div><p class="small muted">Only proceed with valid permission and applicable calling rules checked. No automatic follow-up call will be placed.</p><div class="dialog-actions"><button class="btn" data-action="close-dialog">Cancel</button><button class="btn primary" data-action="dial" data-id="${id}" data-request="${crypto.randomUUID()}" ${p.allowed?'':'disabled'}>${icon('calls')} Confirm real call</button></div><p id="dial-error" class="error" role="alert"></p>`);
}
async function detail(id){
 const call=await api(`/api/calls/${id}`);currentDetail=call;
 const grouped=[];for(const f of call.transcript){const last=grouped.at(-1);if(last?.role===f.role)last.text+=f.text;else grouped.push({...f});}
 openDialog(leadName(call),`${kindLabel(call.kind)} · ${date(call.created_at)}`,`<div class="row wrap">${badge(call.status)}${call.outcome?badge(call.outcome):''}</div><div class="call-meta"><div><span>Ended</span>${date(call.ended_at)}</div><div><span>Final API usage</span>${call.usage_finalized?esc(JSON.stringify(call.usage)):'Not finalized / not applicable'}</div></div>${call.summary?`<div class="call-summary">${esc(call.summary)}</div>`:''}${call.next_step?`<p class="small"><strong>Next step:</strong> ${esc(call.next_step)}</p>`:''}${call.requests.map(r=>`<div class="request"><strong>${esc(r.type.replaceAll('_',' ').toUpperCase())} · REQUEST ONLY</strong>${esc(r.details)}<p class="hint">Needs human confirmation. No calendar booking or live transfer was performed.</p></div>`).join('')}${call.error?`<div class="summary-error">${esc(call.error)}</div>`:''}<div class="form-section">TRANSCRIPT FRAGMENTS</div><div class="transcript" style="height:auto;max-height:310px;padding:0">${grouped.length?grouped.map(f=>`<div class="utterance ${f.role==='lead'?'lead':'agent'}"><span class="speaker">${f.role==='lead'?'Lead / you':'AI agent'}</span><p>${esc(f.text)}</p></div>`).join(''):'<p class="hint">No transcript was received.</p>'}</div><div class="dialog-actions wrap"><button class="btn" data-action="export-call">${icon('download')} Export JSON</button>${call.kind==='twilio'?`<button class="btn" data-action="reconcile" data-id="${call.id}">Check provider</button>`:''}${activeStatus(call.status)||call.status==='unknown'?`<button class="btn danger" data-action="stop-call" data-id="${call.id}">End call</button>`:''}<button class="btn" data-action="call-detail" data-id="${call.id}">Refresh</button></div>`);
}
function download(name,content,type='application/json') {const blob=new Blob([content],{type}),url=URL.createObjectURL(blob);const a=document.createElement('a');a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}
async function demo(){
 if(voice.running)throw new Error('End the current voice test before starting a preview.');
 const call=await post('/api/demo');labState={label:'A conversation, with a next step.',message:'This was a scripted text preview. No AI or telephone service was used.',fragments:call.transcript,kind:'demo'};
 await refresh(); if(tab!=='lab')location.hash='lab';else render();toast('Scripted preview saved. No real call was made.');
}
function setVoiceView(label,message){labState.label=label;labState.message=message;if($('#voice-label'))$('#voice-label').textContent=label;if($('#voice-message'))$('#voice-message').textContent=message;}
function pcmToBase64(buffer){const bytes=new Uint8Array(buffer);let s='';for(let i=0;i<bytes.length;i++)s+=String.fromCharCode(bytes[i]);return btoa(s);}
function playAudio(base64){
 if(!voice.ctx||!voice.running)return;
 const bytes=Uint8Array.from(atob(base64),c=>c.charCodeAt(0));if(bytes.length%2)throw new Error('Invalid PCM output.');
 const view=new DataView(bytes.buffer), samples=voice.ctx.createBuffer(1,bytes.length/2,24000), out=samples.getChannelData(0);
 for(let i=0;i<out.length;i++)out[i]=view.getInt16(i*2,true)/32768;
 const now=voice.ctx.currentTime;
 if(voice.nextTime-now>3)throw new Error('Audio playback fell behind. Please restart the test.');
 const source=voice.ctx.createBufferSource();source.buffer=samples;source.connect(voice.ctx.destination);
 voice.sources.add(source);source.onended=()=>voice.sources.delete(source);
 voice.nextTime=Math.max(voice.nextTime,now+.025);source.start(voice.nextTime);voice.nextTime+=samples.duration;
}
async function startVoice(){
 if(voice.running)return;
 const chosen=$('#voice-lead')?.value||null;
 const generation=++voice.generation;voice.running=true;voice.ready=false;voice.muted=false;voice.callId=null;voice.nextTime=0;
 labState={label:'Getting the microphone ready…',message:'This browser test sends audio to OpenAI and stores text notes in your workspace.',fragments:[],kind:'live'};render();
 try{
   if(!navigator.mediaDevices?.getUserMedia)throw new Error('Microphone access needs localhost or a secure HTTPS page.');
   const stream=await navigator.mediaDevices.getUserMedia({audio:{channelCount:1,echoCancellation:true,noiseSuppression:true,autoGainControl:true},video:false});
   if(generation!==voice.generation||!voice.running){stream.getTracks().forEach(t=>t.stop());return;}
   voice.stream=stream;voice.ctx=new AudioContext({sampleRate:24000,latencyHint:'interactive'});await voice.ctx.resume();
   if(voice.ctx.sampleRate!==24000)throw new Error('This browser could not initialize 24 kHz audio. Try a current desktop Chrome browser.');
   await voice.ctx.audioWorklet.addModule('/assets/capture-worklet.js');
   if(generation!==voice.generation||!voice.running)return;
   const source=voice.ctx.createMediaStreamSource(stream);voice.node=new AudioWorkletNode(voice.ctx,'relay-capture');
   source.connect(voice.node);voice.node.connect(voice.ctx.destination); // Worklet emits silence to the speaker, not microphone feedback.
   const ticket=await post('/api/voice/ticket',{lead_id:chosen});
   if(generation!==voice.generation||!voice.running){await post(`/api/calls/${ticket.call_id}/stop`);return;}
   voice.callId=ticket.call_id;
   const url=new URL(ticket.path,location.href);url.protocol=location.protocol==='https:'?'wss:':'ws:';url.searchParams.set('ticket',ticket.ticket);
   voice.ws=new WebSocket(url);const ws=voice.ws;
   setVoiceView('Connecting to your voice agent…','Waiting for GPT-Live to confirm the session. Your microphone is not streamed before it is ready.');
   voice.node.port.onmessage=e=>{if(voice.running&&voice.ready&&!voice.muted&&ws.readyState===WebSocket.OPEN){if(ws.bufferedAmount>262144){void stopVoice('Network input fell behind. Restart the test.');return;}ws.send(JSON.stringify({type:'audio',audio:pcmToBase64(e.data)}));}};
   ws.onmessage=e=>{
    if(ws!==voice.ws)return;
    try{
     const event=JSON.parse(e.data);
     if(event.type==='ready'){voice.ready=true;setVoiceView('You’re live with your agent.','Speak naturally. You can interrupt, mute your microphone, or end the test at any time.');$('#voice-stage')?.classList.add('live');if($('#voice-chip')){$('#voice-chip').textContent='LIVE BROWSER SESSION';$('#voice-chip').classList.add('green');}}
     else if(event.type==='audio')playAudio(event.audio);
     else if(event.type==='transcript'){labState.fragments.push({role:event.role,text:event.text});renderTranscript();}
     else if(event.type==='tool')toast(event.message+' Practice data only.');
     else if(event.type==='error'){setVoiceView('The voice session hit a problem.',event.message);toast(event.message);}
     else if(event.type==='ended'){const finalMessage=event.usage_finalized?'The session ended. Your transcript is available in call history.':'The session ended without confirmed final usage. Check call history and provider usage.';void cleanupVoice(finalMessage);}
    }catch(error){void stopVoice(error.message);}
   };
   ws.onerror=()=>{toast('Voice connection failed. Check the server, origin, and API access.');};
   ws.onclose=()=>{if(ws===voice.ws)void cleanupVoice('The voice connection closed. Review call history for its final state.');};
 }catch(error){if(generation===voice.generation)await stopVoice(error.message);toast(error.message);}
}
async function cleanupVoice(message){
 voice.generation++;voice.running=false;voice.ready=false;
 voice.stream?.getTracks().forEach(t=>t.stop());voice.stream=null;
 for(const source of voice.sources){try{source.stop();}catch{}}voice.sources.clear();
 if(voice.node){voice.node.port.onmessage=null;voice.node.disconnect();voice.node=null;}
 const ctx=voice.ctx;voice.ctx=null;if(ctx)await ctx.close().catch(()=>{});
 const ws=voice.ws;voice.ws=null;if(ws&&ws.readyState<2)ws.close();
 setVoiceView('Your voice test has ended.',message);labState.kind='ended';
 if(tab==='lab')render();
 await refresh().catch(()=>{});
}
async function stopVoice(reason='The test has ended. Review its notes in call history.'){
 const id=voice.callId,ws=voice.ws;
 if(ws?.readyState===WebSocket.OPEN)ws.send(JSON.stringify({type:'stop'}));
 await cleanupVoice(reason);
 if(id){try{await post(`/api/calls/${id}/stop`);}catch(e){toast('Could not confirm server stop. The server duration cap still applies.');}}
}
function muteVoice(){voice.muted=!voice.muted;voice.stream?.getAudioTracks().forEach(t=>t.enabled=!voice.muted);if(voice.ws?.readyState===WebSocket.OPEN)voice.ws.send(JSON.stringify({type:voice.muted?'mute':'unmute'}));if($('#mute-voice'))$('#mute-voice').textContent=voice.muted?'Unmute':'Mute';}
async function lock(){await stopVoice();token='';sessionStorage.removeItem('relay-token');data=null;$('#workspace').classList.add('hidden');$('#login').classList.remove('hidden');$('#token').value='';}
async function enter(){await refresh();$('#login').classList.add('hidden');$('#workspace').classList.remove('hidden');tab=titles[location.hash.slice(1)]?location.hash.slice(1):'overview';render();}

$('#login-form').addEventListener('submit',async e=>{e.preventDefault();const btn=$('button',e.target);btn.disabled=true;$('#login-error').textContent='';token=$('#token').value.trim();try{await enter();sessionStorage.setItem('relay-token',token);$('#token').value='';}catch(error){$('#login-error').textContent=error.message;token='';}finally{btn.disabled=false;}});
$('#logout').addEventListener('click',()=>void lock());
window.addEventListener('hashchange',async()=>{const next=titles[location.hash.slice(1)]?location.hash.slice(1):'overview';if(tab==='lab'&&next!=='lab'&&voice.running)await stopVoice('Voice test ended when you left the lab.');tab=next;query='';render();});
window.addEventListener('beforeunload',()=>{if(voice.ws?.readyState===WebSocket.OPEN)voice.ws.send(JSON.stringify({type:'stop'}));voice.stream?.getTracks().forEach(t=>t.stop());});
document.addEventListener('input',e=>{if(e.target.id==='lead-search'){const position=e.target.selectionStart;query=e.target.value;render();$('#lead-search').focus();$('#lead-search').setSelectionRange(position,position);}});
document.addEventListener('change',async e=>{if(e.target.id==='csv-file'){const file=e.target.files[0];if(file){if(file.size>220000){toast('CSV must be smaller than 220 KB.');return;}$('#csv-text').value=await file.text();}}});
document.addEventListener('submit',async e=>{
 const form=e.target;if(!['playbook-form','lead-form','import-form'].includes(form.id))return;
 e.preventDefault();const submit=$('button[type="submit"]',form);submit.disabled=true;
 const err=$('#'+(form.id==='playbook-form'?'playbook':form.id==='lead-form'?'lead':'import')+'-error');err.textContent='';
 try{
   if(form.id==='playbook-form'){const values=new FormData(form),body=Object.fromEntries(values);body.approved=values.has('approved');body.weekdays=values.getAll('weekdays').map(Number);body.start_hour=Number(body.start_hour);body.end_hour=Number(body.end_hour);await api('/api/playbook',{method:'PUT',body:JSON.stringify(body)});await refresh(true);toast('Playbook saved. Active calls keep their original playbook snapshot.');}
   if(form.id==='lead-form'){const values=new FormData(form),body=Object.fromEntries(values);body.consent=values.has('consent');if(form.dataset.id)await api('/api/leads/'+form.dataset.id,{method:'PUT',body:JSON.stringify(body)});else{const result=await post('/api/leads',body);if(!result.created)toast('This number already exists. The existing contact was not overwritten.');}$('#dialog').close();await refresh(true);toast('Contact saved. No call was placed.');}
   if(form.id==='import-form'){const result=await post('/api/leads/import',{csv:$('#csv-text').value});$('#import-result').innerHTML=`<div class="info-box section-space">${result.added} added · ${result.duplicates} duplicates preserved · ${result.errors.length} row errors</div>${result.errors.length?`<div class="summary-error">${result.errors.slice(0,30).map(x=>`Row ${x.row}: ${esc(x.error)}`).join('<br>')}</div>`:''}`;await refresh(true);toast('Import complete. No calls were placed.');}
 }catch(error){err.textContent=error.message;}finally{submit.disabled=false;}
});
document.addEventListener('click',async e=>{
 const navigation=e.target.closest('[data-nav]');if(navigation){location.hash=navigation.dataset.nav;return;}
 const button=e.target.closest('[data-action]');if(!button||button.disabled)return;
 const action=button.dataset.action,id=button.dataset.id;button.disabled=true;
 try{
  if(action==='lock-workspace')await lock();
  else if(action==='close-dialog')$('#dialog').close();
  else if(action==='add-lead')leadDialog();
  else if(action==='edit-lead')leadDialog(id);
  else if(action==='import')importDialog();
  else if(action==='samples'){const result=await post('/api/sample-leads');await refresh(true);toast(`${result.added} fictional samples added. They cannot receive real calls.`);}
  else if(action==='demo')await demo();
  else if(action==='preflight')await preflight(id);
  else if(action==='dial'){try{const result=await post('/api/calls/dial',{lead_id:id,confirm:true,request_id:button.dataset.request});await refresh();await detail(result.call.id);toast(result.reused?'Existing attempt restored. No new call was created.':'Call attempt recorded. Review its actual provider status.');}catch(error){$('#dial-error').textContent=error.message;}}
  else if(action==='call-detail')await detail(id);
  else if(action==='stop-call'){await post(`/api/calls/${id}/stop`);await refresh();await detail(id);}
  else if(action==='reconcile'){await post(`/api/calls/${id}/reconcile`);await refresh();await detail(id);}
  else if(action==='export-call'&&currentDetail)download(`${currentDetail.id}.json`,JSON.stringify(currentDetail,null,2));
  else if(action==='csv-template')download('relay-leads-template.csv','name,phone,company,timezone,language,notes,consent,consent_note\nTest contact,+12025550101,Example,Africa/Cairo,English,Replace with your own number,false,\n','text/csv');
  else if(action==='suppress'){openDialog('Permanently stop calls to this number?','This adds a do-not-call entry that imports and AI tools cannot remove.',`<div class="dialog-actions"><button class="btn" data-action="close-dialog">Cancel</button><button class="btn danger" data-action="confirm-suppress" data-id="${id}">Confirm do not call</button></div>`);}
  else if(action==='confirm-suppress'){await post(`/api/leads/${id}/suppress`);$('#dialog').close();await refresh(true);toast('Number suppressed. No future calls are permitted by this workspace.');}
  else if(action==='deliver'){openDialog('Share this outcome with your endpoint?','This sends call notes and meeting/callback requests to the server-configured URL. Transcripts are excluded.',`<div class="info-box amber">The receiver must deduplicate by event ID. After an uncertain response, it may already have processed the event; check before retrying.</div><div class="dialog-actions"><button class="btn" data-action="close-dialog">Cancel</button><button class="btn primary" data-action="confirm-deliver" data-id="${id}">Approve external delivery</button></div>`);}
  else if(action==='confirm-deliver'){const result=await post(`/api/outbox/${id}/deliver`,{confirm:true});$('#dialog').close();await refresh(true);toast(result.status==='sent'?'Endpoint confirmed successful receipt.':'Delivery is uncertain. Review the outbox before retrying.');}
  else if(action==='start-voice')await startVoice();
  else if(action==='stop-voice')await stopVoice();
  else if(action==='mute-voice')muteVoice();
 }catch(error){toast(error.message);}finally{button.disabled=false;}
});
setInterval(async()=>{if(!token||!data||document.hidden)return;try{await refresh(['overview','calls'].includes(tab)&&!$('#dialog').open);}catch(e){if(e.status===401)toast('Workspace authentication expired. Lock the workspace and sign in again.');}},7000);
if(token)enter().catch(()=>{token='';sessionStorage.removeItem('relay-token');});
