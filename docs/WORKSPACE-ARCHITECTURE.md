# AI-managed leads workspace

Implementation: 18 September 2026. Single trusted local operator, one application process, SQLite. This is not a public deployment or a live-provider certification.

## Three layers and three agents

| Layer | Authority and storage | Not permitted |
| --- | --- | --- |
| Source evidence | Existing lead/call identity and provider lifecycle; `ws_segments`, capture revisions, normalized source spans, audit events | AI replacement of source transcripts, manufactured audio or timing |
| Lead intelligence | Versioned assessments, source-validated claims, confirmed notes, internal tasks, rubric and typed fields | Removing suppression, inventing permission, treating a request as a booking or recommendation as agreement |
| Presentation | One `Workspace` document, revision history, proposals and typed `ChangeSet` operations | Embedded records/totals, executable components, arbitrary JSON paths, SQL, URLs, permissions |

The live voice model remains `gpt-live-1`, with the separate existing in-call reasoning backend. The workspace worker has its own explicit `WORKSPACE_API_KEY` and `WORKSPACE_MODEL`, prompt, schema, context and permissions. It exposes **no dialing, messaging, booking, export, webhook-approval, network, filesystem or generic execution tools**. The voice contract and permission gates are not replaced by the workspace.

`app/db.py` updates scoped indexes/capture generations. `app/workspace/evidence.py` retains source identities/revisions and readable spans. `intelligence.py` validates references and computes reproducible classifications. `presentation.py` is the atomic publication boundary used by both manual and agent operations. `routes.py` authenticates all workspace reads/writes. `worker.py` runs the persistent graph outside the live-audio event loop.

## Evidence, capture and corrections

Streaming fragments keep stable segment IDs and source revisions. Duplicate events are deduplicated; late/revised fragments invalidate affected assessments. Logical source order is retained. Every significant extracted claim requires an exact source quote and validated lead/call/source association. Transcript text is untrusted data, never an operator command. Normalized turns preserve references to the captured fragments, not invented diarization.

A provider-completed callback alone does not certify completeness. Analysis waits for terminal lifecycle, bridge finalization and the configured quiet/settle interval. Unknown/in-progress calls hold analysis. Missing close events, restart interruption, missing timing, dropped content and legacy capture are labelled. Capture bounds are explicit: the implementation limits stored transcript content to 8 MB / 100,000 segments per call and reports dropped fragments rather than silently certifying completion. Long stored histories are processed in resumable bounded chunks; unavailable words/timing are not reconstructed.

Lead details retain all linked calls, operational status, requests, summaries, usage when provided, and paginated captured fragments. Evidence buttons resolve the exact call/segment or human note. Source correction creates an auditable revision. Redaction purges affected source revisions, copied tool text, extraction cache, derived assessment/task text and workflow checkpoints, then requires reassessment. It preserves internal task IDs/human terminal states. It does **not** promise to delete independent human notes, model-authored view labels, backups, external provider copies or filesystem remnants. Review those separately. Audio is not stored and provider recording settings are unchanged.

Practice/sample calls stay in a separate query scope and do not produce real assessments, follow-up tasks, suppression changes, outbox messages or commercial aggregates. Unlinked practice records remain accessible in the practice call history. Switching views clears selected evidence before another scope is displayed.

## Assessment and internal work

The persisted rubric uses versioned weights for need, approved fit, explicit intent and decision authority. Classifications are reproducible from supported criteria; they are **not probabilities of closing**. Uncalled/insufficiently supported leads remain unassessed, not low quality. Unknown budget/authority/timing remain unknown. Product qualification is gated on approved playbook context and rubric.

Potential, immediate priority, confidence/coverage and contact eligibility are separate fields. Priority considers due internal work and permission/suppression; a later commitment is not automatically urgent. Human-confirmed facts override later unreviewed inference; contradictory evidence is shown as conflict. Reanalysis preserves prior assessments and source freshness.

Commitments require exact agreement wording and a source. Proposed recommendations and requests are not completed work. Date resolution requires supported wording, call time and lead timezone; ambiguous phrases need review. Operators can clarify a due date and set internal task state with version checks. Saving a task never executes outreach.

## Durable workflow and failure semantics

The application starts one background worker with a database-backed queue and **LangGraph `StateGraph` + SQLite `SqliteSaver`**, not a volatile fire-and-forget task. Its phases are readiness, extract, reconcile, compute, internal work, plan, validate, commit and notify. Checkpoints use a JSON-only serializer, not pickle. Remote graph tracing is explicitly disabled.

Completed/revised real calls and relevant human edits advance a lead generation; commands get durable jobs. Dedupe includes generation, rubric, prompt/schema and model versions. Extraction caches include the actual source chunk, so changing chunk boundaries cannot reuse the wrong text. Restarted jobs resume checkpoints, but a changed model/prompt/schema supersedes unfinished work rather than attributing mixed output to an old configuration. Analysis is requeued; old operator commands require resubmission. A crash after commit does not duplicate tasks/assessments.

Model requests run outside the shared Store lock. Graph and commit stages verify source generation, rubric, presentation version and protected state. Stale evidence results are discarded; stale presentation patches cannot overwrite newer manual edits. SQLite publication validates the entire change set transactionally. An invalid second operation, invalid model response, unavailable key/model, timeout, rate limit or budget exhaustion leaves the last valid state intact. Failed jobs expose a sanitized status and bounded retries. Extraction continuation is not falsely reported as complete coverage. Assessment persistence can proceed when only optional presentation planning is unavailable.

