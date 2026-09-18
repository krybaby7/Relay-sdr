# Relay SDR — implemented AI-managed leads workspace

Updated 2026-09-18. The implementation is on `feat/ai-leads-workspace-continue`.
The original interrupted-checkpoint failures have been resolved and the broader
manual/AI shared-workspace flow has been implemented and verified. This is a
single-operator local pilot, not a production calling release or live-provider
certification.

## Current native implementation

Read `README.md`, `docs/WORKSPACE-ARCHITECTURE.md`,
`docs/WORKSPACE-ACCEPTANCE.md` and `CONTINUATION.md`. Source is already at native
application paths, with compiled assets under `web/workspace/`. The complete
original scope and security requirements remain authoritative at:

`recovery/ai-leads-workspace-v2/requirements/Relay_SDR_AI_Leads_Workspace_Implementation_Prompt.md`

Do not reconstruct or reapply the older restoration overlays, `02-core-*.patch`,
`03-backend.patch`, or `restore_frontend_checkpoint.py`. Historical recovery
missing-work lists and their failed browser reports describe earlier versions,
not the current code. The original handoff is preserved in Git history at
`37d5c3a25c4173df8371cd11ba99a54325fad972`.

## Latest complete clean verification

Actual source tested: `de7c04b2ed0199f072e66ac14469f705210f0c95`.
Actions run: https://github.com/krybaby7/Relay-sdr/actions/runs/35326541860

- Recovery integrity passed; the original recovery directory is unchanged.
- Backend: **169 passed**, one upstream Starlette/AnyIO deprecation warning.
- Frontend typecheck, lint and production build passed.
- Shared keyboard/pointer geometry unit tests: **8 passed**.
- Desktop/mobile Chromium browser suite: **22 passed**, zero retries/skips.

The verified checkout was clean. Exact commands, source-file hashes, exit codes,
logs and actual fictional-data screenshots are committed under
`verification/acceptance-2026-09-18/`. Prefer the `*-rendered-overview.png`
screenshots, captured after explicit non-overlap and viewport-bound checks.
The previous 19/22 clean-run failure and its diagnostics remain in Git history
at `df36ce182c20873392a22e9a34560b8732defa0c`; tests were synchronized with real
UI readiness, not skipped or weakened. Later documentation/CI housekeeping
commits do not change the application source tested above.

Routine verification is `.github/workflows/workspace-ci.yml`, which uses the
committed dependency resolution and runs `scripts/verify_workspace.py`. It
builds native assets before browser tests. It does not run restoration scripts.

## Local operation and verification

Follow README for Python installation, private configuration and the workspace
token. Run `python run.py`, then open the printed loopback address and `/leads`.
Manual operation does not need a model key or Node development server. Optional
reasoning has an explicit independent server-side key/model and remains disabled
until configured. Keep outbound calling disabled.

For verification, install `requirements-dev.txt`, run `npm ci` in `frontend/`,
install Chromium with Playwright, then run:

```bash
python scripts/verify_workspace.py --output verification/local
```

All recorded verification uses mocked providers and fictional loopback fixtures.
Live model reasoning quality, live voice/PSTN, physical mobile devices,
Safari/Firefox, broad load tests, security/compliance certification, comprehensive
retention operations and multi-process use are not established.

## Non-destructive continuation boundaries

Inspect current remote branches/commits before any new work; all hashes above are
anchors, never reset targets. `main` was preserved at
`22f69c92ecfe0c690362947351b3703913d7b379`. Do not merge, force-push, deploy,
enable outbound calling, contact leads, send messages, approve external webhooks
or change recording settings without separate authorization.

Keep source evidence, cumulative lead intelligence and versioned presentation
separate. AI and manual operations share the same backend-validated specification.
Preserve the three-agent permission boundaries, authentication, consent,
suppression, provider contracts/callbacks, unknown-call handling and practice
isolation. Preserve `recovery/ai-leads-workspace-v2/` unchanged and exclude
credentials, `.env`, `.data`, runtime databases, real transcripts/contact exports
and dependency caches from source commits. No uploaded archive or previous chat
is required.
