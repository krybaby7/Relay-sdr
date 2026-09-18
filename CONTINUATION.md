# AI leads workspace continuation — 2026-09-18

Branch: `feat/ai-leads-workspace-continue`. Recovery anchor: `c0c35ddfb9d23596d492a41a18c79587b1b031b0`, including feature head `19c4c091a98f55c63433d9bc405f5b1303191b28`. Main remains unchanged at `22f69c92ecfe0c690362947351b3703913d7b379`.

## Milestone 1: native recovery restored

Read the complete handoff, preservation metadata, RESUME, RECOVERY and original implementation brief. Inspected current branches and ancestry. Restored all 22 recovered files byte-for-byte to application paths, preserving the entire recovery directory unchanged. These are INITIAL versions, not a verified integrated release.

A fresh native GitHub checkout was verified in Actions run 35275591238 at commit 4ff7a632c445d6b342eaf2d08eec4cc1c0aec68e. Direct git DNS is unavailable in the editing container; a newly generated native-source/toolchain snapshot from that run enables local execution. No historical expiring artifact or encoded transport was used.

## Actual tests

- `python recovery/ai-leads-workspace-v2/verify_github_checkpoint.py`: passed in fresh Actions and local checkout. 66 payload hashes / 67 text files including manifest, 26 Python syntax checks. Integrity only.
- `python -m pytest tests -q`: 87 passed, one Starlette/AnyIO deprecation warning, Actions 1.36s; local 1.08s. Baseline before integration, not feature tests.
- No live provider/model calls. No real calls, lead contact, deployment, or outbound enablement.

## Next milestone

Reconstruct missing workspace router, Store/config/live lifecycle hooks, frontend styling and packaging; test the integrated app. Repair source revisions/finalization, resumable chunks, strict provider schema, human correction precedence, lock/pin/concurrency protection and bounded scoped queries. Add deterministic resilience and browser acceptance tests. Push source and exact test results incrementally.

## Boundaries

No changes to main or recovery, no force push, merge, deployment, outbound enablement, recording changes, real data or secrets. Preserve authentication, consent, suppression, calling policy, signed callbacks, unknown-call reconciliation and practice isolation. Continue autonomously through implementation and verification.

## Milestone 2: backend integration (local checks complete; browser work pending)

Implemented indexed Store capture and lazy transcript loading; nested-savepoint atomicity; separate workspace configuration; worker lifecycle; authenticated bounded APIs; source correction/redaction; protected revision ordering; resumed chunk extraction; strict provider-schema translation; practice-call timeline isolation; and the /leads application route. Voice provider event/tool contracts are retained.

Actual local results after integration:
- `python -m pytest tests -q`: 87 passed, one Starlette/AnyIO deprecation warning (5.07s). These are the existing regression tests, not the planned workspace acceptance suite.
- `python -m compileall -q app`: passed.
- Deterministic FixtureModel worker smoke: one durable assessment, two mocked model requests, succeeded job.
- Authenticated HTTP smoke: bootstrap, query, aggregates, tasks, calls, lead detail and call detail returned 200; audited correction and redaction returned 200. No external model or provider calls.

The reconstructed feature is NOT release-verified. Next: frontend style/package/build, full backend resilience and security tests, desktop/mobile browser verification, documentation and PR. Source is preserved through an ordinary UTF-8 reviewed git patch applied to the continuation branch by a branch-restricted workflow; the resulting files are native repository source, and no historical recovery transport is used. No force push or main/recovery changes.

Fresh isolated verification: `python -m compileall -q app` and `python -m pytest tests -q` passed in Actions run 35278025146, on the exact reconstructed source blobs verified above. This is regression verification, not full workspace or browser acceptance.

## Milestone 3: reconciliation hardening

Exact-source backend fixes verified in Actions run 35280381231. Human precedence now applies to procurement, proposal, budget and other supported facts; approved playbook gates fit; practice redaction does not erase real intelligence; provider reads are bounded; terminal capture and generation checks reject stale results; paginated scoped history and note-source APIs are connected.

