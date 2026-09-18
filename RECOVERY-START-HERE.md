# Continue Relay SDR from the recovered implementation

This branch preserves the interrupted AI-managed leads workspace work. It is a **recovery checkpoint, not a completed or functionally verified feature release**. Do not merge this archival branch into `main` as an implementation.

Repository: https://github.com/krybaby7/Relay-sdr
Recovery branch: `recovery/ai-leads-workspace-2026-09-17`
Intended implementation branch: `feat/ai-leads-workspace` (inspect its current head before changing it).

## Fresh-chat instructions — no user upload required

Use the connected GitHub tools to read this file and the recovery files on **this branch**, not the default branch. Read the complete files; follow pagination when needed.

1. Inspect current repository branches and commits. Do not assume the historical commits below are still the latest.
2. Read `recovery/ai-leads-workspace-v2/RECOVERY.md`, `RESUME.md`, and `requirements/Relay_SDR_AI_Leads_Workspace_Implementation_Prompt.md` completely. The original implementation brief remains authoritative for product scope, architecture, security, tests, and delivery.
3. Inspect `recovery/ai-leads-workspace-v2/GITHUB-PRESERVATION.json` and run `python recovery/ai-leads-workspace-v2/verify_github_checkpoint.py`. That verifies the GitHub source checkpoint, not application behavior. The original `verify_checkpoint.py` expects three historical PNG screenshots that remain in the user's original Library archive and are not required to restore source.
4. Preserve the recovery directory unchanged. Work in a separate checkout/copy and reconcile `recovered-source/` with the current application. The 22 recovered source/configuration files are an initial overlay, **not** a standalone app or the exact last tested working tree. `Relay-sdr/` is historical baseline source; `recovered-dependency-manifests/` contains historical bootstrap/CI manifests, not guaranteed final application dependencies.
5. Continue restoration and implementation now. Do not restart from zero, replace useful recovered code with scaffolding, repeat brainstorming, or stop after a proposal. Reconstruct genuinely missing integration from the surviving source and full requirements; identify reconstructed portions honestly. Do not assume earlier chat execution records are available.

## Known missing work and unverified refinements

Read `RESUME.md` for the detailed list. Missing pieces include the workspace API router; configuration and worker lifecycle; integration with the legacy Store, main application, and live capture; frontend stylesheet; final package scripts; complete workspace/resilience/browser tests; built assets; and final documentation.

Verify or reconstruct the later fixes involving provider strict schemas, resumable transcript chunking, Store locking, transcript deduplication/revisions/finalization races, redaction/checkpoint cleanup, stale-result rejection, human-correction precedence, practice isolation, date/timezone ambiguity, scoped queries, layout locks/pins, optimistic concurrency, and stable focus/selection.

Historical screenshots, dependency audits, baseline test logs, and recovery syntax checks do not prove this reconstructed application works. Run baseline protections first, then the full applicable backend, migration, mocked-provider, resilience, typecheck, lint, production-build, and browser acceptance tests. Inspect actual desktop/mobile rendering. Clearly distinguish mocked checks from live-provider verification.

## Authority and boundaries

The user authorizes commits and pushes to a non-destructive feature branch and opening a pull request. Do not force-push over newer work, change the default branch, merge, deploy publicly, enable outbound calling, place real calls, contact leads, send messages, approve external webhooks, or change recording settings. Preserve authentication, consent, suppression, calling policy, provider callbacks, unknown-call handling, and practice isolation.

Keep call evidence, cumulative lead intelligence, and shared versioned workspace presentation separate. The orchestrator must actually apply validated persisted workspace changes through the same specification used by manual controls. Preserve the original brief's complete scope and three-agent permission boundaries. Do not invent records, metrics, consent, evidence, or transcript completeness.

Commit and push incremental source checkpoints before lengthy work can be lost again. Maintain `CONTINUATION.md` with the branch/commit, exact commands and results, remaining work, and next step. Exclude secrets, `.env`, `.data`, runtime databases, real transcripts, contact exports, and dependency caches. If a remote write actually fails, provide a usable local source archive/patch and the precise limitation. Work autonomously through ordinary implementation decisions and keep the user informed of meaningful progress.

## Historical anchors

On September 17, 2026, before publishing this recovery branch:
- `feat/ai-leads-workspace`: `19c4c091a98f55c63433d9bc405f5b1303191b28` (CI/toolchain work only).
- `main`: `22f69c92ecfe0c690362947351b3703913d7b379`.
- Archived baseline: `83f7c0cd641dc7e05dce98746de7a7c665b70957`.

The original ZIP and its three historical screenshots remain in the user's Library at `/Relay-SDR-Recovery/Relay-SDR-Recovery-Checkpoint-v2-2026-09-17.zip`. Restoring the implementation does not require the user to attach that ZIP again: the GitHub checkpoint supplies the recovered source and full brief directly. Do not require the screenshots before proceeding.
