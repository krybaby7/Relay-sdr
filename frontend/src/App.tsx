import { useCallback, useEffect, useRef, useState } from 'react';
import { Renderer, JSONUIProvider } from '@json-render/react';
import { Responsive, useContainerWidth, noCompactor } from 'react-grid-layout';
import type { Layout, ResponsiveGridLayoutProps } from 'react-grid-layout';
import type { Bootstrap, Dataset, Query, Detail, Reference, Widget, Kind, Operation, Layouts, Breakpoint, Task, Job, Revision, Mode } from './types';
import { api, readApi, ApiError, date, events, identifier, label } from './api';
import { Badge, Empty, Icon, Modal, WidgetBoundary } from './ui';
import { registry, WorkspaceData } from './catalog';
import { AddWidget, FieldEditor, ImportEditor, LeadEditor, QueryControls, RubricEditor, ViewEditor, WidgetEditor, widgetLabels } from './editors';
import { CallViewer, LeadDetail, NoteViewer } from './details';
import { changeGeometry } from './geometry';
import 'react-grid-layout/css/styles.css';
import 'react-resizable/css/styles.css';
import './style.css';

type Dialog = 'view' | 'duplicate' | 'widget' | 'add_widget' | 'lead' | 'edit_lead' | 'import' | 'field' | 'rubric' | 'settings' | 'history' | 'proposals' | 'filters' | 'jobs' | null;
const COLS = { lg: 12, md: 8, sm: 4 };
const stripLayout = (layout: Layout) => layout.map(({ i, x, y, w, h }) => ({ i, x, y, w, h }));
const definitions: Record<string, string> = {
  today: 'Due and overdue commitments, plus decisions or internal work needing review.',
  all: 'Every real lead, including uncalled, unassessed, suppressed and failed-analysis records.',
  potential: 'Leads assessed as promising or strong using the approved evidence rubric.',
  followups: 'Leads with open, waiting, proposed or review-needed internal work.',
  qualification: 'Leads whose commercial potential is still unassessed—not low quality.',
  review: 'Failed, unavailable, stale, incomplete or conflicting assessments requiring attention.',
  dnc: 'Permanently suppressed contacts. No contact eligibility can be changed by the orchestrator.',
  practice: 'Fictional samples and browser/demo call history, isolated from real pipeline intelligence.',
};

function MeasuredGrid(props: Omit<ResponsiveGridLayoutProps<Breakpoint>, 'width'>) {
  // This component mounts with its element present; the login/loading shell does not.
  const { width, containerRef, mounted } = useContainerWidth({ measureBeforeMount: true });
  return <div ref={containerRef}>{mounted && <Responsive<Breakpoint> {...props} width={width}/>}</div>;
}

