# Continue Relay SDR from the rescued work, not from zero

## Task

Restore and finish the AI-managed leads workspace described in `requirements/Relay_SDR_AI_Leads_Workspace_Implementation_Prompt.md`. That brief remains authoritative. The user authorized a feature branch and PR, not a merge, deployment, or real outbound calls.

## First preserve and inspect

1. Run `python verify_checkpoint.py` from the extracted checkpoint root. Keep this checkpoint unchanged; work in a separate copy.
2. Inspect the current GitHub repository with connected GitHub tools. The last inspected feature head was `19c4c091a98f55c63433d9bc405f5b1303191b28` and contained CI work only. Do not infer the remote is still identical or overwrite later human work.
3. `Relay-sdr/` is the baseline. `recovered-source/` is an overlay of actual rescued INITIAL source, not a standalone app and not the exact last tested tree.
4. Build a clean working branch and reconcile the overlay. Preserve original IDs, suppression, consent, call/provider contracts, and practice isolation. Never enable calling as part of restoration.

## Source already rescued

Backend directory `recovered-source/app/workspace/` has `schema.py`, `migrations.py`, `evidence.py`, `intelligence.py`, `queries.py`, `presentation.py`, `model.py`, `worker.py`, and `__init__.py`.

Frontend has actual `App.tsx`, `catalog.tsx`, `editors.tsx`, `details.tsx`, `types.ts`, `api.ts`, `ui.tsx`, `main.tsx`, and Vite/TypeScript/lint/index configuration. Initial source-writing record byte sizes for App.tsx (37,036), editors.tsx (18,309), and details.tsx (19,605) matched the restored files. This size agreement is not a cryptographic assertion that all later edits were restored.

`tests/workspace_fixtures.py` is recovered. Existing baseline tests remain under the baseline tree.

## Missing integration and files

- Workspace API router, enable/disable/config settings, worker lifecycle startup and shutdown.
- Integration changes to `app/db.py`, `app/main.py`, `app/config.py`, `app/live.py`, and appropriate models/routes, including lazy transcript loading and explicit capture readiness.
- Original `patch_store.py` source-integration script was visible in prior execution records but is not included in this checkpoint. It adjusted Store initialization/migrations, indexed transcript hydration, protected real transcript replacement, source revision hooks, tool-result auditing, capture lifecycle hooks, and lighter `/api/state` responses. Recover/read before attempting equivalent changes; do not apply old absolute-path scripts blindly.
- Frontend stylesheet; original complete workspace backend/resilience tests and Playwright tests/config; final package scripts and runtime pin set; compiled frontend assets and final documentation.

If continuing in the same chat and the earlier execution records remain accessible, prefer recovering actual source-writing commands over reconstructing from screenshots. Long source-display outputs were sometimes already truncated; those must not be treated as complete files. Original source-creation commands were generally complete. Recover actual code where possible before writing replacements, and label any newly reconstructed code honestly.

## Known later refinements that are NOT guaranteed replayed

These were present in the earlier execution record/history and require recovery or careful reimplementation and testing; this list is a continuation aid, not a claim that the recovered snapshot already has the fixes.

- Provider strict schema conversion (`oneOf`/discriminator/default/const handling) and model-response validation.
- Long-transcript chunk continuation and checkpoint recovery instead of ending with an unrecoverable partial analysis.
- Transaction boundaries and lock handling, especially not holding the shared Store lock across slow model awaits; immediate opt-out must not wait for analysis.
- Transcript source revision/event deduplication, source ordering and timing validation, explicit finalization races, redaction and checkpoint-data purge, stale source/assessment invalidation.
- Practice call timeline linkage without contaminating real assessments or aggregates; terminal/unknown-call reconciliation safeguards.
- Legacy human-note import and confirmed corrections retaining precedence through new contradictory evidence.
- Pagination and scoped call/segment access with correct lead, call, source revision, and bounded query validation.
- Human-local timezone handling for priority and due dates; ambiguity must not become an invented commitment.
- Locked/pinned view protection, optimistic concurrency, conflicting changes, and further adaptive-layout limits.
- Responsive canvas geometry, keyboard alternatives, stable selection, scroll/focus, and staged updates while editing or reading details.

## Verification still required

Restore and run the baseline protections first. Then run complete backend, deterministic provider, resilience, migration, frontend typecheck/lint/build, and browser suites against the integrated current tree. Inspect the actual desktop/mobile rendering again. Past test output does not validate this reconstruction.

The last original execution appended additional resilience tests and attempted pytest, but there was no returned completion result before interruption. Do not invent that result. No live model/provider verification is established by this checkpoint.

## Recovery integrity vs product verification

`verify_checkpoint.py` uses only Python's standard library to check SHA-256 hashes and Python syntax. It does not import application code, start a server, contact any provider, test migrations, or place calls. `RECOVERY-VERIFICATION.json` records exactly the recovery checks performed.

## Delivery discipline

Commit incremental, honestly labeled work to the feature branch after review, rather than letting the only copy live in a temporary session. Maintain source checkpoints plus concise continuation notes throughout. Do not commit `.env`, credentials, runtime databases, `.data`, real transcripts, contact exports, or test dependency caches. Open a PR only with an accurate verification status; do not merge or deploy automatically.
