# Implement Relay SDR's AI-Managed Leads Workspace

## 1. Your task and authority

Implement a substantial redesign of the leads experience in this repository:

https://github.com/krybaby7/Relay-sdr

Do not merely produce a proposal, architecture document, mockup, or tutorial. Inspect the actual repository, implement the working feature, test it, and provide the resulting code and verification report.

Work on a feature branch such as `feat/ai-leads-workspace`. You are authorized to commit and push the implementation to that branch and open a pull request against the repository's default branch. Do not automatically merge it, deploy a public service, place real telephone calls, contact leads, or enable outbound calling.

Use the connected GitHub tools to inspect the repository before drawing conclusions about its current state. Work autonomously through ordinary implementation decisions. Ask only for essential access or authorization that cannot be resolved through available read-only tools. Do not stop at scaffolding or replace implementation with another round of brainstorming.

If repository writes or execution capabilities are unavailable after an actual attempt, explain the precise limitation and complete the usable local implementation, patch, source package, and tests that the available environment permits. Never claim a commit, push, test, integration, or deployment succeeded without evidence.

## 2. Product vision

Replace the conventional leads table with a persistent, AI-managed sales workspace.

The workspace must preserve the details captured from every call, maintain an evidence-backed understanding of each lead across calls, organize leads by potential and priority, and make the most useful information visible through a highly customizable interface.

A separate AI workspace orchestrator—not the live voice agent—must understand transcripts, reconcile them with lead history, maintain assessments and follow-up work, create useful views, and rearrange the workspace.

This must be a genuine working capability. A static dashboard plus a chatbot describing hypothetical changes is not sufficient. The orchestrator's changes must affect the actual interface and survive reloads and server restarts.

Users must also be able to edit the same workspace manually. AI and manual editing must share one authoritative workspace specification, not two incompatible page formats.

The organizing principle is:

**The AI maintains an evidence-backed understanding of the pipeline, and controls how that understanding is presented. It does not invent records, silently rewrite source evidence, or grant itself permissions.**

## 3. Existing application: inspect, preserve, extend

The previous inspection was of commit `22f69c92ecfe0c690362947351b3703913d7b379`. Treat this as historical context, not proof of the current HEAD.

At that inspection, Relay used a Python/FastAPI backend, SQLite persistence, and plain HTML/CSS/JavaScript. Relevant files included `app/db.py`, `app/models.py`, `app/live.py`, `app/main.py`, `app/policy.py`, `app/telephony.py`, and `web/app.js`.

It already had lead intake and editing, CSV import, consent assertions, permanent do-not-call suppression, browser practice, a GPT-Live voice bridge, a separate in-call reasoning backend, a Twilio adapter, call records, transcript fragments, summaries, outcomes, meeting/human-callback requests, and approved outbound webhook delivery.

Preserve these working paths and their protections. In particular:

- Keep the voice agent, in-call reasoning backend, and new workspace orchestrator separate in responsibility and permissions. Workspace analysis must not block live audio or immediate opt-out handling.
- Preserve real-call confirmation, consent and suppression checks, calling windows, allowlists, limits, idempotency, signed callbacks, authentication, and unknown-call reconciliation behavior.
- Browser practice and fictional samples must not contaminate real lead intelligence, trigger real follow-ups, change real contact eligibility, or appear in real sales metrics.
- Meeting requests remain requests until an actual authorized booking is confirmed. Human-callback requests are not live transfers. Proposed or drafted work is not completed work.

The prior transcript writer stored streaming fragments and silently stopped accepting entries at a limit of 12,000. Inspect the current behavior and replace silent incompleteness with an explicit, tested capture/completeness policy. Do not infer a complete transcript merely because a call ended.

The previous version did not persist audio recordings. Preserve that default. Do not add recording or change provider recording settings under this task. “All call details” means all available captured information, with gaps honestly labeled—not fictional audio playback or invented timestamps.

Read existing documentation and tests, establish a baseline, and inspect the actual voice/provider contracts before modifying integration-sensitive code. Verify model identifiers and APIs against current official provider documentation; do not guess or silently substitute a different voice API.

## 4. Chosen architecture and open-source references

