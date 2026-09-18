# Relay SDR

A local-first, browser-based AI sales-development workspace, built around the **new GPT-Live API**, with a Twilio outbound-call connector and separate CRM data endpoints.

**AI-managed leads workspace · 18 September 2026 · single-user, single-process pilot.**

The workspace is implemented and has deterministic acceptance coverage; it is not a production calling release. See [workspace setup and architecture](docs/WORKSPACE-ARCHITECTURE.md), [requirements coverage](docs/WORKSPACE-ACCEPTANCE.md), and the committed verification logs under `verification/acceptance-2026-09-18/`. Earlier verification documents describe the September 16 baseline, not this feature.

The source is runnable. No API keys, provider accounts, lead lists, customer data, or live-call authorization are included. **No real calls were placed during development.** All provider-path tests use mocks. Read `docs/VERIFICATION.md` for the exact checks and gaps.

## What is included

| Area | Implemented behavior |
| --- | --- |
| Workspace | Persistent shared AI/manual views, responsive draggable canvas, keyboard alternatives, pins/locks, proposals, history, undo/reset, private token login, real backend aggregates |
| Lead intelligence | Evidence-linked cumulative assessments; potential, priority, coverage and eligibility kept separate; confirmed human corrections; internal commitments; paginated call/source/history details; typed custom fields |
| Background reasoning | Separate optional Grok 4.6 (xAI) workspace model, durable SQLite jobs and LangGraph checkpoints, bounded retries/chunks/budgets, stale-write rejection, explicit gaps, no outbound tools |
| Leads | Manual add/edit, validated E.164 numbers, timezone, consent evidence, CSV import with per-row errors, deduplication by number, irreversible do-not-call entries in the app |
| Playbook | Company/product/facts, qualification questions, next-step goal, voice/language/tone, allowed calling days and hours, operator approval — edited in Lab |
| Lab | One operator page: GPT-Live config, Grok 4.6 orchestrator (pause/rubric), shared instructions, no-key scripted preview, and mic test once the Live key is on the server |
| Phone connector | Twilio call creation, signed TwiML and callbacks, call-bound Media Stream token, PCMU audio passthrough to GPT-Live |
| Sales tools | Save outcome; save a meeting request; save a human-callback request; opt out; end conversation |
| Review | Transcript fragments, summaries, request-only labels, usage-finalization state, JSON export, manual call stop and provider-state check |
| CRM input | Scoped-token `POST /integrations/leads`; importing never triggers dialing |
| CRM output | Manual approval of a real-call outcome, fixed HTTPS destination, HMAC-signed webhook, stable event ID; no transcript export by default |

**Meeting requests are not calendar bookings. Human-callback requests are not warm transfers.** No Gmail, Calendar, HubSpot, Salesforce, WhatsApp, SIM dialer, or other native app connector is implemented. There is no auto-dial campaign, lead scraping, mass messaging, or unattended redial.

## Start locally

Use Python **3.11 or newer**. Development tests ran on Python 3.13.5. The `/leads` interface uses React and TypeScript. Compiled assets are committed in `web/workspace`, so normal local use needs only Python and one server, with no CDN. To change or rebuild the frontend, use Node 22 and the commands below. Other Relay sections retain their original interface.

### macOS / Linux

```bash
cd relay-sdr
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
python run.py
```

### Windows PowerShell

```powershell
cd relay-sdr
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
.\.venv\Scripts\python.exe run.py
```

Open the local address printed in the terminal, normally `http://localhost:8080`. Paste the **workspace token** from that same terminal. It is an application login secret, not your OpenAI key.

If port 8080 is occupied, change `PORT` in `.env`. Restart after configuration changes. Start from the project directory so `.env` and the default `.data` path resolve consistently.

First try **Lab → Run scripted preview**. It makes no model request, microphone request, or telephone call. Fictional sample contacts are optional and are explicitly blocked from live dialing.

The backend must remain running. Closing the browser does not shut down the server. This package is not a deployed web service, hosted demo, mobile APK, or desktop installer.

