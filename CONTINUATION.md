# AI leads workspace continuation — 2026-09-18

Branch: `feat/ai-leads-workspace-continue`, forked non-destructively from recovery commit `c0c35ddfb9d23596d492a41a18c79587b1b031b0` (which includes feature head `19c4c091a98f55c63433d9bc405f5b1303191b28`). Main was inspected at `22f69c92ecfe0c690362947351b3703913d7b379` and is not modified.

## Current status

The complete GitHub handoff, RECOVERY.md, RESUME.md, GITHUB-PRESERVATION.json, original 264-line implementation brief, branch heads and ancestry have been read through the connected GitHub tools. The recovery directory remains unchanged. Recovery source is an INITIAL overlay, not a verified release.

Execution limitation: direct git/network DNS in the editing container failed (`Could not resolve host: github.com`). Connected GitHub reads/writes are available. Use a read-only Actions checkout of the native repository for isolated verification and, where necessary, transfer a newly generated native-source/toolchain snapshot for local execution. No old dependency artifact or encoded recovery transport is required.

## Verification

- Current branch/ancestry inspection: complete. Recovery is five commits ahead of historical feature, zero behind; changes are recovery preservation only.
- `verify_github_checkpoint.py`: inspected; execution pending.
- Baseline tests: pending fresh run. Historical logs are not current results.
- Feature integration/tests/browser checks: pending.

## Next steps

1. Run checkpoint integrity and baseline protections in an isolated no-secrets/no-outbound test environment.
2. Restore the 22 native recovered source files into application paths, retaining the original recovery tree untouched.
3. Reconstruct missing router, Store/config/capture/lifecycle integration and styles; repair documented resilience gaps.
4. Test backend, migrations, worker recovery, schema/security boundaries, typecheck/lint/build and desktop/mobile browser behavior. Record exact commands/results here.
5. Push incremental useful milestones and open an accurately described PR; never merge or deploy.

## Boundaries

No changes to main, force pushes, public deployment, outbound enablement, real calls, lead contact, recording settings, secrets or runtime data. Preserve authentication, consent, suppression, calling policy, signed callbacks, unknown-call reconciliation, provider contracts and practice isolation. Mocked tests are not live model/provider verification.