No browser is needed while the server is running. Nothing processes when it is stopped. Only a single process/Uvicorn worker is supported; there is no Redis/Celery service or distributed deployment guarantee.

## Shared presentation and stability

`Workspace` supports eight initial transparent views: Today (due work), All leads (unfiltered real records), Highest potential (promising/strong), Follow-ups (has tasks), Needs qualification (unassessed), Needs review, Do not call (suppressed), plus a separately labelled Practice / demo view. Search can temporarily filter All leads; saving a restricted query creates a different view, so the underlying records remain accessible.

The closed catalog has PriorityQueue, LeadsTable, PipelineBoard, Commitments, CallTimeline, EvidencePanel, Questions, RecentChanges and Objections. Data comes from authenticated scoped queries/aggregates, not generated sample state. The renderer mounts `@json-render/react` components from a fixed `@json-render/core` catalog with only a widget ID. Arbitrary trees, actions, HTML and executable expressions are not accepted by the workspace schema. The adopted json-render package includes a sample-data prompt default; Relay never calls that generator. The independent workspace prompt and backend validators reject invented data.

`react-grid-layout` owns actual responsive pointer interaction; a small shared geometry helper resolves keyboard/pointer collisions without silently moving pins. Initial measured width selects the correct breakpoint (12/8/4 columns). All geometry is backend-validated, including membership, bounds and overlap. Keyboard operations can reorder/resize without dragging. Board-only views have their own record pagination. Columns have explicit order/width/visibility. Selected view, saved layouts, widget IDs and bindings survive reloads. Typed custom field definitions are separate from values; an empty field remains unknown.

Manual and AI edits use the same typed operations. Adaptive applies up to four routine operations; larger changes and structural changes normally become proposals. Manual and Suggest do not automatically publish agent presentation edits. At most three agent-created views are allowed, preventing endless duplicates. Pins protect widget configuration/membership/geometry against AI; locked views protect all their widgets. Undo, earlier-version restore and reset change presentation only. History is paginated.

Authenticated SSE carries only audit cursors, not secrets or unrestricted transcripts. The UI refreshes scoped data and stages material reordering while selecting, editing, dragging or reading a detail. Search/query state is retained through unrelated pin/configuration saves. Read-only 429 retries are narrowly allowlisted; mutations are never replayed automatically. An initial-load failure exposes retry/sign-in controls. Small-screen navigation retains all application sections and tab locking.

## Configuration and local storage

See `.env.example` for every setting and README for local setup. Defaults: workspace disabled; explicit empty key/model; UTC presentation zone; 1 s polling; 3 s settle; 24,000-character chunks; four new chunks per run; 45 s provider timeout; 6,000 output tokens; 100 requests and 1,500,000 conservatively reserved tokens per UTC day. Reservations are not a monetary budget or exact token count. Input JSON is bounded at 160,000 bytes; response bytes at 512,000. Do not use live-provider credentials in tests.

The worker calls the fixed xAI Responses endpoint (`https://api.x.ai/v1/responses`) with `store:false`, strict structured output and no execution tools. Default model is Grok 4.6. Provider policy still governs processing/retention. Reassessments may resend relevant prior real-call text and human notes. Layout planning uses bounded persisted assessments and current views rather than the full transcript database.

Back up **the entire data directory after a clean shutdown**, including the primary SQLite database, workspace checkpoint database, WAL files if present, and token. These files are sensitive and not encrypted by Relay. Do not share them with source archives. Additive versioned migrations preserve original IDs, phone identity, suppression, requests, outcomes and transcripts; an old six-table fixture and reruns are tested. Do not downgrade a migrated database in place; restore a protected pre-upgrade backup with the corresponding older code.

## Dependencies and official compatibility checks

Actual integrations: React 19.2.3, json-render core/react 0.20.0, react-grid-layout 2.2.4, LangGraph 1.2.11 and langgraph-checkpoint-sqlite 3.1.1. See [license notices](THIRD-PARTY.md), npm lockfile and Python constraints for exact resolution. AG-UI/CopilotKit are not installed: the tested authenticated cursor stream and the shared operation API cover this local single-operator scope without another conversational runtime. Puck, Tambo, OpenPage, Twenty, A2UI, DeepSeek Harness, Mastra, OpenHands and E2B are architectural inspiration only; no competing renderer or arbitrary code executor was introduced.

Official API documentation was rechecked on 18 September 2026:
- [GPT-Live guide](https://developers.openai.com/api/docs/guides/live) and [gpt-live-1 model](https://developers.openai.com/api/docs/models/gpt-live-1): separate voice and backend responsibilities; Live is not silently replaced with Realtime.
- [xAI Grok 4.6](https://docs.x.ai/developers/grok-4-6) and [structured outputs](https://docs.x.ai/developers/model-capabilities/text/structured-outputs): workspace reasoning uses the xAI Responses API, not OpenAI Responses; no calling tools.
- [LangGraph persistence](https://docs.langchain.com/oss/python/langgraph/persistence): thread checkpoints; installed SqliteSaver/StateGraph interfaces are exercised by restart tests.
- [json-render source](https://github.com/vercel-labs/json-render) and [react-grid-layout source](https://github.com/react-grid-layout/react-grid-layout): installed package APIs/license files and production build checked; real rendering and gestures tested.

These checks do not establish project access, live reasoning quality, live voice/PSTN compatibility, pricing, latency or safe public operation. See the acceptance report for executed checks and remaining verification boundaries.
