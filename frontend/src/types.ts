export type Kind = 'PriorityQueue' | 'LeadsTable' | 'PipelineBoard' | 'Commitments' | 'CallTimeline' | 'EvidencePanel' | 'Questions' | 'RecentChanges' | 'Objections';
export type Breakpoint = 'lg' | 'md' | 'sm';
export type Mode = 'manual' | 'suggest' | 'adaptive';
export interface Filter { field: string; op: 'eq' | 'contains' | 'in' | 'unknown'; value: string | number | boolean | string[] | null }
export interface Query { scope: 'real' | 'practice'; search: string; filters: Filter[]; sort: 'name' | 'company' | 'potential' | 'priority' | 'stage' | 'created_at' | 'assessment_at'; direction: 'asc' | 'desc'; group: 'none' | 'potential' | 'priority' | 'stage' | 'eligibility' | 'company' }
export interface Column { field: string; width: number; visible: boolean }
export interface Widget { id: string; kind: Kind; title: string; binding: 'view' | 'selected_lead' | 'activity'; pinned: boolean; columns: Column[]; limit: number }
export interface Geometry { i: string; x: number; y: number; w: number; h: number }
export type Layouts = Record<Breakpoint, Geometry[]>;
export interface View { id: string; name: string; query: Query; widgets: string[]; layouts: Layouts; locked: boolean; origin: 'system' | 'human' | 'agent'; emphasis: 'overview' | 'pricing' | 'decision_process' | 'timing' | 'conflicts' }
export interface Spec { schema_version: 1; mode: Mode; default_view: string; allow_structural_auto: boolean; views: View[]; widgets: Record<string, Widget> }
export type Operation =
 | { op: 'edit_view'; view_id: string; name?: string; query?: Query; emphasis?: View['emphasis'] }
 | { op: 'create_view'; view_id: string; name: string; query: Query; duplicate_from: string }
 | { op: 'delete_view'; view_id: string }
 | { op: 'add_widget' | 'configure_widget'; view_id: string; widget: Widget }
 | { op: 'remove_widget'; view_id: string; widget_id: string }
 | { op: 'set_layout'; view_id: string; layouts: Layouts }
 | { op: 'pin_widget'; view_id: string; widget_id: string; pinned: boolean }
 | { op: 'lock_view'; view_id: string; locked: boolean }
 | { op: 'preferences'; mode: Mode; default_view: string; allow_structural_auto: boolean };