## Use and build the AI-managed leads workspace

Open **Leads** or `/leads`. Manual search, fields, views, widgets, layouts and evidence inspection work without a model key. The workspace starts with Adaptive presentation preferences, but server-side reasoning remains **disabled until explicitly configured**.

To enable only internal workspace reasoning, edit your private `.env`:

```dotenv
WORKSPACE_ENABLED=true
WORKSPACE_API_KEY=your_separate_xai_key
WORKSPACE_MODEL=grok-4.6
WORKSPACE_TIMEZONE=UTC
ENABLE_OUTBOUND=false
```

`WORKSPACE_MODEL` should be `grok-4.6` (xAI Responses API). There is no silent model/key substitution and no fallback to `OPENAI_API_KEY`. Restart the server. Approve accurate product facts and the sales rubric in **Lab** before treating assessments as qualified. Enabling reasoning sends relevant stored real-call text and human notes to xAI; it does not enable dialing, messaging, recording or webhook approval. The orchestrator has no calling tools.

**Manual** keeps presentation changes as proposals. **Suggest** previews each agent presentation change. **Adaptive** applies small, validated, reversible changes, but larger/structural changes require approval unless the operator explicitly allows small structural changes. Pins and locks remain protected. Pause reasoning in agent settings to stop new processing; an already executing request may finish. The server must stay running for background processing.

Use **Customize canvas** to add/configure/remove widgets, drag or resize with the pointer, or use the labelled Up/Down/Wider/Narrower/Taller/Shorter buttons. Save the layout. Use the view definition to rename, duplicate, group/filter, or emphasize a detail section. **More workspace options** includes history/undo/reset, custom fields, rubric, and view locking. On small screens, **Menu** preserves all application sections and the tab-lock action.

To rebuild the committed application assets:

```bash
cd frontend
npm ci
npm run typecheck
npm run lint
npm run test:unit
npm run build
cd ..
python run.py
```

`npm run build` writes `web/workspace`; the existing FastAPI server serves it. No separate frontend development server is required. Dependency versions are pinned in the npm lockfile and Python requirements/constraints. For the complete deterministic check, install development requirements and Chromium, then run:

```bash
python -m pip install -r requirements-dev.txt
npm ci --prefix frontend
cd frontend
npx playwright install chromium
cd ..
python scripts/verify_workspace.py --output verification/local
```

The browser fixture creates a disposable loopback-only database for every test, uses a clearly labelled deterministic model, and never contacts a provider. The verifier **builds before testing browsers**. Fixture orchestration proves application behavior, not live model reasoning quality.

## Enable a real browser voice test

In the server-side `.env`:

```dotenv
OPENAI_API_KEY=your_actual_server_side_key
LIVE_MODEL=gpt-live-1
BACKEND_MODEL=gpt-5.6-terra
ENABLE_OUTBOUND=false
```

Restart. Edit Lab (voice, language, tone, and whether a browser test is allowed), then click **Start voice test**. Grant microphone access only to your own local/HTTPS workspace. Headphones are useful for your first audio check.

The configured account needs access to both the Live voice model and its Responses backend. Model names are configurable. Account access, exact pricing, audio quality, interruptions, and speech/tool behavior have **not** been tested against a live account in this build.

Audio flows from browser → your server → OpenAI and back. The browser path uses a mono 24 kHz PCM16 AudioWorklet with echo-cancellation requested from the browser. It requires a browser that can create a 24 kHz AudioContext; it fails explicitly rather than sending the wrong sample rate. This is a server WebSocket implementation, **not WebRTC**.

The agent is instructed to disclose that it is AI, mention conversation notes, ask permission to continue, ask one question at a time, use approved facts, and delegate sales decisions and actions to its backend. These are model instructions, not proof that every live utterance will be handled correctly. Human evaluation is required.

## Enable a tightly controlled Twilio test

Do not start with a prospect list. Use **your own telephone number**, explicit permission, an appropriate calling window, and a reviewed playbook.