Local acceptance run before this checkpoint: 155 tests passed (87 baseline + 68 workspace cases), one upstream Starlette/AnyIO deprecation warning. Frontend type-check/lint/build passed; first two Chromium desktop/mobile source-navigation tests passed after fixing initial grid measurement. Expanded browser tests and final frontend publication remain in progress. No live model/provider calls, deployment or lead contact. Recovery remains unchanged.

## Preservation milestone: interrupted frontend and tests

On 2026-09-18, the user requested a durable checkpoint and fresh-chat prompt. Recovered the missing stylesheet, 68-case backend suite, browser fixture, expanded eight-case browser suite and frontend package scripts. Restored five native frontend files using guarded transformations recovered from the interrupted execution record. The original working tree and lockfile did not survive; this is a reconstructed checkpoint, not a byte-identical filesystem recovery or completed release. See `continuation/PRESERVED-FRONTEND.json` for source hashes and replacement counts.

This source checkpoint was published before new verification in Actions run 35285742889. The original recovery directory remains unchanged. Do not reapply the already-applied restoration script or prior backend patches. Fresh verification will be recorded separately; historical test passes do not validate this reconstructed tree.

## Fresh preservation verification
Actions run 35285742889. Native results: `verification/preservation-2026-09-18/RESULTS.json` and sibling logs.
- recovery-integrity: exit 0
- backend: exit 0
- typecheck: exit 0
- lint: exit 0
- build: exit 0
- browser: exit 1

The frontend lockfile was regenerated from pinned direct dependencies, not recovered from the old filesystem. Browser checks use a disposable loopback server, fictional records and a mocked model. No live provider/model verification, public deployment, outbound enablement, lead contact or main/recovery changes. This remains a WIP checkpoint. Read actual failures before continuing; do not infer full acceptance from baseline or integrity passes.

## Native implementation milestone — 2026-09-18

Continued from `37d5c3a25c4173df8371cd11ba99a54325fad972`; remote still matched
that anchor when inspected. `516d793541ebd871c3e482ad7d49cfee989cdf5b` added
fresh native verification (no recovery scripts/patches applied). That fresh run
35314035701 passed integrity, 155 backend tests and frontend typecheck/lint/build.

Implemented stable accessible names for saved views and the mobile Organize
button, consistently named keyboard geometry controls, a single authenticated
bounded dataset read, read-only 429 retry honoring Retry-After, and an explicit
retry-data control. Original 180/minute admin and bad-auth limits remain intact.
The initial browser rerun reproduced unstable names and request exhaustion.
After those fixes, the previously unreached persistence path exposed the test
helper writing sessionStorage on opaque about:blank; scoped that helper to the
local HTTP fixture. Every browser scenario now owns a fresh server, worker and
SQLite database (no production bypass/reset endpoint, no shared rate-limit state).

Local commands: `python recovery/ai-leads-workspace-v2/verify_github_checkpoint.py`;
`python -m pytest tests/test_workspace_http.py -q` (9 passed, 1 upstream warning);
`cd frontend && npm run typecheck && npm run lint && npm run build` (all passed);
`RELAY_TEST_PYTHON=/mnt/data/relay-venv/bin/python PLAYWRIGHT_BROWSERS_PATH=/mnt/data/playwright npm run test:e2e`
(8 passed in 36.3s, zero skipped/retries). The path variables are this session's
isolated toolchain only; normal setup uses your Python and Playwright installation.
All source data/model responses are fictional. No real provider calls were made.

Remaining at this milestone: broaden UI acceptance (actual model-planned geometry,
board/columns/history/undo/locks/error recovery); audit all original requirements;
finish architecture/setup/license documentation, full regression rerun, screenshots
and unmerged pull request. This milestone is not a completed release claim.

