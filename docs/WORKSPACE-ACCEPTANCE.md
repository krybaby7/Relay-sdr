# Requirements coverage and verification boundaries

The full original brief remains under `recovery/ai-leads-workspace-v2/requirements/`. That directory is retained unchanged. The implementation extends the actual native application, not the historical recovered overlay. `CONTINUATION.md` records source anchors and milestone outcomes.

## Requirement audit

| Original scope | Implementation and exercised checks |
| --- | --- |
| Existing application and three-agent permissions | Existing voice/provider, consent, opt-out, authentication, unknown-call, practice and integration suites retained. Separate workspace model with no calling/export/booking tools. |
| Actual chosen libraries | Real json-render catalog/Renderer, react-grid-layout pointer controls, LangGraph persisted graph. Installed APIs inspected, build/typecheck and real browser rendering exercised. No second editor protocol. |
| Captured evidence | Stable fragments, source revisions/order, duplicates, late updates, explicit limits/completeness, exact spans, controlled correction/redaction. Tests include capture finalization races and unresolved provider state. |
| Cumulative intelligence | Evidence-backed real-call fixture, no-answer/uncalled handling, approved rubric, unknowns, confidence, potential/priority/eligibility separation, human precedence and contradictory evidence. |
| Internal work | Agreement-only ledger, conservative dates/timezones, task-state preservation, no automatic side effects; exact quote/source tests and ambiguous-date cases. |
| Shared versioned workspace | Same typed changes for human and agent, validated atomic transaction, three breakpoint layouts, pins/locks, proposals, stale-write rejection, no fabricated rows/totals or capabilities. |
| Working catalog and details | Saved views, search, filters/grouping, table columns, board-only pagination, commitments/calls, evidence/unknowns, objections and recent changes; source/navigation and paginated detail tests. |
| Broad customization | View create/rename/duplicate/emphasis, widget configuration/composition, pointer drag/resize, keyboard alternatives, typed fields, history/undo/reset. Desktop/mobile tests verify persisted native state, not only text changes. |
| Durable orchestration | Real SQLite queue and graph checkpoints; restart/after-commit recovery, dedupe, late revisions, slow-model lock isolation, source chunks, model/schema provenance and cache-boundary rollover tests. Browser-closed command scenario. |
| Autonomy and stability | Adaptive/Suggest/Manual, structural approval, pins/locks, limited auto-created views, staged busy updates, preserved query/selection/focus boundaries, exact version conflicts. |
| Security and truthfulness | Closed input/tool/spec schemas, quote/lead/call validation, forbidden-operation tests, SQL-like literal search, fake state rejection, authentication/origin gates, no recording changes. This is deterministic adversarial coverage, not a penetration-test certification. |
| Migration and operation | Six-table old-schema fixture, additive/rerunnable migrations, bounded dataset reads, separate scoped evidence endpoints, existing server serving compiled assets, explicit key/configuration and privacy documentation. |
| Delivery | Native source/tests, requirements/constraints/lockfile, configuration example, routine verifier/CI, license notices and committed results/screenshots. PR is opened without merge or deployment. |

## Executable checks

Run `python scripts/verify_workspace.py --output verification/local` after installing Python development requirements, `npm ci` and Chromium. The verifier records source SHA, modified-file hashes, commands, exit codes, timing and logs. Its stages are recovery integrity; the complete backend suite (including baseline protections); frontend typecheck; lint; geometry unit tests; production build; desktop/mobile Chromium acceptance. Browser tests always run against newly built native assets.

`frontend/e2e/fixtures.ts` starts a separate loopback-only application/database/worker per test with the real production rate limit and a fictional deterministic model. It has no reset/backdoor endpoint, real keys, live contacts, calls or external side effects. Model commands in that fixture are deliberately prescribed outputs; they test orchestration/persistence and do not score natural-language quality.

The expanded tests go past the original failure points: actual model-authored geometry at all breakpoints; keyboard reorder; desktop pointer drag/resize and mobile resize; manual pin/save/reload; subsequent agent changes preserving pins and widget identity; approvals/locks; table order/width/visibility; board-only pagination; undo/reset; failed initial read retry; model outage/manual operation; competing-edit atomic rejection; practice evidence clearing; and navigation/tab locking on small screens. The original eight scenarios remain enabled. Pure geometry tests validate collision resolution, pins, bounds and immutability separately.

The original three browser failures had distinct causes: dynamic counts changed accessible view names; the mobile Organize control lost its accessible text; the shared fixture exhausted the production request budget. Those were corrected in earlier native commits. Broader acceptance then caught real collision handling and initial-breakpoint bugs, which were corrected without relaxing server layout validation or skipping assertions.

## Explicit limits

No live OpenAI model, live GPT-Live audio, Twilio PSTN/media handshake, webhook delivery, real contact data, recording change or public deployment was used. Chromium desktop and emulated small-screen Chromium are tested; physical mobile devices, Safari/Firefox, screen-reader certification, broad load tests, penetration testing, legal compliance and multi-process operation are not established. Layout composition is broad within the supported catalog, not arbitrary executable UI generation. Long or gapped captures are labelled rather than represented as complete conversations.

Final exact results and screenshots are stored under `verification/acceptance-2026-09-18/`; historical results are not substituted for a fresh run. Failed exploratory runs remain described in `CONTINUATION.md`, and only completed checks are reported as passing.