1. Configure a Twilio account and a voice-capable caller number you are authorized to use. Check the provider's permissions for your actual destination country and account.
2. Serve the app at a stable public **HTTPS origin** with WebSocket support. A development tunnel may forward that origin to your local server. Keep the server running. Do not expose it over plain HTTP or use an untrusted computer.
3. Set the values below in `.env`, then restart.
4. Add your own number as a **new real test lead**, record genuine permission evidence, confirm its timezone, and approve the playbook.
5. Click **Call** beside the lead. Read the preflight checks, then explicitly confirm the real call. Review the provider console and call history afterward.

```dotenv
PUBLIC_BASE_URL=https://your-own-public-host.example
TWILIO_ACCOUNT_SID=AC_your_actual_account_sid
TWILIO_AUTH_TOKEN=your_actual_twilio_auth_token
TWILIO_FROM_NUMBER=+your_authorized_caller_number
ALLOWED_NUMBERS=+your_own_test_number
ENABLE_OUTBOUND=true
MAX_CALL_SECONDS=180
MAX_DAILY_CALLS=10
MAX_CONCURRENT_CALLS=1
```

Those are placeholders, not working credentials or valid numbers. Actual Twilio Account SIDs use `AC` followed by 32 hexadecimal characters; the adapter validates this. Phone numbers require `+`, country code, and digits.

The call-create request supplies the TwiML URL and status-callback URL automatically. The routes are:

```text
POST /twilio/voice/{relay_call_id}
POST /twilio/status/{relay_call_id}
WSS  /twilio/media/{relay_call_id}
```

Never disable signature checks to make a tunnel work. `PUBLIC_BASE_URL` must match the externally visible origin; do not add a path or query string. The signature verifier derives canonical URLs from this trusted setting, not from forwarded host headers. HTTPS voice callback signatures strip an explicit port as described by Twilio. WSS verification supports the exact configured HTTPS/WSS form and optional trailing slash. **Real provider handshake compatibility still needs verification on the chosen deployment.**

Twilio audio must identify itself as mono `audio/x-mulaw`, 8 kHz. Its stream token is passed through a TwiML `Parameter`, not a query string. A signed connection still must prove the expected account, call ID, stream ID, and single-use token.

### Dialing gates

The server rechecks live dialing enabled, required configuration present, approved playbook, nonsample lead, recorded permission and evidence, permanent suppression, pilot allowlist, lead-local calling window, concurrency, daily telephone attempts, and unresolved previous calls. Explicit per-call confirmation and an idempotency key are also required.

Daily limits count **telephone attempts**, including failed attempts, by UTC creation date. They do not limit the total number of browser practice sessions. OpenAI and telephone charges are external to this application; duration caps are not a currency-denominated spending cap. Configure provider-account budgets and inspect real usage separately.

Only one application process / Uvicorn worker may use a workspace. The workspace has a durable local analysis job queue, **not** a distributed dialing queue, distributed lock, or multi-worker deployment model.

### Unknown call state: do not blindly redial

A network timeout does not prove a call failed to start. A previous `unknown` phone attempt blocks further dialing. Reusing the same request ID returns the existing attempt without creating another call.

Use **Call history → Review → Check provider** when a provider call SID is already bound. If the process crashed or timed out before it learned the SID, this pilot cannot safely reconcile that automatically. Inspect the Twilio console and resolve the incident before resuming. Do not delete the state or change the request ID merely to get around the block. A future release should add a supervised SID-attachment/reconciliation workflow.

Provider status callbacks use sequence numbers and cannot regress a confirmed terminal state. A completed connection is not a qualified lead or successful sale. The app does not configure answering-machine detection; its agent is instructed to end on voicemail or IVR, but live recognition is unverified.

## Connect a CRM or another app

There are two separate integration problems:

**Data:** an external tool can submit a lead and receive approved call outcomes. The included HTTP endpoints handle that, using separate scoped credentials. See `docs/INTEGRATIONS.md`.

