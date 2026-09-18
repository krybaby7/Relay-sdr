import { createContext, useContext, useEffect, useState } from 'react';
import { defineCatalog } from '@json-render/core';
import { schema } from '@json-render/react/schema';
import { defineRegistry } from '@json-render/react';
import { z } from 'zod';
import type { Bootstrap, Dataset, Detail, LeadRow, Reference, Widget, Task, Query, CallRow } from './types';
import { Badge, Empty, Icon } from './ui';
import { readApi, date, label } from './api';

// Deliberately closed leaf components. catalog.prompt() is NEVER called: version
// 0.20.0's default sample-data instructions are incompatible with live CRM data.
const props = z.object({ widgetId: z.string().regex(/^[a-zA-Z][a-zA-Z0-9_-]{0,63}$/) }).strict();
const definition = { props, description: 'Render authorized server data through a stable workspace widget reference. No embedded records or totals.' };
export const catalog = defineCatalog(schema, { components: {
  PriorityQueue: definition, LeadsTable: definition, PipelineBoard: definition, Commitments: definition,
  CallTimeline: definition, EvidencePanel: definition, Questions: definition, RecentChanges: definition, Objections: definition,
}, actions: {} });

interface Context {
  viewId: string; bootstrap: Bootstrap; data: Dataset; dataVersion: number; detail: Detail | null; query: Query;
  selected: Set<string>; toggleSelection: (id: string) => void;
  openLead: (id: string) => void; openCall: (id: string, ref?: Reference) => void;
  evidence: (ref: Reference) => void; task: (task: Task, status: string) => void;
  sort: (field: Query['sort']) => void; page: (page: number) => void;
}
export const WorkspaceData = createContext<Context | null>(null);
export function useWorkspace() { const context = useContext(WorkspaceData); if (!context) throw new Error('Workspace data provider missing'); return context; }
function useWidget(id: string): [Context, Widget] { const ctx = useWorkspace(); const widget = ctx.bootstrap.spec.widgets[id]; if (!widget) throw new Error('Unknown widget reference'); return [ctx, widget]; }
export function EvidenceLink({ reference }: { reference: Reference }) {
  const ctx = useWorkspace();
  return <button className="evidence-link" onClick={() => ctx.evidence(reference)}><Icon name="link" size={13}/>{reference.note_id ? 'Human note' : reference.segment_id ? 'View source' : 'View request'}</button>;
}
function Cell({ row, field }: { row: LeadRow; field: string }) {
  const ctx = useWorkspace();
  if (field === 'name') return <button className="lead-name" onClick={() => ctx.openLead(row.id)}><span className="avatar">{row.name.slice(0, 2).toUpperCase()}</span><span>{row.name}{row.stale && <small className="stale-text">Assessment stale</small>}</span></button>;
  if (['potential', 'priority', 'confidence', 'eligibility', 'stage'].includes(field)) return <Badge value={String(row[field])}/>;
  if (field === 'assessment_at') return <span className="muted">{date(row.assessment_at, ctx.bootstrap.timezone)}</span>;
  return <span className={row[field] == null || row[field] === '' ? 'muted' : ''}>{label(row[field])}</span>;
}
function LeadsTable({ widgetId }: { widgetId: string }) {
  const [ctx, widget] = useWidget(widgetId); const columns = widget.columns.filter(c => c.visible);
  if (!ctx.data.records.total) return <Empty title="No leads match this view" text="Try All leads, change your filters, or add a contact. Unassessed never means low quality."/>;
  return <><div className="table-scroll"><table className="leads-table"><thead><tr><th className="select-cell"><span className="sr-only">Select</span></th>{columns.map(c => <th key={c.field} style={{ minWidth: c.width, width: c.width }}><button onClick={() => { if (['name','company','potential','priority','stage','assessment_at'].includes(c.field)) ctx.sort(c.field as Query['sort']); }}>{ctx.bootstrap.fields.find(f => f.id === c.field)?.name || label(c.field)}{ctx.query.sort === c.field && (ctx.query.direction === 'desc' ? ' ↓' : ' ↑')}</button></th>)}</tr></thead>
    <tbody>{ctx.data.records.items.map((row, index, rows) => <Rows key={row.id} row={row} previous={index ? rows[index - 1] : null} columns={columns}/>)}</tbody></table></div>
    <DirectoryPages/></>;
}
function DirectoryPages() {
  const ctx = useWorkspace(); const records = ctx.data.records;
  return <div className="pager" aria-label="Lead directory pages"><span>{records.total ? (records.page - 1) * records.page_size + 1 : 0}–{Math.min(records.page * records.page_size, records.total)} of {records.total}</span><div><button disabled={records.page === 1} onClick={() => ctx.page(records.page - 1)}>Previous</button><button disabled={!records.has_more} onClick={() => ctx.page(records.page + 1)}>Next</button></div></div>;
}
function Rows({ row, previous, columns }: { row: LeadRow; previous: LeadRow | null; columns: Widget['columns'] }) {
  const ctx = useWorkspace(); const grouped = ctx.query.group !== 'none';
  return <>{grouped && (!previous || previous[ctx.query.group] !== row[ctx.query.group]) && <tr className="group-row"><td colSpan={columns.length + 1}>{label(row[ctx.query.group])}</td></tr>}
  <tr className={ctx.selected.has(row.id) ? 'selected-row' : ''}><td className="select-cell"><input type="checkbox" aria-label={`Select ${row.name}`} checked={ctx.selected.has(row.id)} onChange={() => ctx.toggleSelection(row.id)}/></td>{columns.map(column => <td key={column.field}><Cell row={row} field={column.field}/></td>)}</tr></>;
}
function PriorityQueue({ widgetId }: { widgetId: string }) {
  const [ctx, widget] = useWidget(widgetId);
  if (!ctx.data.records.items.length) return <Empty title="Your attention queue is clear" text="Due commitments, unresolved decisions and review items appear here. Nothing has been fabricated."/>;
  return <div className="priority-list">{ctx.data.records.items.slice(0, widget.limit).map((lead, i) => <button className="priority-item" key={lead.id} onClick={() => ctx.openLead(lead.id)}><span className="queue-number">{String((ctx.data.records.page - 1) * ctx.data.records.page_size + i + 1).padStart(2, '0')}</span><span className="queue-copy"><strong>{lead.name}<small>{lead.company}</small></strong><span>{lead.next_action || 'No recorded commitment. Qualification is still open.'}</span><span className="tags"><Badge value={lead.potential}/><Badge value={lead.eligibility}/>{lead.stale && <Badge value="review">Stale assessment</Badge>}</span></span><span className="queue-end"><Badge value={lead.priority}/><Icon name="arrow" size={17}/></span></button>)}<p className="widget-footnote">Potential is opportunity fit. Priority is action timing. Contact permission is separate.</p></div>;
}
function PipelineBoard({ widgetId }: { widgetId: string }) {
  const [ctx] = useWidget(widgetId); const stages = [...new Set(['unassessed','qualification','engaged','proposal','decision', ...ctx.data.metrics.stages.map(s => s.stage)])];
  if (!ctx.data.metrics.total) return <Empty title="The pipeline starts with evidence" text="No real leads match this view. Connection status alone never creates a qualified opportunity."/>;
  return <><div className="board">{stages.map(stage => <section className="board-column" key={stage}><h3>{label(stage)}<span>{ctx.data.metrics.stages.find(s => s.stage === stage)?.count || 0}</span></h3>{ctx.data.records.items.filter(row => row.stage === stage).map(row => <button className="board-card" key={row.id} onClick={() => ctx.openLead(row.id)}><strong>{row.name}</strong><small>{row.company}</small><Badge value={row.potential}/><span>{label(row.priority)}</span></button>)}</section>)}</div><p className="widget-footnote">Stage counts cover this view. Cards show the current directory page; open a card to inspect its evidence.</p><DirectoryPages/></>;
}
function useWidgetPage<T>(endpoint: 'tasks' | 'calls', ctx: Context, limit: number) {
  const [page, setPage] = useState(1); const [value, setValue] = useState<{items: T[]; has_more: boolean} | null>(null); const [error, setError] = useState('');
  const queryKey = JSON.stringify(ctx.query); const cursor = ctx.bootstrap.cursor; const [retry, setRetry] = useState(0);
  useEffect(() => { setPage(1); }, [queryKey, ctx.viewId, limit]);
  useEffect(() => {
    const controller = new AbortController(); setError(''); setValue(null);
    void readApi<{items: T[]; has_more: boolean}>(`/api/workspace/${endpoint}/query`, 'POST', {view_id: ctx.viewId, query: JSON.parse(queryKey), page, page_size: limit}, controller.signal).then(setValue).catch(e => { if (!controller.signal.aborted) setError((e as Error).message); });
    return () => controller.abort();
  }, [endpoint, queryKey, ctx.viewId, page, limit, cursor, ctx.dataVersion, retry]);
  return {page, setPage, value, error, retry: () => setRetry(n => n + 1)};
}
function WidgetPages({ page, hasMore, change }: {page:number; hasMore:boolean; change:(page:number)=>void}) {
  return <div className="pager"><span>Page {page}</span><div><button disabled={page === 1} onClick={() => change(page - 1)}>Previous page</button><button disabled={!hasMore} onClick={() => change(page + 1)}>Next page</button></div></div>;
}
function Commitments({ widgetId }: { widgetId: string }) {
  const [ctx, widget] = useWidget(widgetId);
  const result = useWidgetPage<Task>('tasks', ctx, widget.limit);
  if (result.error) return <div role="alert"><p className="error">{result.error}</p><button onClick={result.retry}>Retry loading this widget</button></div>;
  if (!result.value) return <p className="loading">Loading internal tasks…</p>;
  if (!result.value.items.length) return <Empty title="No recorded commitments" text="Agreements and recommendations stay separate. Saving a follow-up never calls or messages anyone."/>;
  return <div className="task-list">{result.value.items.map(task => <article className="task-item" key={task.id}><div className="task-icon"><Icon name="clock"/></div><div><button className="text-button" onClick={() => ctx.openLead(task.lead_id)}>{task.name || 'Open lead'}</button><p>{task.data.wording}</p><div className="tags"><Badge value={task.status}/><Badge>{task.data.nature === 'extracted_commitment' ? `${label(task.party)} commitment` : label(task.data.nature)}</Badge></div><small>{task.due_at ? date(task.due_at, ctx.bootstrap.timezone) : task.data.date_phrase || 'Date not agreed'} · {label(task.data.date_resolution)}</small>{task.data.reference && <EvidenceLink reference={task.data.reference}/>}<div className="task-actions"><button onClick={() => ctx.task(task, task.status === 'done' ? 'open' : 'done')}>{task.status === 'done' ? 'Reopen internal task' : 'Mark internal task done'}</button></div></div></article>)}<p className="widget-footnote">Showing up to {widget.limit} of {ctx.data.tasks.total} internal tasks. Requests are not bookings or transfers.</p><WidgetPages page={result.page} hasMore={result.value.has_more} change={result.setPage}/></div>;
}
function CallTimeline({ widgetId }: { widgetId: string }) {
  const [ctx, widget] = useWidget(widgetId);
  const result = useWidgetPage<CallRow>('calls', ctx, widget.limit);
  if (result.error) return <div role="alert"><p className="error">{result.error}</p><button onClick={result.retry}>Retry loading this widget</button></div>;
  if (!result.value) return <p className="loading">Loading captured calls…</p>;
  if (!result.value.items.length) return <Empty title="No calls captured in this view" text="Every captured call remains available, including unanswered attempts and practice sessions in their own view."/>;
  return <div className="timeline">{result.value.items.map(call => <button className="timeline-item" key={call.call_id} onClick={() => ctx.openCall(call.call_id)}><span className="timeline-dot"/><span><strong>{call.name || (call.kind === 'simulation' ? 'Scripted demo' : 'Unlinked practice')}</strong><small>{date(call.created_at, ctx.bootstrap.timezone)}</small><span className="tags"><Badge value={call.status}/><Badge>{call.kind === 'twilio' ? 'Phone record' : 'Practice only'}</Badge></span><small>{call.segment_count} captured fragments · {call.dropped ? 'Capture truncated' : call.close_observed ? 'Close observed; completeness unverified' : 'Incomplete / unverified capture'}</small></span><Icon name="arrow" size={15}/></button>)}<WidgetPages page={result.page} hasMore={result.value.has_more} change={result.setPage}/></div>;
}
function EvidencePanel({ widgetId }: { widgetId: string }) {
  const [ctx] = useWidget(widgetId); const assessment = ctx.detail?.assessment?.data;
  if (!ctx.detail) return <Empty title="Select a lead to inspect the reasons" text="Supported claims link back to captured source fragments. Uncertainty and conflicting information stay visible."/>;
  if (!assessment) return <Empty title="This lead is unassessed" text="No supported assessment is available. Open details to review calls or add a human correction."/>;
  return <div className="evidence-widget"><div className="tags"><Badge value={assessment.potential}/><Badge value={assessment.confidence}/></div>{assessment.claims.slice(0, 6).map(claim => <div className="claim" key={claim.id}><span className="eyebrow">{label(claim.topic)} · {label(claim.interpretation)}</span><p>{claim.text}</p>{claim.references.map((ref, i) => <EvidenceLink key={i} reference={ref}/>)}</div>)}</div>;
}
function Questions({ widgetId }: { widgetId: string }) {
  const [ctx] = useWidget(widgetId); const assessment = ctx.detail?.assessment?.data;
  if (!assessment) return <Empty title="What is still unknown?" text="Select an assessed lead to see unresolved questions. Missing information is never treated as a negative answer."/>;
  return <div className="question-list">{assessment.unknowns.map((item, i) => <p key={i}><span>?</span>{item}</p>)}{assessment.questions?.map((item, i) => <p key={`q${i}`}><span>?</span>{item.text}<small>Suggested question, not a source statement</small></p>)}</div>;
}
function RecentChanges({ widgetId }: { widgetId: string }) {
  const [ctx, widget] = useWidget(widgetId);
  if (!ctx.data.activity.length) return <Empty title="No changes yet" text="Human edits and concise agent decisions will appear here with their versions."/>;
  return <div className="changes-list">{ctx.data.activity.slice(0, widget.limit).map(change => <div key={change.id}><span className={`change-avatar ${change.actor}`}><Icon name={change.actor === 'agent' ? 'spark' : 'check'} size={14}/></span><p>{change.summary}<small>{label(change.actor)} · {date(change.created_at, ctx.bootstrap.timezone)}</small></p></div>)}</div>;
}
function Objections({ widgetId }: { widgetId: string }) {
  const [ctx] = useWidget(widgetId);
  if (!ctx.data.metrics.objections.length) return <Empty title="No supported objections yet" text="This summary only counts objection claims in persisted assessments."/>;
  return <div className="objections">{ctx.data.metrics.objections.map((item, index) => <p key={index}><span>{item.text}</span><strong>{item.count}</strong></p>)}</div>;
}
export const { registry } = defineRegistry(catalog, { components: {
  PriorityQueue: ({ props: p }) => <PriorityQueue {...p}/>, LeadsTable: ({ props: p }) => <LeadsTable {...p}/>,
  PipelineBoard: ({ props: p }) => <PipelineBoard {...p}/>, Commitments: ({ props: p }) => <Commitments {...p}/>,
  CallTimeline: ({ props: p }) => <CallTimeline {...p}/>, EvidencePanel: ({ props: p }) => <EvidencePanel {...p}/>,
  Questions: ({ props: p }) => <Questions {...p}/>, RecentChanges: ({ props: p }) => <RecentChanges {...p}/>,
  Objections: ({ props: p }) => <Objections {...p}/>,
} });