export interface Proposal { id: string; base_version: number; status: string; created_at: string; data: { reason: string; operations: Operation[] } }
export interface FieldDefinition { id: string; name: string; type: 'text' | 'number' | 'boolean' | 'date' | 'select'; options: string[] }
export interface Rubric { version: number; approved: boolean; description: string; criteria: Record<string, number> }
export interface Orchestrator { enabled_by_server: boolean; configured: boolean; paused: boolean; model: string; max_chunks_per_run: number; max_daily_requests: number; max_daily_reserved_tokens: number; running: boolean }
export interface Bootstrap { version: number; spec: Spec; fields: FieldDefinition[]; rubric: Rubric; orchestrator: Orchestrator; proposals: Proposal[]; cursor: number; timezone: string; fixture_mode?: boolean }
export interface LeadRow { id: string; name: string; company: string; potential: string; priority: string; confidence: string; eligibility: string; stage: string; assessment_at: string | null; next_action: string; analysis_status: string; needs_review: boolean; assessment_version: number | null; generation: number; assessed_generation: number; stale: boolean; [key: string]: unknown }
export interface RecordPage { items: LeadRow[]; total: number; page: number; page_size: number; has_more: boolean; scope: string }
export interface Metrics { total: number; promising: number; due: number; review: number; suppressed: number; unassessed: number; stages: { stage: string; count: number }[]; objections: { text: string; count: number }[]; scope: string }
export interface Reference { call_id?: string | null; segment_id?: string | null; note_id?: string; quote?: string; spans?: { segment_id: string; start: number; end: number }[]; source_time?: number | null; request_id?: string }
export interface Claim { id: string; topic: string; text: string; value: string; interpretation: string; references: Reference[]; call_id: string | null; source_revision: number }
export interface AssessmentData { playbook_approved?: boolean; human_facts?: { reference: Reference; topic: string; text: string; value: string }[]; potential: string; confidence: string; stage: string; evidence_points: number; points_label: string; assessed_at: string; criteria: Record<string, { value: string; source: string; claim_ids: string[]; human_note_id?: string | null }>; conflicts: { topic: string; reason: string; claim_ids: string[]; human_note_id?: string }[]; unknowns: string[]; claims: Claim[]; questions?: { text: string; status: string }[]; coverage: { total_chunks: number; processed_chunks: number; all_chunks_processed: boolean; transcript_certified_complete: boolean; capture_gaps?: { call_id: string; status: string; flags: string[] }[] }; objections: Claim[]; rubric_version: number; rubric_approved: boolean; needs_decision: boolean }
export interface Assessment { id: number; generation: number; created_at: string; model: string; rubric_version: number; prompt_version: string; data: AssessmentData }
export interface Task { id: string; lead_id: string; call_id: string | null; kind: string; party: string; status: string; due_at: string | null; created_at: string; version: number; name?: string; company?: string; eligibility?: string; data: { wording: string; reference: Reference | null; nature: string; date_phrase: string; date_resolution: string; source_active: boolean; execution: string } }
export interface CallRow { call_id: string; lead_id: string | null; kind: string; status: string; created_at: string; ended_at: string | null; segment_count: number; dropped: number; close_observed: boolean; name?: string; company?: string }
export interface Lead { id: string; name: string; company: string; phone: string; timezone: string; language: string; consent: boolean; consent_note: string; notes: string; sample: boolean; opted_out: boolean; status: string }
export interface Note { id: string; text: string; topic: string; value: string; confirmed: boolean; active: boolean; created_at: string; supersedes: string | null }
export interface Detail { lead: Lead; head: { generation: number; assessed_generation: number; status: string }; assessment: Assessment | null; notes: Note[]; tasks: Task[]; calls: CallRow[]; history: { id: number; created_at: string; potential: string; model: string }[]; eligibility: string; priority: string; priority_reason: string; stale: boolean; custom_values: Record<string, { version: number; value: string | boolean | number | null }> }
export interface Segment { page_offset?: number; id: string; call_id: string; seq: number; role: string; text: string; start_ms: number | null; end_ms: number | null; active: boolean; redacted: boolean; supersedes: string | null; received_at: string }
export interface Capture { revision: number; status: string; flags: string[]; dropped: number; complete: boolean; segment_count: number; audio_recorded: false; close_observed: boolean }
export interface CallDetail { call: { id: string; kind: string; lead_id: string | null; status: string; created_at: string; ended_at: string | null; summary: string; outcome: string | null; next_step: string; requests: { type: string; details: string; status: string }[]; provider_sid: string | null; session_id: string | null; error: string | null; usage: unknown; usage_finalized: boolean; lead_timezone?: string | null }; capture: Capture; segments: Segment[]; total_segments: number; offset: number; has_more: boolean; tool_results: { created_at: string; kind: string; summary: string; data: unknown }[] }
export interface Activity { id: number; created_at: string; actor: string; kind: string; subject: string | null; summary: string }
export interface Job { id: string; kind: string; lead_id: string | null; status: string; attempts: number; error: string | null; created_at: string; model: string; result: { workspace?: { status: string; reason?: string } } | null }
export interface Revision { version: number; actor: string; reason: string; created_at: string }
export interface Dataset { records: RecordPage; metrics: Metrics; tasks: { items: Task[]; total: number; has_more: boolean }; calls: { items: CallRow[]; has_more: boolean }; activity: Activity[] }