## Shared-workspace acceptance continuation — 2026-09-18

Inspected newer remote head `1bf36a7aab36cc72b32ff6ab19ee2217fc2984a1` rather
than resetting the supplied `37d5c3a` anchor. Source/toolchain verification commit
`ab71d202e3bc245a7b4d85c5717f45eabf9e2f23` ran in Actions 35320940023.
Local baseline: recovery integrity passed; `python -m pytest tests -q`: 164
passed, one upstream AnyIO warning (15.36s); frontend typecheck/lint/build passed;
eight desktop/mobile Chromium tests passed, zero retries/skips (1.4m).

Native UI changes at this milestone: recoverable initial-load errors; keyboard
panel reordering with collision resolution and immutable pins; board pagination;
preserved local queries when pinning/configuring; immediate invalidation of
selected evidence across saved-view/practice switches; independent widget-read
retry and refresh after task edits; paginated workspace history; detail emphasis
retained when creating a view. Typecheck and lint passed after these changes.
Broader browser tests are being added; these new interactions are not yet claimed
verified. All data/providers are fictional/mocked; no live provider verification.

Publication uses an ordinary guarded incremental source patch because git network
access is unavailable in the editing container. The publisher verifies base and
result blobs and removes its one-time input after applying it to native files.
It never executes the older restoration patches or workflows. Recovery, main,
calling, provider destinations and recording settings remain unchanged.

Next: complete AI geometry/manual pin/lock/reload flows, board/column/history and
error-recovery coverage; security/resilience audit, full rerun, setup/architecture/
license documentation, actual screenshots and an unmerged pull request.


## Final implementation milestone — 2026-09-18

Continued from newer native head 152dcbcd41f307e53710893ae5f3c30af3648ee6,
preserving main and the original recovery. Completed the shared manual/AI
acceptance flow rather than stopping at the original three failed lookups.

Added actual model-planned geometry fixtures; keyboard/pointer collision
handling with protected pins; correct initial mobile breakpoint; complete
small-screen navigation and tab locking; board-only pagination; history,
column controls, proposals/locks, read/model failure recovery and stale-edit
acceptance coverage. Worker resume now rejects changed model/prompt/schema
provenance, and extraction-cache keys include source-chunk content.
Documentation covers setup, actual library/license integration, evidence,
retention limits, configuration and every original requirement category.
Native CI uses the real lockfile/build/fixtures, not restoration scripts.

Local verification of these exact source blobs: integrity passed; backend
169 passed, one upstream AnyIO deprecation warning (15.83s); typecheck,
lint, production build passed; geometry unit tests 8 passed; desktop/mobile
Chromium 20 passed (3.5m), zero retries/skips. Command:
`python scripts/verify_workspace.py --output /mnt/data/relay-final-verification`.
The local environment used Python 3.13.5, Node 22, the pinned dependencies,
RELAY_TEST_PYTHON pointing to its isolated venv and PLAYWRIGHT_BROWSERS_PATH
pointing to its installed Chromium. Build ran before browsers.

Exploratory expanded tests exposed two genuine failures: pointer resize
left overlapping panels and keyboard mobile edits selected lg instead of
initial sm. Both were repaired, then the full suite rerun without skips or
relaxed layout validation. GitHub publication checks full patch hashes,
parent/result blobs and unchanged recovery. One detected patch-transfer
punctuation typo was corrected before those checks; no malformed native
source was published. New one-time publication inputs are removed after
applying; older recovery scripts are not executed.

Fresh clean-checkout results and screenshots will be recorded separately
below and under verification/acceptance-2026-09-18. No live model/provider,
real lead contact, recording change, public deployment, main change, merge
or force push. Remaining verification boundaries: live reasoning quality,
real voice/PSTN, physical mobile/Safari/Firefox, load/security/compliance
certification, retention operations and multi-process use. These are not
claimed verified. Final delivery includes an unmerged pull request.