export default function App() {
  const [authenticated, setAuthenticated] = useState(!!sessionStorage.getItem('relay-token'));
  const [token, setToken] = useState(''); const [boot, setBoot] = useState<Bootstrap | null>(null);
  const [viewId, setViewId] = useState(''); const [query, setQuery] = useState<Query | null>(null); const [page, setPage] = useState(1);
  const [data, setData] = useState<Dataset | null>(null); const [loading, setLoading] = useState(false); const [error, setError] = useState(''); const [notice, setNotice] = useState('');
  const [detail, setDetail] = useState<Detail | null>(null); const [detailOpen, setDetailOpen] = useState(false); const [call, setCall] = useState<{ id: string; reference?: Reference } | null>(null);
  const [noteSource, setNoteSource] = useState<{ id: string; leadId: string } | null>(null);
  const [selected, setSelected] = useState<Set<string>>(new Set()); const [dialog, setDialog] = useState<Dialog>(null); const [widgetId, setWidgetId] = useState('');
  const [command, setCommand] = useState(''); const [activeJob, setActiveJob] = useState<Job | null>(null); const [jobs, setJobs] = useState<Job[]>([]); const [revisions, setRevisions] = useState<Revision[]>([]); const [historyMore, setHistoryMore] = useState(false);
  const [pending, setPending] = useState(false); const [refreshCounter, setRefreshCounter] = useState(0); const [dragging, setDragging] = useState(false); const [layoutDraft, setLayoutDraft] = useState<Layouts | null>(null);
  const [breakpoint, setBreakpoint] = useState<Breakpoint>('lg'); const [editCanvas, setEditCanvas] = useState(false);
  const bootstrapLoading = useRef(false); const sessionEpoch = useRef(0);
  const detailRequest = useRef(0); const busy = useRef(false); const lastInteraction = useRef(0); const bootRef = useRef(boot); const queryRef = useRef(query); const viewRef = useRef(viewId); const detailRef = useRef(detail);
  bootRef.current = boot; queryRef.current = query; viewRef.current = viewId; detailRef.current = detail;
  busy.current = detailOpen || !!call || !!noteSource || !!dialog || !!layoutDraft || dragging || editCanvas || selected.size > 0;
  const view = boot?.spec.views.find(v => v.id === viewId) || boot?.spec.views[0];

  const loadBootstrap = useCallback(async (initial = false) => {
    if (bootstrapLoading.current) return;
    bootstrapLoading.current = true; const epoch = sessionEpoch.current; setError('');
    try {
      const fresh = await readApi<Bootstrap>('/api/workspace');
      if (epoch !== sessionEpoch.current) return;
      const id = !initial && fresh.spec.views.some(v => v.id === viewRef.current) ? viewRef.current : fresh.spec.default_view;
      const oldView = bootRef.current?.spec.views.find(v => v.id === id);
      const localQuery = queryRef.current;
      const preserveQuery = !initial && id === viewRef.current && oldView && localQuery && JSON.stringify(localQuery) !== JSON.stringify(oldView.query);
      setBoot(fresh); setViewId(id); setQuery(preserveQuery ? localQuery : fresh.spec.views.find(v => v.id === id)!.query); setPending(false); setRefreshCounter(n => n + 1);
      return fresh;
    } catch (e) {
      if (epoch !== sessionEpoch.current) return;
      if (e instanceof ApiError && [401,403].includes(e.status)) { sessionStorage.removeItem('relay-token'); setAuthenticated(false); setBoot(null); setData(null); setDetail(null); }
      setError((e as Error).message); throw e;
    } finally { if (epoch === sessionEpoch.current) bootstrapLoading.current = false; }
  }, []);
  useEffect(() => { if (authenticated) void loadBootstrap(true).catch(() => undefined); }, [authenticated, loadBootstrap]);
  useEffect(() => {
    const interaction = () => { lastInteraction.current = Date.now(); };
    window.addEventListener('pointerdown', interaction); window.addEventListener('keydown', interaction); window.addEventListener('wheel', interaction, { passive: true });
    return () => { window.removeEventListener('pointerdown', interaction); window.removeEventListener('keydown', interaction); window.removeEventListener('wheel', interaction); };
  }, []);
  useEffect(() => {
    if (!authenticated || !bootRef.current) return;
    const controller = new AbortController();
    void events(bootRef.current.cursor, controller.signal, () => setPending(true));
    return () => controller.abort();
  }, [authenticated, !!boot]);
  useEffect(() => {
    if (!pending) return;
    const timer = setInterval(() => {
      const focused = document.activeElement?.matches('input,textarea,select,[contenteditable=true]');
      if (!busy.current && !focused && Date.now() - lastInteraction.current > 3000) void loadBootstrap().catch(() => undefined);
    }, 1000);
    return () => clearInterval(timer);
  }, [pending, loadBootstrap]);
  useEffect(() => {
    if (!query || !viewId || !authenticated) return;
    const controller = new AbortController(); const timer = setTimeout(() => {
      setLoading(true); const body = { view_id: viewId, query, page, page_size: 25 };
      void readApi<Dataset>('/api/workspace/dataset', 'POST', body, controller.signal)
        .then(result => { if (controller.signal.aborted) return; setData(result); setLoading(false); })
        .catch(e => { if (!controller.signal.aborted) { setError((e as Error).message); setLoading(false); } });
    }, query.search ? 250 : 0);
    return () => { clearTimeout(timer); controller.abort(); };
  }, [query, viewId, page, refreshCounter, authenticated]);
  useEffect(() => {
    if (!activeJob || ['succeeded','failed','superseded','waiting_configuration'].includes(activeJob.status)) return;
    const timer = setInterval(() => { void api<{ items: Job[] }>('/api/workspace/jobs?limit=100').then(result => {
      const job = result.items.find(j => j.id === activeJob.id); if (job) { setActiveJob(job); if (['succeeded','failed','superseded','waiting_configuration'].includes(job.status)) setPending(true); }
    }).catch(e => setError((e as Error).message)); }, 2000);
    return () => clearInterval(timer);
  }, [activeJob]);

  async function save(operations: Operation[], reason: string, newViewId?: string) {
    if (!bootRef.current) return;
    const ops: Operation[] = layoutDraft && !operations.some(op => op.op === 'set_layout') ? [{ op: 'set_layout', view_id: viewId, layouts: layoutDraft }, ...operations] : operations;
    const oldView = bootRef.current.spec.views.find(v => v.id === viewId);
    const preserveQuery = oldView && queryRef.current && JSON.stringify(queryRef.current) !== JSON.stringify(oldView.query) && !ops.some(op => op.op === 'edit_view' && op.view_id === viewId && 'query' in op);
    const result = await api<{ version: number; spec: Bootstrap['spec'] }>('/api/workspace/changes', 'POST', { base_version: bootRef.current.version, reason, operations: ops });
    setLayoutDraft(null); setBoot({ ...bootRef.current, ...result }); setPending(false); setNotice(reason);
    if (newViewId) { setViewId(newViewId); setQuery(result.spec.views.find(v => v.id === newViewId)!.query); setPage(1); }
    else { const freshView = result.spec.views.find(v => v.id === viewId); if (freshView && !preserveQuery) setQuery(freshView.query); }
    setRefreshCounter(n => n + 1);
  }
  function action(promise: Promise<unknown>) { void promise.catch(e => setError((e as Error).message)); }
  function changeView(id: string) {
    if (layoutDraft) { setError('Save or discard the current layout changes before switching views.'); return; }
    const chosen = boot!.spec.views.find(v => v.id === id)!; setViewId(id); setQuery(chosen.query); setPage(1); setData(null); setSelected(new Set()); setNotice('');
    // Selected evidence belongs to the old view, especially across real/practice.
    detailRequest.current++; setDetail(null); setDetailOpen(false); setCall(null); setNoteSource(null);
  }
  async function openLead(id: string) { const request = ++detailRequest.current; setError(''); try { const result = await api<Detail>(`/api/workspace/leads/${id}`); if (request !== detailRequest.current) return; setDetail(result); setDetailOpen(true); } catch (e) { setError((e as Error).message); } }
  async function refreshDetail() { const id = detailRef.current?.lead.id; if (id) { const result = await api<Detail>(`/api/workspace/leads/${id}`); if (id === detailRef.current?.lead.id) setDetail(result); } setRefreshCounter(n => n + 1); }
  async function taskChange(task: Task, status: string, due?: string) { await api(`/api/workspace/tasks/${task.id}`, 'POST', { version: task.version, status, due_at: due || null }); await refreshDetail(); setNotice('Internal task updated. No call, message, booking or transfer was executed.'); }
  function showEvidence(ref: Reference) {
    if (ref.note_id && detailRef.current) setNoteSource({id: ref.note_id, leadId: detailRef.current.lead.id});
    else if (ref.call_id) setCall({ id: ref.call_id, reference: ref });
  }
  async function sendCommand() {
    if (!boot || !view) return; setError('');
    try { const result = await api<{ id: string; status: string }>('/api/workspace/commands', 'POST', { text: command, view_id: view.id, base_version: boot.version });
      setActiveJob({ ...result, kind: 'command', attempts: 0, error: null, lead_id: null, model: boot.orchestrator.model, created_at: new Date().toISOString(), result: null }); setCommand('');
    } catch (e) { setError((e as Error).message); }
  }
  function captureLayout(layout: Layout) { if (!view) return; setLayoutDraft({ ...(layoutDraft || view.layouts), [breakpoint]: stripLayout(layout) }); setDragging(false); }
  function keyboardGeometry(id: string, change: 'up' | 'down' | 'wider' | 'narrower' | 'taller' | 'shorter') {
    if (!view || view.locked) return;
    try {
      const next = structuredClone(layoutDraft || view.layouts);
      next[breakpoint] = changeGeometry(next[breakpoint], id, change, new Set(Object.values(boot!.spec.widgets).filter(w => w.pinned).map(w => w.id)), COLS[breakpoint]);
      setLayoutDraft(next); setError('');
    } catch (e) { setError((e as Error).message); }
  }

  async function addWidget(kind: Kind) {
    const id = identifier('widget'); const widget: Widget = { id, kind, title: widgetLabels[kind], binding: kind === 'EvidencePanel' || kind === 'Questions' ? 'selected_lead' : kind === 'RecentChanges' ? 'activity' : 'view', pinned: false, limit: 20,
      columns: ['name','company','potential','priority','confidence','eligibility'].map(field => ({ field, width: 160, visible: true })) };
    await save([{ op: 'add_widget', view_id: view!.id, widget }], `Added ${widgetLabels[kind]}`);
  }
  async function showHistory(before?: number) { const result = await readApi<{ items: Revision[]; has_more: boolean }>(`/api/workspace/revisions${before ? `?before=${before}` : ''}`); setRevisions(previous => before ? [...previous, ...result.items] : result.items); setHistoryMore(result.has_more); setDialog('history'); }
  async function restore(target?: number) { await api('/api/workspace/restore', 'POST', { base_version: boot!.version, target_version: target ?? null }); setLayoutDraft(null); await loadBootstrap(); setDialog(null); setNotice(target ? `Restored presentation version ${target}. Lead records were not changed.` : 'Reset presentation only. Lead records and evidence are retained.'); }
  async function showJobs() { setJobs((await api<{ items: Job[] }>('/api/workspace/jobs')).items); setDialog('jobs'); }

  function lockWorkspace() {
    sessionEpoch.current++; detailRequest.current++; bootstrapLoading.current = false;
    sessionStorage.removeItem('relay-token'); setAuthenticated(false); setBoot(null); setData(null); setDetail(null); setDetailOpen(false); setCall(null); setNoteSource(null); setDialog(null); setActiveJob(null); setSelected(new Set()); setQuery(null); setLayoutDraft(null); setToken(''); setError(''); setEditCanvas(false); setPending(false);
  }

  if (!authenticated) return <main className="login-page"><div className="login-card"><div className="brand"><span className="brand-symbol">r</span>relay <small>SDR</small></div><h1>Your private sales workspace</h1><p>Use the same local admin token as the rest of Relay. It stays in this browser tab’s session storage.</p><form onSubmit={e => { e.preventDefault(); sessionStorage.setItem('relay-token', token.trim()); setError(''); setAuthenticated(true); }}><label>Workspace token<input type="password" autoComplete="off" required minLength={24} value={token} onChange={e => setToken(e.target.value)}/></label>{error && <p className="error" role="alert">{error}</p>}<button className="primary">Open workspace <Icon name="arrow"/></button></form><small>Server credentials and provider keys never belong in this field.</small></div></main>;
  if (!boot || !view || !query) return <main className="loading-page">{!error && <span className="spinner"/>}<h2>{error ? 'Your workspace could not be loaded' : 'Opening your saved workspace…'}</h2>{error && <><p className="error" role="alert">{error}</p><p>Your saved records and layout have not changed.</p><button onClick={() => action(loadBootstrap(true))}>Retry opening workspace</button></>}<button onClick={lockWorkspace}>Back to sign in</button></main>;
  const modelReady = boot.orchestrator.enabled_by_server && boot.orchestrator.configured && !boot.orchestrator.paused;
  const layouts = Object.fromEntries(Object.entries(layoutDraft || view.layouts).map(([bp, items]) => [bp, items.map(item => ({ ...item, minW: 4, minH: 4, maxH: 30, static: !editCanvas || view.locked || boot.spec.widgets[item.i].pinned }))]));
  const context = data ? { viewId: view.id, bootstrap: boot, data, dataVersion: refreshCounter, detail, query, selected, toggleSelection: (id: string) => setSelected(previous => { const next = new Set(previous); if (next.has(id)) next.delete(id); else next.add(id); return next; }),
    openLead: (id: string) => { void openLead(id); }, openCall: (id: string, reference?: Reference) => setCall({ id, reference }), evidence: showEvidence, task: (task: Task, status: string) => action(taskChange(task, status)),
    sort: (sort: Query['sort']) => { setQuery({ ...query, sort, direction: query.sort === sort && query.direction === 'desc' ? 'asc' : 'desc' }); setPage(1); }, page: setPage } : null;
  return <div className="shell">
    <aside className="sidebar"><a className="brand" href="/#overview"><span className="brand-symbol">r</span><span>relay <small>SDR</small></span></a><span className="nav-caption">WORKSPACE</span><nav aria-label="Main navigation">{[['grid','Overview','/#overview'],['people','Leads','/leads'],['phone','Voice lab','/#lab'],['book','Playbook','/#playbook'],['clock','Calls','/#calls'],['link','Connections','/#connections']].map(([icon,name,href]) => <a key={name} href={href} className={name === 'Leads' ? 'nav-item active' : 'nav-item'} title={name}><Icon name={icon}/><span>{name}</span>{name === 'Leads' && <span className="nav-dot"/>}</a>)}</nav><div className="sidebar-bottom"><div className="workspace-avatar">R</div><div><strong>Private workspace</strong><small>Local · single operator</small></div><button className="icon-button" aria-label="Lock workspace" onClick={lockWorkspace}><Icon name="lock" size={16}/></button></div></aside>
    <main className="workspace-main"><header className="topbar"><span>Workspace <span className="separator">/</span> <strong>Leads</strong></span><div><span className={`connection-dot ${modelReady ? 'online' : ''}`}/><button className="text-button" onClick={() => setDialog('settings')}>{modelReady ? 'Workspace agent connected' : 'Workspace agent needs setup'}</button><span className="version-tag">v{boot.version}</span></div></header>
      {boot.fixture_mode && <p className="notice warning fixture-banner">VERIFICATION DATASET — All people, call content and assessments shown here are fictional fixtures. No calls were placed.</p>}
      <div className="page-heading"><div><span className="eyebrow">YOUR PIPELINE, IN CONTEXT</span><h1>Leads workspace<span className="heading-dot">.</span></h1><p>Evidence you can trace. Priorities you can act on.</p></div><div className="header-actions"><button onClick={() => setDialog('import')}>Import CSV</button><button className="primary" onClick={() => setDialog('lead')}><Icon name="plus" size={16}/>Add lead</button></div></div>
      <section className="command-area" aria-label="Workspace orchestrator"><div className="command-label"><span className="agent-mark"><Icon name="spark"/></span><div><strong>Organize with your workspace agent</strong><small>Changes are saved, versioned and reversible. No outreach permissions.</small></div><label className="mode-selector"><span className="sr-only">Organization mode</span><select aria-label="Organization mode" value={boot.spec.mode} onChange={e => action(save([{ op: 'preferences', mode: e.target.value as Mode, default_view: boot.spec.default_view, allow_structural_auto: boot.spec.allow_structural_auto }], `Organization mode changed to ${e.target.value}`))}><option value="adaptive">Adaptive</option><option value="suggest">Suggest</option><option value="manual">Manual</option></select></label></div>
        <form className="command-form" onSubmit={e => { e.preventDefault(); void sendCommand(); }}><input aria-label="Workspace instruction" placeholder="Show leads awaiting a proposal, grouped by priority…" maxLength={2000} value={command} onChange={e => setCommand(e.target.value)}/><button className="primary" aria-label="Organize" disabled={!modelReady || !command.trim()} title={!modelReady ? 'Configure server-side workspace reasoning first' : 'Submit internal organization command'}><Icon name="arrow" size={18}/><span>Organize</span></button></form>
        <div className="command-chips">{['Move callbacks due today to the top and pin the call history.','Create a view of promising leads blocked by procurement.','I have twenty minutes. Show where a decision from me would unblock progress.'].map((example, index) => <button key={example} onClick={() => setCommand(example)}>{['Callbacks due today','Procurement blockers','Where I can unblock progress'][index]} <span>↗</span></button>)}</div>
        {!modelReady && <p className="setup-note">Manual workspace editing is available now. {boot.orchestrator.paused ? 'Workspace reasoning is paused.' : 'Enable server-side workspace reasoning and configure a model key to use the agent.'} <button className="text-button" onClick={() => setDialog('settings')}>Setup & limits</button></p>}
        {activeJob && <div className={`job-status ${activeJob.status}`} role="status"><Icon name="spark" size={14}/><span>{label(activeJob.status)} · {activeJob.error || activeJob.result?.workspace?.reason || (activeJob.status === 'succeeded' ? `Workspace ${activeJob.result?.workspace?.status || 'updated'}. Saved changes will appear when it is safe to apply them.` : 'Internal organization is queued on the server. This does not contact leads.')}</span><button className="text-button" onClick={() => action(showJobs())}>Run details</button></div>}
      </section>
      {error && <div className="alert error" role="alert"><span>{error} The last valid saved workspace is retained.</span><button onClick={() => { setError(''); setRefreshCounter(n => n + 1); }}>Retry loading data</button><button aria-label="Dismiss error" onClick={() => setError('')}><Icon name="close" size={15}/></button></div>}
      {notice && <div className="alert success" role="status"><Icon name="check" size={15}/><span>{notice}</span><button aria-label="Dismiss notification" onClick={() => setNotice('')}><Icon name="close" size={15}/></button></div>}
      {pending && <div className="alert pending" role="status"><Icon name="spark" size={16}/><span>Saved updates are ready. {busy.current ? 'Your active selection, editing session or detail view is protected.' : 'Updates apply after a brief idle period.'}</span><button disabled={busy.current} onClick={() => action(loadBootstrap())}>Apply updates</button></div>}
      {!!boot.proposals.length && <div className="alert pending"><span>{boot.proposals.length} organization proposal{boot.proposals.length === 1 ? '' : 's'} awaiting review.</span><button onClick={() => setDialog('proposals')}>Review changes</button></div>}
      <nav className="view-tabs" aria-label="Saved views">{boot.spec.views.map(saved => <button key={saved.id} aria-label={saved.name} aria-pressed={saved.id === view.id} aria-description={saved.id === view.id && data ? `${data.records.total} matching records` : undefined} className={saved.id === view.id ? 'active' : ''} onClick={() => changeView(saved.id)}>{saved.locked && <Icon name="lock" size={12}/>}<span>{saved.name}</span>{saved.id === view.id && data && <small>{data.records.total}</small>}</button>)}<button className="new-view" aria-label="Create saved view" onClick={() => setDialog('duplicate')}><Icon name="plus" size={16}/></button></nav>
      <div className="view-description"><p>{definitions[view.id] || 'A custom saved query. Filters and ordering are visible in Customize view.'}</p><button className="text-button" onClick={() => setDialog('view')}>View definition <Icon name="sliders" size={13}/></button></div>
      {query.scope === 'practice' && <div className="notice practice-note"><strong>Practice is isolated.</strong> Fictional samples and browser/demo calls never count as real sales activity. <button onClick={() => action(api('/api/sample-leads', 'POST').then(() => { setRefreshCounter(n => n + 1); }))}>Add labeled sample contacts</button><a href="/#lab">Open voice lab ↗</a></div>}
      {!boot.rubric.approved && <div className="rubric-banner"><span><Icon name="book" size={15}/>Your sales rubric is awaiting approval. Unknown leads remain unassessed.</span><button className="text-button" onClick={() => setDialog('rubric')}>Review rubric</button></div>}
      <section className="metric-strip" aria-label="Evidence-backed overview">{[['Leads in this view', data?.metrics.total, 'All matching records, not just the page'],['Promising opportunities', data?.metrics.promising, 'Supported need and product fit'],['Commitments due', data?.metrics.due, 'Due today or overdue; no outreach performed'],['Needs review', data?.metrics.review, 'Coverage, freshness or conflicting evidence']].map(([title,value,subtitle]) => <div className="metric" key={String(title)}><span>{title}</span><strong>{value === undefined ? '—' : value}</strong><small>{subtitle}</small></div>)}</section>
      <div className="workspace-toolbar"><label className="search-box"><Icon name="search" size={17}/><input aria-label="Search leads" placeholder="Search names, companies or phone numbers" value={query.search} onChange={e => { setQuery({ ...query, search: e.target.value }); setPage(1); }}/>{query.search && <button aria-label="Clear search" onClick={() => setQuery({ ...query, search: '' })}><Icon name="close" size={13}/></button>}</label><div className="toolbar-actions"><button onClick={() => setDialog('filters')}><Icon name="sliders" size={15}/>Filters {query.filters.length > 0 && <small>{query.filters.length}</small>}</button><button aria-pressed={editCanvas} onClick={() => setEditCanvas(!editCanvas)}><Icon name="grid" size={15}/>{editCanvas ? 'Finish customizing' : 'Customize canvas'}</button><details className="more-menu"><summary aria-label="More workspace options">•••</summary><div><button onClick={() => setDialog('duplicate')}>Create / duplicate view</button><button onClick={() => setDialog('view')}>Rename / configure view</button><button onClick={() => action(save([{ op: 'lock_view', view_id: view.id, locked: !view.locked }], `${view.locked ? 'Unlocked' : 'Locked'} ${view.name}`))}>{view.locked ? 'Unlock view' : 'Lock view'}</button><button onClick={() => setDialog('field')}>Custom field</button><button onClick={() => setDialog('rubric')}>Sales rubric</button><button onClick={() => action(showHistory())}>History / undo / reset</button><button onClick={() => action(showJobs())}>Analysis runs</button><button onClick={() => setDialog('settings')}>Agent settings</button></div></details></div></div>
      {selected.size > 0 && <div className="selection-bar"><span>{selected.size} lead{selected.size === 1 ? '' : 's'} selected. Automatic reordering is held.</span><button onClick={() => setSelected(new Set())}>Clear selection</button></div>}
      {editCanvas && <div className="canvas-help"><span><Icon name="grid" size={16}/>Drag panel headers or resize corners. Keyboard move and size controls are also available.</span><button onClick={() => setDialog('add_widget')} disabled={view.locked}><Icon name="plus" size={15}/>Add widget</button></div>}
      {layoutDraft && <div className="layout-savebar"><strong>Layout changes are not saved yet</strong><span>Breakpoint: {breakpoint} · pins and IDs preserved</span><button onClick={() => setLayoutDraft(null)}>Discard</button><button className="primary" onClick={() => action(save([{ op: 'set_layout', view_id: view.id, layouts: layoutDraft }], `Saved ${view.name} layout`))}>Save layout</button></div>}
      <div className={`workspace-canvas ${loading ? 'refreshing' : ''}`} aria-busy={loading}>{!data || !context ? <div className="skeleton-grid"><div/><div/><div/></div> : <WorkspaceData.Provider value={context}><JSONUIProvider registry={registry} initialState={{}} handlers={{}}>
        {<MeasuredGrid layouts={layouts} breakpoints={{ lg: 1000, md: 700, sm: 0 }} cols={COLS} rowHeight={28} margin={[16,16]} containerPadding={[0,0]} compactor={noCompactor}
          dragConfig={{ enabled: editCanvas && !view.locked, handle: '.widget-drag-handle', cancel: 'button,input,select,a,summary' }} resizeConfig={{ enabled: editCanvas && !view.locked }}
          onBreakpointChange={setBreakpoint} onDragStart={() => setDragging(true)} onResizeStart={() => setDragging(true)} onDragStop={captureLayout} onResizeStop={captureLayout}>
          {view.widgets.map(id => { const widget = boot.spec.widgets[id]; return <section className={`widget ${widget.pinned ? 'pinned' : ''}`} key={id} data-widget-id={id} aria-label={widget.title}>
            <header className="widget-header"><div className="widget-drag-handle"><Icon name={widget.kind === 'CallTimeline' ? 'phone' : widget.kind === 'Commitments' ? 'clock' : widget.kind === 'EvidencePanel' ? 'link' : 'grid'} size={16}/><h2>{widget.title}</h2>{widget.pinned && <span title="Pinned against agent changes"><Icon name="pin" size={13}/></span>}</div><div><button className="icon-button" aria-label={`${widget.pinned ? 'Unpin' : 'Pin'} ${widget.title}`} disabled={view.locked} onClick={() => action(save([{ op: 'pin_widget', view_id: view.id, widget_id: id, pinned: !widget.pinned }], `${widget.pinned ? 'Unpinned' : 'Pinned'} ${widget.title}`))}><Icon name="pin" size={14}/></button>{editCanvas && <button className="icon-button" aria-label={`Configure ${widget.title}`} disabled={view.locked} onClick={() => { setWidgetId(id); setDialog('widget'); }}><Icon name="sliders" size={14}/></button>}</div></header>
            {editCanvas && <div className="keyboard-layout" aria-label={`Keyboard controls for ${widget.title}`}>{(['up','down','wider','narrower','taller','shorter'] as const).map(change => <button key={change} aria-label={`${change[0].toUpperCase() + change.slice(1)} ${widget.title}`} disabled={widget.pinned || view.locked} onClick={() => keyboardGeometry(id, change)}>{label(change)}</button>)}<button className="danger-text" aria-label={`Remove ${widget.title}`} disabled={view.locked || widget.pinned} onClick={() => action(save([{ op: 'remove_widget', view_id: view.id, widget_id: id }], `Removed ${widget.title}; records retained`))}>Remove</button></div>}
            <div className="widget-content"><WidgetBoundary><Renderer registry={registry} spec={{ root: id, elements: { [id]: { type: widget.kind, props: { widgetId: id }, children: [] } } }}/></WidgetBoundary></div>
          </section>; })}
        </MeasuredGrid>}
        {!view.widgets.length && <Empty title="Compose this workspace" text="Add widgets or restore a previous layout. Your underlying lead records have not changed." action={<button className="primary" onClick={() => setDialog('add_widget')}>Add widget</button>}/>}
        {detailOpen && detail && <LeadDetail key={detail.lead.id} detail={detail} bootstrap={boot} emphasis={view.emphasis} close={() => setDetailOpen(false)} refresh={refreshDetail} openCall={(id, reference) => setCall({ id, reference })} editLead={() => setDialog('edit_lead')} taskChange={taskChange}/>}
      </JSONUIProvider></WorkspaceData.Provider>}</div>
      <footer className="workspace-footer"><span>Sources stay separate from assessments. Assessments stay separate from layout.</span><span>{loading ? 'Refreshing authorized data…' : `Saved workspace v${boot.version}`} · {boot.timezone}</span></footer>
    </main>
    {noteSource && <NoteViewer key={noteSource.id} id={noteSource.id} leadId={noteSource.leadId} zone={boot.timezone} close={() => setNoteSource(null)}/>}
    {call && <CallViewer key={call.id} id={call.id} reference={call.reference} zone={boot.timezone} close={() => { setCall(null); action(refreshDetail()); }}/>}
    {(dialog === 'view' || dialog === 'duplicate') && <ViewEditor view={view} bootstrap={boot} duplicate={dialog === 'duplicate'} initialQuery={query} close={() => setDialog(null)} save={save}/>}
    {dialog === 'widget' && <WidgetEditor widget={boot.spec.widgets[widgetId]} fields={boot.fields} close={() => setDialog(null)} save={widget => save([{ op: 'configure_widget', view_id: view.id, widget }], `Configured ${widget.title}`)}/>}
    {dialog === 'add_widget' && <AddWidget close={() => setDialog(null)} save={addWidget}/>}
    {(dialog === 'lead' || dialog === 'edit_lead') && <LeadEditor lead={dialog === 'edit_lead' ? detail?.lead : undefined} close={() => setDialog(null)} saved={async id => { setRefreshCounter(n => n + 1); if (id && dialog === 'edit_lead') await refreshDetail(); setNotice('Lead saved. No calling action was performed.'); }}/>}
    {dialog === 'import' && <ImportEditor close={() => setDialog(null)} saved={async () => setRefreshCounter(n => n + 1)}/>}
    {dialog === 'field' && <FieldEditor close={() => setDialog(null)} saved={async () => { await loadBootstrap(); }}/>} 
    {dialog === 'rubric' && <RubricEditor rubric={boot.rubric} close={() => setDialog(null)} saved={async () => { await loadBootstrap(); }}/>} 
    {dialog === 'filters' && <Modal title="Search, filter & group" close={() => setDialog(null)} wide><QueryControls query={query} onChange={value => { setQuery(value); setPage(1); }} fields={boot.fields}/><footer className="modal-actions"><button onClick={() => { setQuery(view.query); setPage(1); }}>Reset to saved query</button><button onClick={() => setDialog('duplicate')}>Save as a new view</button><button className="primary" onClick={() => { if (view.id === 'all' && (query.search || query.filters.length)) { setDialog('duplicate'); return; } action(save([{ op: 'edit_view', view_id: view.id, query }], `Saved filters for ${view.name}`).then(() => setDialog(null))); }}>Save to this view</button></footer></Modal>}
    {dialog === 'settings' && <Modal title="Workspace agent settings" close={() => setDialog(null)}><div className="settings-section"><h3>Separate from the live voice agent</h3><p>Workspace reasoning uses {boot.orchestrator.model}. It has no dialing, booking, export, suppression, or provider-configuration tools.</p><dl className="operational"><dt>Server authorization</dt><dd>{boot.orchestrator.enabled_by_server ? 'Enabled' : 'Disabled in server configuration'}</dd><dt>Model key configured</dt><dd>{boot.orchestrator.configured ? 'Yes — server side only' : 'No'}</dd><dt>Worker</dt><dd>{boot.orchestrator.running ? 'Running while this server is on' : 'Not running'}</dd><dt>New extraction chunks per run</dt><dd>{boot.orchestrator.max_chunks_per_run}</dd><dt>Daily request cap</dt><dd>{boot.orchestrator.max_daily_requests}</dd><dt>Daily reserved-token cap</dt><dd>{boot.orchestrator.max_daily_reserved_tokens}</dd></dl><p className="notice">Enabling reasoning sends relevant captured real-call text and human notes to OpenAI. Set <code>WORKSPACE_ENABLED=true</code> and a server-side <code>WORKSPACE_API_KEY</code> and <code>WORKSPACE_MODEL</code>. The workspace uses a separate explicit key setting; it does not fall back to the voice key. Restart Relay. This does not enable outbound calling.</p><button disabled={!boot.orchestrator.enabled_by_server} onClick={() => action(api('/api/workspace/settings/pause', 'POST', { paused: !boot.orchestrator.paused }).then(() => loadBootstrap()))}>{boot.orchestrator.paused ? 'Resume workspace reasoning' : 'Pause workspace reasoning'}</button></div><div className="settings-section"><h3>Organization behavior</h3><p><strong>Manual:</strong> keep agent presentation changes as proposals. <strong>Suggest:</strong> preview every agent layout change. <strong>Adaptive:</strong> apply small reversible changes to unlocked content; preview larger changes.</p><label className="check-label"><input type="checkbox" checked={boot.spec.allow_structural_auto} onChange={e => action(save([{ op: 'preferences', mode: boot.spec.mode, default_view: boot.spec.default_view, allow_structural_auto: e.target.checked }], 'Updated structural organization preference'))}/>Allow small structural changes automatically in Adaptive mode</label><label>Default saved view<select value={boot.spec.default_view} onChange={e => action(save([{ op: 'preferences', mode: boot.spec.mode, default_view: e.target.value, allow_structural_auto: boot.spec.allow_structural_auto }], 'Updated the default view'))}>{boot.spec.views.map(v => <option key={v.id} value={v.id}>{v.name}</option>)}</select></label><p className="hint">Pinned widgets and locked views remain protected. Material changes are held while you edit, select, drag or read details.</p></div></Modal>}
    {dialog === 'history' && <Modal title="Workspace history & restore" close={() => setDialog(null)} wide><p>Restore changes presentation only. It never deletes lead records, transcripts, assessments or tasks.</p><div className="modal-actions"><button disabled={boot.version <= 1} onClick={() => action(restore(boot.version - 1))}>Undo last workspace change</button><button onClick={() => { if (window.confirm('Reset the layout to defaults? All lead records and evidence are retained.')) action(restore()); }}>Reset layout</button></div>{revisions.map(revision => <div className="revision" key={revision.version}><div><strong>Version {revision.version} · {label(revision.actor)}</strong><p>{revision.reason}</p><small>{date(revision.created_at, boot.timezone)}</small></div><button disabled={revision.version === boot.version} onClick={() => action(restore(revision.version))}>Restore</button></div>)}{historyMore && <button onClick={() => action(showHistory(revisions.at(-1)?.version))}>Load older workspace versions</button>}</Modal>}
    {dialog === 'proposals' && <Modal title="Review organization changes" close={() => setDialog(null)} wide>{boot.proposals.map(proposal => <article className="proposal" key={proposal.id}><h3>{proposal.data.reason}</h3><small>Based on workspace v{proposal.base_version}. Current: v{boot.version}.</small><pre>{JSON.stringify(proposal.data.operations, null, 2)}</pre><div className="modal-actions"><button onClick={() => action(api(`/api/workspace/proposals/${proposal.id}`, 'POST', { approve: false, base_version: boot.version }).then(() => loadBootstrap()))}>Reject</button><button className="primary" disabled={proposal.base_version !== boot.version} onClick={() => action(api(`/api/workspace/proposals/${proposal.id}`, 'POST', { approve: true, base_version: boot.version }).then(() => loadBootstrap()))}>Approve saved change</button></div>{proposal.base_version !== boot.version && <p className="notice warning">Stale proposal: it cannot overwrite your newer workspace. Reject it and issue a fresh instruction.</p>}</article>)}</Modal>}
    {dialog === 'jobs' && <Modal title="Workspace analysis runs" close={() => setDialog(null)} wide>{!jobs.length && <Empty title="No analysis runs yet" text="Configure server-side reasoning to process captured real calls. Manual controls do not require a model."/>}{jobs.map(job => <article className="revision" key={job.id}><div><div className="tags"><Badge value={job.status}/><Badge>{job.kind}</Badge></div><p>{job.error || job.result?.workspace?.reason || `Run ${job.id.slice(-8)}`}</p><small>{date(job.created_at, boot.timezone)} · {job.model} · {job.attempts} attempts</small></div>{['failed','retry','waiting_configuration'].includes(job.status) && <button onClick={() => action(api(`/api/workspace/jobs/${job.id}/retry`, 'POST').then(showJobs))}>Retry</button>}</article>)}</Modal>}
  </div>;
}
