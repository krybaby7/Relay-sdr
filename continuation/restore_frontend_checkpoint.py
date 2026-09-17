"""One-time restoration of source changes recovered from the interrupted run.

Only the five exact known frontend base blobs are accepted. No backend, recovery,
credentials, records, or calling configuration is modified. The resulting native
files must be committed and reverified; historical tests are not proof of this tree.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = {
    'App.tsx': '3a9f72d3f33958d32a8f3a543ba8756715f226bf',
    'api.ts': 'b24149283d6068a63653eea335f4faf6a145e556',
    'catalog.tsx': '39b0f368371fe941af6792f09f12534491726b42',
    'details.tsx': '2f14b1194512a309c5e9c3a9502ac611efcbbd78',
    'types.ts': '1822df910dab8a2d4dcc07a96c05c6053653f432',
}


def blob(data: bytes) -> str:
    return hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()


def main():
    texts = {}
    for name, expected in BASE.items():
        path = ROOT / 'frontend' / 'src' / name
        raw = path.read_bytes()
        if blob(raw) != expected:
            raise SystemExit(f'Refusing to replace changed source: {name}. Reconcile manually; do not reset it.')
        texts[name] = raw.decode('utf-8')
    matches = []

    def edit(name, old, new, limit=None):
        count = texts[name].count(old)
        matches.append({'file': name, 'pattern': old[:120], 'matches': count})
        if not count:
            print('REVIEW: recovered replacement did not match:', name, old[:100])
        texts[name] = texts[name].replace(old, new, count if limit is None else limit)

    # Original finish_ui.py, frontend-only portion. Backend patches are already applied.
    edit('api.ts', '  return response.json() as Promise<T>;', "  const value = await response.json() as T;\n  if (signal?.aborted || sessionStorage.getItem('relay-token') !== token) throw new DOMException('Request superseded', 'AbortError');\n  return value;")
    edit('App.tsx', 'import { CallViewer, LeadDetail }', 'import { CallViewer, LeadDetail, NoteViewer }')
    edit('App.tsx', 'const [selected, setSelected]', "const [noteSource, setNoteSource] = useState<{ id: string; leadId: string } | null>(null);\n  const [selected, setSelected]")
    edit('App.tsx', 'busy.current = detailOpen || !!call || !!dialog || !!layoutDraft || dragging', 'busy.current = detailOpen || !!call || !!noteSource || !!dialog || !!layoutDraft || dragging || editCanvas')
    edit('App.tsx', 'setBoot(fresh); setViewId(id); setQuery(fresh.spec.views.find(v => v.id === id)!.query);', '''const oldView = bootRef.current?.spec.views.find(v => v.id === id);
      const localQuery = queryRef.current;
      const preserveQuery = !initial && id === viewRef.current && oldView && localQuery && JSON.stringify(localQuery) !== JSON.stringify(oldView.query);
      setBoot(fresh); setViewId(id); setQuery(preserveQuery ? localQuery : fresh.spec.views.find(v => v.id === id)!.query);''')
    edit('App.tsx', ').then(([records, metrics, tasks, calls, activity]) => { setData', ').then(([records, metrics, tasks, calls, activity]) => { if (controller.signal.aborted) return; setData')
    edit('App.tsx', '<code>WORKSPACE_OPENAI_API_KEY</code> (or the existing server key)', '<code>WORKSPACE_API_KEY</code> and <code>WORKSPACE_MODEL</code>. The workspace uses a separate explicit key setting; it does not fall back to the voice key')
    edit('App.tsx', '<LeadDetail detail={detail}', '<LeadDetail key={detail.lead.id} detail={detail}')
    edit('App.tsx', '<CallViewer id={call.id}', '<CallViewer key={call.id} id={call.id}')
    edit('types.ts', 'export interface AssessmentData { potential:', 'export interface AssessmentData { playbook_approved?: boolean; human_facts?: { reference: Reference; topic: string; text: string; value: string }[]; potential:')
    edit('types.ts', 'export interface Segment { id:', 'export interface Segment { page_offset?: number; id:')
    edit('details.tsx', 'import type { Assessment,', 'import type { Note, CallRow, Assessment,')
    insert = '''function PageControls({ page, hasMore, change }: { page: number; hasMore: boolean; change: (page: number) => void }) {
  return <div className="pagination"><button disabled={page <= 1} onClick={() => change(page - 1)}>Previous page</button><span>Page {page}</span><button disabled={!hasMore} onClick={() => change(page + 1)}>Next page</button></div>;
}
function useCollection<T>(url: string, refresh: unknown) {
  const [page, setPage] = useState(1);
  const [state, setState] = useState<{ items: T[]; has_more: boolean; page: number }>({ items: [], has_more: false, page: 1 });
  const [error, setError] = useState('');
  useEffect(() => {
    const controller = new AbortController();
    void api<typeof state>(`${url}?page=${page}&page_size=25`, 'GET', undefined, controller.signal).then(value => { if (!controller.signal.aborted) { setState(value); setError(''); } }).catch(e => { if (!controller.signal.aborted) setError((e as Error).message); });
    return () => controller.abort();
  }, [url, page, refresh]);
  return { ...state, error, setPage };
}
export function NoteViewer({ id, leadId, zone, close }: { id: string; leadId: string; zone: string; close: () => void }) {
  const [note, setNote] = useState<Note | null>(null); const [error, setError] = useState('');
  useEffect(() => { const controller = new AbortController(); void api<Note>(`/api/workspace/notes/${id}?lead_id=${leadId}`, 'GET', undefined, controller.signal).then(setNote).catch(e => { if (!controller.signal.aborted) setError((e as Error).message); }); return () => controller.abort(); }, [id, leadId]);
  return <Modal title="Human source note" close={close}>{error && <p className="error">{error}</p>}{note ? <article className="human-note"><Badge>{note.confirmed ? 'Human-confirmed correction' : 'Unconfirmed human note'}</Badge><blockquote>{note.text}</blockquote><p>{label(note.topic)} · {label(note.value)} · {date(note.created_at, zone)}</p>{!note.active && <p className="notice warning">Superseded note, retained as historical evidence.</p>}<small>Source {note.id}</small></article> : !error && <p>Loading note…</p>}</Modal>;
}

'''
    edit('details.tsx', 'export function LeadDetail', insert + 'export function LeadDetail', 1)
    edit('details.tsx', '  const assessment =', '''  const notesPage = useCollection<Note>(`/api/workspace/leads/${detail.lead.id}/collections/notes`, detail);
  const tasksPage = useCollection<Task>(`/api/workspace/leads/${detail.lead.id}/collections/tasks`, detail);
  const callsPage = useCollection<CallRow>(`/api/workspace/leads/${detail.lead.id}/calls`, detail);
  const historyPage = useCollection<Detail['history'][number]>(`/api/workspace/leads/${detail.lead.id}/collections/history`, detail);
  const assessment =''')
    for old, new in [('detail.history.length', 'historyPage.items.length'), ('detail.history.map', 'historyPage.items.map'), ('detail.tasks.length', 'tasksPage.items.length'), ('detail.tasks.map', 'tasksPage.items.map'), ('detail.calls.length', 'callsPage.items.length'), ('detail.calls.map', 'callsPage.items.map'), ('detail.notes.map', 'notesPage.items.map')]:
        edit('details.tsx', old, new)
    edit('details.tsx', '{error && <p className="error" role="alert">{error}</p>}', '{[error, notesPage.error, tasksPage.error, callsPage.error, historyPage.error].filter(Boolean).map((message, i) => <p className="error" role="alert" key={i}>{message}</p>)}', 1)
    edit('details.tsx', '{callsPage.items.length >= 50 && <p className="notice">Showing the 50 most recent linked calls. Use the paginated Calls API for older records.</p>}', '<PageControls page={callsPage.page} hasMore={callsPage.has_more} change={callsPage.setPage}/>')
    edit('details.tsx', '<form onSubmit={e => { e.preventDefault(); void submitNote(); }}>', '<PageControls page={notesPage.page} hasMore={notesPage.has_more} change={notesPage.setPage}/><form onSubmit={e => { e.preventDefault(); void submitNote(); }}>')
    edit('details.tsx', "onChange={e => setTopic(e.target.value)}>{['note','need','fit','intent','authority','timing','objection']", "onChange={e => { setTopic(e.target.value); if (e.target.value === 'note') setConfirmed(false); }}>{['note','need','fit','intent','authority','timing','objection','budget','decision_process','procurement','proposal','decision_needed']")
    edit('details.tsx', '<input type="checkbox" checked={confirmed}', '<input type="checkbox" disabled={topic === \'note\'} checked={confirmed}')
    edit('details.tsx', 'Confirmed corrections take precedence in reconciliation.', 'Select a factual topic to confirm a correction. Confirmed corrections take precedence in reconciliation.')
    edit('details.tsx', '      {!!assessment.conflicts.length', '''      {assessment.playbook_approved === false && <p className="notice">Sales playbook not approved. Product fit and commercial potential remain unknown.</p>}
      {!!assessment.human_facts?.length && <section><h3>Human-confirmed facts</h3>{assessment.human_facts.map(fact => <article className="human-note" key={fact.reference.note_id}><Badge>{label(fact.topic)} · {label(fact.value)}</Badge><p>{fact.text}</p><EvidenceLink reference={fact.reference}/></article>)}</section>}
      {!!assessment.conflicts.length''')
    edit('details.tsx', '    </section> : <Empty title="This lead', '      <PageControls page={historyPage.page} hasMore={historyPage.has_more} change={historyPage.setPage}/>\n    </section> : <Empty title="This lead')
    edit('details.tsx', 'Save due time</button></div></article>)}</section>', 'Save due time</button></div></article>)}<PageControls page={tasksPage.page} hasMore={tasksPage.has_more} change={tasksPage.setPage}/></section>')
    edit('details.tsx', '<input type={field.type', '<input step="any" type={field.type')
    edit('details.tsx', '.then(setData).catch(e => { if (!controller.signal.aborted)', '.then(value => { if (!controller.signal.aborted) setData(value); }).catch(e => { if (!controller.signal.aborted)')
    edit('details.tsx', 'api<Segment>(`/api/workspace/segments/${reference.segment_id}?lead_id=${data.call.lead_id}`', 'api<Segment>(`/api/workspace/segments/${reference.segment_id}?lead_id=${data.call.lead_id}&call_id=${id}`')
    edit('details.tsx', '.then(segment => { if (!segment.active) setReplaced(true); setOffset(Math.max(0, segment.seq - 4)); })', '.then(segment => { if (controller.signal.aborted) return; if (!segment.active) setReplaced(true); setOffset(Math.max(0, (segment.page_offset ?? 0) - 3)); })')
    edit('details.tsx', '  }, [data, reference]);', '  }, [data, reference, id]);')
    edit('details.tsx', 'rows={4} value={text}', 'rows={4} maxLength={16000} value={text}')

    # Original finish_ui2.py and the final label/context corrections.
    edit('App.tsx', "if (ref.note_id) { setDetailOpen(true); setNotice(`Supporting human note: ${ref.note_id}. Open Notes & corrections.`); }", 'if (ref.note_id && detailRef.current) setNoteSource({id: ref.note_id, leadId: detailRef.current.lead.id});')
    edit('App.tsx', '    {call && <CallViewer', '    {noteSource && <NoteViewer key={noteSource.id} id={noteSource.id} leadId={noteSource.leadId} zone={boot.timezone} close={() => setNoteSource(null)}/>}\n    {call && <CallViewer')
    edit('App.tsx', 'close={() => setCall(null)}', 'close={() => { setCall(null); action(refreshDetail()); }}')
    edit('App.tsx', 'setCall(null); setDialog(null);', "setCall(null); setNoteSource(null); setDialog(null); setActiveJob(null); setSelected(new Set()); setQuery(null); setLayoutDraft(null); setToken('');")
    edit('App.tsx', 'const busy = useRef(false);', 'const detailRequest = useRef(0); const busy = useRef(false);')
    edit('App.tsx', "async function openLead(id: string) { setError(''); try { const result = await api<Detail>(`/api/workspace/leads/${id}`); setDetail(result); setDetailOpen(true); }", "async function openLead(id: string) { const request = ++detailRequest.current; setError(''); try { const result = await api<Detail>(`/api/workspace/leads/${id}`); if (request !== detailRequest.current) return; setDetail(result); setDetailOpen(true); }")
    edit('App.tsx', 'async function refreshDetail() { if (detailRef.current) setDetail(await api<Detail>(`/api/workspace/leads/${detailRef.current.lead.id}`)); setRefreshCounter(n => n + 1); }', 'async function refreshDetail() { const id = detailRef.current?.lead.id; if (id) { const result = await api<Detail>(`/api/workspace/leads/${id}`); if (id === detailRef.current?.lead.id) setDetail(result); } setRefreshCounter(n => n + 1); }')
    edit('details.tsx', 'const [correction, setCorrection] =', "const [redaction, setRedaction] = useState<Segment | null>(null); const [redactReason, setRedactReason] = useState(''); const [redactConfirmed, setRedactConfirmed] = useState(false);\n  const [correction, setCorrection] =")
    edit('details.tsx', '  async function saveCorrection()', '''  async function saveRedaction() {
    if (!data || !redaction) return;
    try {
      await api(`/api/workspace/segments/${redaction.id}/redact`, 'POST', { revision: data.capture.revision, reason: redactReason, confirm: redactConfirmed });
      setRedaction(null); setData(await api<CallDetail>(`/api/workspace/calls/${id}?offset=${offset}&include_replaced=${replaced}`));
    } catch (e) { setError((e as Error).message); }
  }
  async function saveCorrection()''')
    edit('details.tsx', '>Correct</button></span>', '>Correct</button><button aria-label={`Redact source segment ${segment.seq}`} disabled={segment.redacted} onClick={() => { setRedaction(segment); setRedactReason(\'\'); setRedactConfirmed(false); }}>Redact</button></span>')
    edit('details.tsx', '    {correction &&', '''    {redaction && <div className="correction-editor"><h3>Redact source segment #{redaction.seq}</h3><p>This removes all revisions of this logical fragment and invalidates affected local intelligence and cached analysis. Independent human notes, saved presentation labels, backups and external deliveries require separate review. This cannot be undone.</p><label>Redaction reason<input minLength={5} maxLength={500} value={redactReason} onChange={e => setRedactReason(e.target.value)}/></label><label className="check-label"><input type="checkbox" checked={redactConfirmed} onChange={e => setRedactConfirmed(e.target.checked)}/>I confirm deletion of these captured source revisions</label><div className="modal-actions"><button onClick={() => setRedaction(null)}>Cancel redaction</button><button className="danger" disabled={!redactConfirmed || redactReason.length < 5} onClick={() => void saveRedaction()}>Redact captured source</button></div></div>}
    {correction &&''')
    edit('details.tsx', '<label>Topic<select', '<label>Topic<select aria-label="Topic"')
    edit('details.tsx', '<label>Criterion answer<select', '<label>Criterion answer<select aria-label="Criterion answer"')

    # Mount width measurement only when the actual canvas is mounted.
    edit('App.tsx', 'import type { Layout }', 'import type { Layout, ResponsiveGridLayoutProps }')
    edit('App.tsx', 'export default function App()', '''function MeasuredGrid(props: Omit<ResponsiveGridLayoutProps<Breakpoint>, 'width'>) {
  // This component mounts with its element present; the login/loading shell does not.
  const { width, containerRef, mounted } = useContainerWidth({ measureBeforeMount: true });
  return <div ref={containerRef}>{mounted && <Responsive<Breakpoint> {...props} width={width}/>}</div>;
}

export default function App()''')
    edit('App.tsx', '  const { width, containerRef, mounted } = useContainerWidth();\n', '')
    edit('App.tsx', '<div ref={containerRef} className={`workspace-canvas', '<div className={`workspace-canvas')
    edit('App.tsx', '{mounted && <Responsive<Breakpoint> width={width}', '{<MeasuredGrid')
    edit('App.tsx', '</Responsive>}', '</MeasuredGrid>}')

    # Original paged_widgets.py, excluding its superseded guessed-view experiment.
    edit('catalog.tsx', 'createContext, useContext', 'createContext, useContext, useEffect, useState')
    edit('catalog.tsx', 'Task, Query }', 'Task, Query, CallRow }')
    edit('catalog.tsx', 'import { date, label }', 'import { api, date, label }')
    edit('catalog.tsx', '  bootstrap: Bootstrap; data:', '  viewId: string; bootstrap: Bootstrap; data:')
    paged = '''function useWidgetPage<T>(endpoint: 'tasks' | 'calls', ctx: Context, limit: number) {
  const [page, setPage] = useState(1); const [value, setValue] = useState<{items: T[]; has_more: boolean} | null>(null); const [error, setError] = useState('');
  const queryKey = JSON.stringify(ctx.query); const cursor = ctx.bootstrap.cursor;
  useEffect(() => { setPage(1); }, [queryKey, ctx.viewId, limit]);
  useEffect(() => {
    const controller = new AbortController(); setError('');
    void api<{items: T[]; has_more: boolean}>(`/api/workspace/${endpoint}/query`, 'POST', {view_id: ctx.viewId, query: JSON.parse(queryKey), page, page_size: limit}, controller.signal).then(setValue).catch(e => { if (!controller.signal.aborted) setError((e as Error).message); });
    return () => controller.abort();
  }, [endpoint, queryKey, ctx.viewId, page, limit, cursor]);
  return {page, setPage, value, error};
}
function WidgetPages({ page, hasMore, change }: {page:number; hasMore:boolean; change:(page:number)=>void}) {
  return <div className="pager"><span>Page {page}</span><div><button disabled={page === 1} onClick={() => change(page - 1)}>Previous page</button><button disabled={!hasMore} onClick={() => change(page + 1)}>Next page</button></div></div>;
}
'''
    edit('catalog.tsx', 'function Commitments(', paged + 'function Commitments(', 1)
    edit('catalog.tsx', '  if (!ctx.data.tasks.items.length)', '''  const result = useWidgetPage<Task>('tasks', ctx, widget.limit);
  if (result.error) return <p className="error">{result.error}</p>;
  if (!result.value) return <p className="loading">Loading internal tasks…</p>;
  if (!result.value.items.length)''')
    edit('catalog.tsx', 'ctx.data.tasks.items.slice(0, widget.limit).map', 'result.value.items.map')
    edit('catalog.tsx', '</p></div>;\n}\nfunction CallTimeline', '</p><WidgetPages page={result.page} hasMore={result.value.has_more} change={result.setPage}/></div>;\n}\nfunction CallTimeline')
    edit('catalog.tsx', '  if (!ctx.data.calls.items.length)', '''  const result = useWidgetPage<CallRow>('calls', ctx, widget.limit);
  if (result.error) return <p className="error">{result.error}</p>;
  if (!result.value) return <p className="loading">Loading captured calls…</p>;
  if (!result.value.items.length)''')
    edit('catalog.tsx', 'ctx.data.calls.items.slice(0, widget.limit).map', 'result.value.items.map')
    # The original replacement was deliberately scoped to these two widgets.
    start = texts['catalog.tsx'].index('function Commitments(')
    end = texts['catalog.tsx'].index('function EvidencePanel(', start)
    part = texts['catalog.tsx'][start:end].replace('size={15}/></button>)}</div>;', 'size={15}/></button>)}<WidgetPages page={result.page} hasMore={result.value.has_more} change={result.setPage}/></div>;')
    texts['catalog.tsx'] = texts['catalog.tsx'][:start] + part + texts['catalog.tsx'][end:]
    edit('App.tsx', 'const context = data ? { bootstrap:', 'const context = data ? { viewId: view.id, bootstrap:')
    # Do NOT reapply the final no-op key={v.id} aria-label patch: actual tabs use saved.id.

    result = {'provenance': 'Reconstructed from surviving interrupted-run source-writing commands. Not an exact filesystem recovery or a release.', 'files': {}, 'replacements': matches}
    for name, text in texts.items():
        raw = text.encode('utf-8')
        result['files']['frontend/src/' + name] = {'base_git_blob': BASE[name], 'restored_git_blob': blob(raw), 'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw)}
    for name, text in texts.items():
        (ROOT / 'frontend' / 'src' / name).write_text(text, encoding='utf-8')
    ignore = ROOT / '.gitignore'
    content = ignore.read_text()
    for pattern in ['frontend/node_modules/', 'frontend/playwright-report/', 'frontend/test-results/', '.ruff_cache/', 'verification/local/']:
        if pattern not in content.splitlines():
            content += '\n' + pattern + '\n'
    ignore.write_text(content)
    (ROOT / 'continuation' / 'PRESERVED-FRONTEND.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'restored': list(result['files']), 'zero_match_replacements': sum(not x['matches'] for x in matches)}, indent=2))


if __name__ == '__main__':
    main()