Implement the dashboard-first direction below. Verify the APIs and licenses of the exact dependency versions you adopt, pin compatible versions, and avoid unnecessary framework accumulation.

**Preferred implementation:**

- React + TypeScript for the new leads workspace, integrated with the existing application.
- `vercel-labs/json-render` for the typed component catalog and declarative runtime rendering.
- `react-grid-layout/react-grid-layout` for draggable, resizable, responsive dashboard geometry.
- Python LangGraph for the workspace orchestrator's resumable, stateful workflow, with persistent storage rather than an in-memory-only checkpointer.
- AG-UI/CopilotKit where its conversational controls and agent/UI events materially help. It is not the CRM database or the durable job queue. A simpler authenticated streaming connection is acceptable when justified by the tested integration, without sacrificing actual agent control.

References:

https://github.com/vercel-labs/json-render
https://github.com/react-grid-layout/react-grid-layout
https://github.com/langchain-ai/langgraph
https://github.com/ag-ui-protocol/ag-ui
https://github.com/CopilotKit/CopilotKit

Use focused manual customization controls around the same workspace document. Do not install a second page engine merely to obtain an editor.

**Other projects previously considered:**

https://github.com/puckeditor/puck — Alternative visual-editor foundation, not automatically compatible with json-render's document format. Do not introduce competing sources of truth or assume hosted AI features are included in the editor package.

https://github.com/tambo-ai/tambo — Inspiration for existing components that both users and agents can manipulate. A credible alternative stack, not an automatic additional dependency.

https://github.com/buildingopen/openpage — Borrow the shared JSON-document approach to AI and manual editing, not its marketing-site generator or sample-content assumptions.

https://github.com/twentyhq/twenty — Product inspiration for separating records, saved views, and configurable record pages. Do not copy code without checking the applicable license.

https://github.com/a2ui-project/a2ui — Declarative-interface and trust-boundary inspiration; no second UI protocol is required for this release.

https://github.com/deepseek-ai/deepseek-harness — Borrow explicit, replaceable capability boundaries, not a general code-executing runtime.

https://github.com/mastra-ai/mastra — TypeScript orchestration alternative; do not run it alongside LangGraph for the same workflow.

https://github.com/OpenHands/OpenHands
https://github.com/e2b-dev/E2B — Engineering experimentation references only, never the default runtime for processing leads or rearranging the page.

Do not repeat an exhaustive comparison. Perform targeted compatibility checks, then implement. If a preferred dependency genuinely cannot satisfy a requirement, document the concrete finding and use the smallest justified alternative. Do not silently deliver a hardcoded imitation while claiming integration with the selected libraries.

## 5. Keep three authoritative data layers separate

### A. Call evidence

Preserve call identity, linked lead, call type, lifecycle/provider status, available start/end information, transcript capture, available speaker/timing information, outcomes, requests, tool/action results, errors, and available usage metadata.

Retain source transcript segments with stable identifiers. Build normalized readable turns without destroying the captured source. Handle duplicate, late, partial, or revised events. Mark missing timing, interruption, truncation, or incomplete capture explicitly. Do not invent diarization, audio offsets, or transcription confidence.

Make corrections and redactions explicit and auditable. Do not promise eternal immutable storage where controlled deletion/redaction may be necessary; do prevent the model from silently replacing evidence with its interpretation.

### B. Lead intelligence

Maintain a cumulative assessment across relevant real calls and human notes. Include needs, product fit, buying signals, objections, decision process, timing, commitments, unresolved questions, next recommended actions, stage, and assessment freshness where supported.

Keep these distinct:

- **Potential:** How promising the opportunity appears based on the approved sales criteria and known evidence.
- **Priority:** How important a specific action is now, considering commitments, due dates, blockers, and eligibility.
- **Confidence/coverage:** How well-supported the assessment is and what remains unknown.
- **Contact eligibility:** Backend-enforced permission and suppression state, separate from commercial attractiveness.

An uncalled or insufficiently understood lead is unassessed, not automatically low quality. Unknown budget is not zero budget. Politeness is not buying intent. A high-potential lead who requested a later follow-up need not be immediately actionable.

Use understandable categories and a transparent, versioned rubric. The model can extract evidence and interpret it; final ranking must be reproducible from persisted assessments and rubric rules. Do not present an arbitrary score as a calibrated probability of closing.