**Calling:** an app must expose a usable outbound-call and live-audio interface. A contacts API, an OAuth connection, or access to a CRM record does not itself provide a voice path. This build includes Twilio only. Another provider requires its own adapter, webhook authentication, codec handling, and call-lifecycle tests.

The workspace token gives broad local operator access. Do not give it to a CRM or automation tool. The intake token cannot read leads, use admin APIs, or dial.

## Data, privacy, and security boundaries

- Provider keys are loaded from server environment variables and never returned by the dashboard API.
- A generated operator token is stored at `.data/admin-token`; the browser stores it in tab-scoped sessionStorage after login. Use the avatar/Lock action to clear the browser copy. Anyone with that token can access the workspace: there are no user accounts, MFA, roles, or per-user audit controls.
- `.data/relay.sqlite3` stores contact details, consent assertions, transcript fragments, call summaries, playbook snapshots, suppression, tool deduplication, and outbox state. It is **not encrypted at rest**. Protect the machine, filesystem, `.env`, backups, and terminal logs. The workspace adds a separate `workspace-checkpoints.sqlite3` database. Controlled source correction/redaction and derived-data invalidation are available, but there is no retention scheduler or comprehensive erasure of independent notes, labels, backups or external provider copies. See the workspace architecture document for the precise scope.
- The app does not persist audio files; Twilio call creation requests `Record=false`. That does not determine OpenAI/Twilio retention, logging, or organizational settings. Review those independently.
- Browser practice can use a lead as rehearsal context but never updates that lead's sales status, permanently suppresses it, or publishes an external outcome. Practice calls still save their own transcript/notes.
- Outbound webhook targets are fixed in trusted server configuration. The model cannot supply a URL, telephone destination, or arbitrary HTTP operation. Outbox transmission requires operator approval. Do not configure a destination you do not control or trust.
- This is not a legal-compliance certification. Review the real calling and data-processing jurisdictions, AI disclosure, permission requirements, applicable restrictions, provider rules, and retention before contacting anyone. A checked consent box is an operator assertion, not independently verified evidence.

For backup, stop the server cleanly and copy the entire `.data` directory to protected storage. It contains personal information and the login token. Do not place `.env`, `.data`, or real call exports in a shared source repository.

## Tests

```bash
python -m pip install -r requirements-dev.txt
python -m pytest -q
```

The automated suite uses an isolated SQLite database and fake Twilio/GPT-Live peers. It will not dial or contact OpenAI. It covers policy gates, input validation, authentication, origin/host checks, signed callbacks, idempotency, unknown states, tool permissions, practice isolation, delegation batches, audio message shape, and session finalization.

The optional browser script is `tests/ui_smoke.py`. It requires a **fresh, isolated, no-key workspace**, Playwright, and Chromium. It imports fictional test data. It is not part of default pytest discovery. See `docs/VERIFICATION.md` for the restricted offline mode actually exercised here.

## Project map

```text
run.py                     local launcher
app/config.py              environment and connector presence
app/models.py              validated input and tool schemas
app/db.py                  single-process SQLite persistence
app/policy.py              real-dial gates
app/telephony.py            fixed-origin Twilio REST and signatures
app/live.py                 GPT-Live bridge and delegated sales tools
app/main.py                 authenticated APIs, callback/media routes
app/workspace/             evidence, intelligence, shared spec, durable worker and APIs
frontend/                  React/TypeScript sources, pinned lockfile and browser tests
web/                       compiled workspace + existing UI and AudioWorklet
tests/                     local automated and browser checks
docs/                      integration contract, API research, verification
```

## Before treating this as production

Account-backed voice/PSTN tests, broader security review, operational monitoring, retention controls, provider budget enforcement, user management, deployment hardening, supervised unknown-call reconciliation, production queue operations, thorough live opt-out evaluation, audio/latency measurement, confirmed calendar integration, human-transfer integration, and chosen-country compliance review are still needed. Do not market this pilot as universally connected, legally certified, or ready for unattended mass calling.