Important claims require source references: call ID, segment ID, supported quote/span, source time when known, interpretation status, and assessment version. Validate references against stored evidence. Label unsupported inferences and uncertainty rather than generating fake citations.

Preserve conflicting facts, previous assessments, and human corrections. User-confirmed corrections take precedence over later unreviewed AI inference; new contradictory evidence should surface a conflict rather than silently undo the correction.

### C. Workspace presentation

Persist one versioned specification defining components, stable widget IDs, supported properties, layouts per breakpoint, saved views, filters, sorting/grouping, column settings, authorized data bindings, pins/locks, and presentation preferences.

Both the agent and manual controls update this specification through the same validated operations.

Keep live records and computed metrics out of model-authored layout data. Prefer references to authorized queries, views, and backend aggregates. The model chooses what to display; the backend supplies the actual data.

Do not put transcripts, CRM records, access permissions, and widget geometry into a single unrestricted model-editable object.

## 6. Build a real leads experience

Provide a polished, usable workspace consistent with Relay's visual identity—not a library demo or a page filled with placeholders.

Include a command area for natural-language instructions, a concise evidence-backed overview, saved-view navigation, a responsive customizable canvas, and a lead-detail drawer or page. Preserve reliable navigation to all records and existing application sections.

Initial useful views should cover Today, All leads, Highest potential, Follow-ups, Needs qualification, Needs review, and Do not call. Define each view transparently; missing information or AI failure must not make a lead disappear from the underlying records.

Implement a coherent catalog of working widgets, including a priority queue, configurable leads table, pipeline board, commitments/follow-up list, call timeline, evidence/assessment panel, unresolved-questions panel, and recent-changes summary. Add objection or pipeline aggregates when supported by real data. Do not include decorative chart widgets that lack a real data path.

Lead details must expose the assessment and its reasons, potential versus priority, eligibility, important unknowns, commitments and task states, all linked calls, per-call summaries, source transcripts, requests/outcomes, and available operational details. A click on supporting evidence should navigate to the relevant captured segment.

A commitments ledger must distinguish what each party actually agreed to do from what the AI merely recommends. Preserve the original wording and supporting evidence. Resolve dates only when the call time and relevant timezone support it; ambiguous dates require clarification/review. A saved follow-up task never places a call or sends a message by itself.

Support searching and filtering without forcing users through chat. Surface loading, empty, failed-analysis, partial-transcript, stale-assessment, and unavailable-model states honestly. Keep separately labeled demo/practice views available without fabricating real pipeline activity.

## 7. Make customization broad and genuinely shared

Users and the orchestrator must be able to create/rename/duplicate views, choose supported widgets, add/remove/reorder/resize them, configure filters and grouping, choose table columns and their order/width/visibility, and save layouts across reloads.

Support typed custom lead fields through a controlled field-definition mechanism with stable IDs and validated values, rather than arbitrary runtime database changes. Distinguish creating a field from knowing its value. Do not let derived AI fields replace protected identity, eligibility, or policy fields.

Allow different detail-page emphasis for different situations: pricing objections, decision-process gaps, timing constraints, or contradictory information. Preserve stable access to full evidence and all calls regardless of which sections are emphasized.

Provide keyboard-accessible alternatives to drag operations, readable small-screen layouts, sensible widget size constraints, and consistent typography, spacing, loading, and focus behavior.

“Fully customizable” means broad composition and configuration of the supported component/data vocabulary. Creating a fundamentally new executable component remains a development operation; never execute arbitrary model-generated JavaScript, JSX, HTML scripts, SQL, or shell commands in the live workspace.

## 8. Implement the orchestrator, not just its interface

Use a separate server-side model configuration for workspace reasoning. It may share a provider or model family with the in-call backend, but must have separate prompts, context boundaries, tools, and permissions. Verify current official APIs and use schema-constrained responses where supported, followed by application validation.

Implement persistent work triggered by completed calls with finalized or explicitly incomplete capture, revised transcripts, relevant human corrections, and user workspace commands. Respect actual lifecycle/finalization races rather than assuming the first provider-completed event means all transcript data has arrived.

A suitable workflow is:

`Capture readiness → Extract supported facts → Reconcile lead history → Compute assessment/ranking → Create internal work → Plan view/layout changes → Validate → Commit versioned changes → Notify UI`

Keep all work off the live-audio path. Processing must continue while Relay's server is running even when the browser is closed. Do not imply work runs when the server is stopped.

Use a durable application job queue and persistent workflow checkpoints. Recover interrupted jobs on restart. Deduplicate repeated triggers using call/source revision and analysis/rubric versions. Prevent stale results from overwriting newer evidence or manual changes. Store run status, failures, retry state, and the model/prompt/schema versions used.

Stay compatible with Relay's supported single-process deployment unless deliberately implementing and testing a broader model. A database-backed worker inside that process is acceptable; volatile fire-and-forget tasks alone are not. Do not add Redis, Celery, a second agent service, or a new production database without a concrete need.

Analyze the affected lead and relevant history first. Workspace planning should use persisted assessments and targeted queries, not resend every transcript after every call. Use bounded input/output, concurrency, timeouts, retries, and cost controls. Long transcripts must receive explicit chunking/coverage handling, not silent truncation.

Calls with no usable conversation still retain their operational records; do not manufacture qualification assessments for unanswered calls or missing transcripts.

Implement natural-language commands that change the real workspace, for example:

- “Show leads awaiting a proposal, grouped by priority.”
- “Move callbacks due today to the top and pin the call history.”
- “Create a view of promising leads blocked by procurement.”
- “I have twenty minutes. Show where a decision from me would unblock progress.”

These should produce validated actions and actual saved changes, not merely prose or temporary chat cards.

When the model is unavailable, the workspace must remain usable manually and preserve the last valid state. Show a clear setup/error state. Never disguise hardcoded demonstration responses as live orchestration.

## 9. Autonomy, stability, and reversibility

Provide Manual, Suggest, and Adaptive organization modes. Adaptive should be the initial intended experience: routine, reversible internal organization can apply automatically without approval for every small change.

The orchestrator may create useful views, update rankings and summaries, and rearrange unlocked widgets within its allowed scope. Expose a concise reason and supporting evidence for significant changes. Offer previews/approval for larger structural changes according to the selected mode and user settings.

Users can pin widgets, lock views/layout regions, correct assessments, undo changes, restore earlier versions, and reset the layout without deleting lead records.

Do not reshuffle rows or move controls while the user is editing, selecting, dragging, or reading an active detail view. Preserve selection, scroll, and focus; stage material reordering until an appropriate idle/apply point. Use sensible limits to prevent endless near-duplicate auto-created views.

Use optimistic concurrency or equivalent version checks for both AI and manual changes. A stale layout patch must be rejected or safely reconciled, not overwrite the latest human edit. Validate an entire change set before publication; a failed or partial generation must leave the last valid workspace intact.

## 10. Security and data truthfulness

Treat transcripts, lead notes, imported values, and external content as untrusted data. Instructions spoken by a lead are never operator instructions for changing permissions, contacting others, exporting data, or manipulating the UI.

Expose narrow, typed application tools for reading authorized records, submitting evidence-backed assessments, managing internal tasks, and modifying views/widgets. Enforce permissions and protected-field rules on the backend, not only in model prompts or frontend buttons.

The orchestrator must not remove suppression, invent consent, alter calling policy, change provider destinations, send messages, book meetings, dial leads, or approve external webhooks as a consequence of reorganizing the page. Existing authorized actions must retain their original server-side gates.

A crucial implementation check: previously inspected json-render prompt defaults encouraged realistic sample data. Inspect the adopted version and replace incompatible defaults. Production components must reject invented record collections or arbitrary model-provided business totals. Empty means empty; unknown means unknown; all aggregates come from authorized backend data.

Restrict component types, properties, data bindings, query operators, action names, layout paths, tree depth/size, and protected state. Verify every referenced widget/element exists, prevent invalid/cyclic component trees, and constrain expensive queries. Do not expose a generic database, network, or filesystem tool.

Keep keys and credentials server-side. Do not stream secrets or unrestricted transcripts through shared UI state or logs. Escape/sanitize displayed text and preserve appropriate authentication, origin checks, and content-security protections. Record concise decision rationales and audit events, not hidden model reasoning.

## 11. Integration, migrations, and local operation

Add backward-compatible, versioned migrations for existing workspaces. Preserve lead IDs, phone identity and suppression relationships, call IDs, source transcripts, saved outcomes, requests, and existing integration behavior. Test migration from an actual old-schema fixture and rerunning migrations safely.

Introduce indexed storage for jobs, analysis/evidence, tasks/commitments, rubric/field definitions, workspace/view revisions, and audit records as appropriate. SQLite may remain the supported database if the implemented access pattern is sound.

Do not overload `/api/state` with every full transcript or repeatedly load the entire database to render a view. Add scoped, validated, paginated query/detail endpoints and fetch evidence on demand.

Mount the React leads workspace cleanly within the existing application; avoid duplicate navigation or conflicts with legacy JavaScript. Keep unrelated pages functioning. Provide a documented frontend build and serve the compiled assets through the existing local backend so normal use does not require separate development servers.

Add a server-side orchestrator model setting, enable/disable controls, and bounded run settings using the existing configuration conventions. Do not silently enable real outbound calling or copy credentials into browser code. Document any new external data processing and local storage/backup implications without claiming compliance certification.

## 12. Required tests and acceptance criteria

Run existing tests first and retain their protections. Add meaningful unit, integration, and browser tests; separate deterministic mocked-provider checks from any real-model checks. Do not place real calls or use real lead data for testing.

Cover at least:

1. Migration preserves existing leads, call evidence, requests, suppression, and practice isolation.
2. A simulated completed real-call fixture creates an evidence-backed assessment and internal follow-up work; an unanswered or evidence-free call does not invent qualification.
3. Duplicate completion events, retries, late transcript changes, stale jobs, and server restarts do not duplicate tasks or overwrite newer corrections.
4. Potential, immediate priority, confidence, and eligibility remain separate. Unknown values and ambiguous dates remain explicit.
5. Evidence links resolve to the correct lead/call/segment; conflicting information and human overrides remain visible.
6. Prompt injection in transcripts cannot alter protected state, invoke arbitrary tools, or bypass dialing/export gates.
7. Empty datasets remain empty, fake metrics/records are rejected, and invalid component specifications fail safely.
8. AI layout edit → manual resize/pin → save/reload → further AI edit preserves IDs, bindings, user locks, and persistent changes.
9. Competing edits, invalid patches, invalid element references, and model failures leave the last valid workspace intact.
10. Background processing works without an open browser while the server runs; interruption and retry behavior are tested.
11. Search, table controls, saved views, board, details, transcript navigation, undo/reset, responsive layouts, and keyboard alternatives work in browser tests.
12. Existing voice, Twilio, authentication, consent, opt-out, unknown-call handling, practice isolation, and integration tests remain valid.

Run type checks, linting, production frontend build, backend tests, and available browser checks. Inspect the actual rendered desktop and smaller-screen interface and fix visual or interaction failures. Record exact commands and results. If a live model or provider path was not exercised, state that explicitly; mocked success is not live verification.

## 13. Delivery

Deliver the working implementation, not only plans. Include source, migrations, pinned dependencies/lockfiles, configuration examples, runnable instructions, deterministic fixtures/tests, architecture notes, and a concise verification report with known limitations.

Update the README for setup, building, model configuration, autonomy modes, evidence handling, limitations, and the continued calling/authorization boundaries. Document which libraries were actually integrated and which were only inspiration, with relevant license notices for reused code.

Commit and push the feature branch and open a pull request when the authorized tools support it. Keep the default branch unchanged. Never commit `.env`, credentials, `.data`, real transcripts, contact exports, or user runtime databases. Provide a source archive or patch as an additional handoff when practical, and as the fallback if GitHub writes fail.

Your final response should identify what was implemented, how to run it, branch/commit/PR or downloadable artifacts, what was actually tested, and what remains unverified. Show actual UI screenshots when available. Do not label unfinished features complete or call the app production-ready without the corresponding evidence.

Start by inspecting the current repository and baseline tests, perform the targeted library integration checks, then implement through testing and packaging. Keep me informed of meaningful progress, but do not stop after the plan or require approval for every ordinary engineering choice.
