# Verification report

Release 0.1.0 · 16 September 2026

## Performed

**Automated Python suite:** 87 tests passed in the last complete run before this report. Tests use isolated temporary SQLite databases, an in-memory GPT-Live protocol peer, and a fake Twilio adapter. No external provider calls occur. A final rerun is recorded in `test-results.txt` alongside this report.

Coverage includes E.164 normalization/rejection, timezone validation, permission evidence, playbook approval, local calling windows, allowlist, sample exclusion, suppression persistence, concurrency and daily attempt limits, unknown-state blocking, HTTP auth, origin and host checks, body limits, CSV errors, credential non-disclosure in state, dial idempotency, timeout uncertainty, callback signatures and ordering, TwiML stream binding, scoped lead intake, practice isolation, authorized tools, meeting/callback request semantics, response-envelope tool batches with empty terminal output, audio event shape, disclosure prompts, duplicate transcript handling, final session usage, single-use browser tickets, and unauthorized WebSocket rejection.

**UI:** 19 checks passed using Playwright with managed Chromium. The environment blocks browser URL navigation, so the test harness rendered the project's actual local HTML/CSS/JS with `set_content` and injected assets. A test-only Python HTTP bridge sent relative `/api/*` requests to an isolated running localhost app; session storage and the download target were shimmed. Browser administration policies were not changed.

Those checks exercised login, mobile-accessible workspace lock, safe default indicators, sample import, sample-call blocking, manual contact creation, HTML escaping, CSV partial-error feedback, playbook persistence, voice-disabled-without-key state, labeled scripted preview, call review, meeting-request labeling, JSON export payload generation, simulation exclusion from the outbox, and all six tabs at 390 px viewport width. No page-wide horizontal overflow or browser JavaScript exception was observed in those exercised flows. Desktop captures used a 1440 px viewport.

**Visual review:** desktop overview, voice-lab, and connections captures, plus the mobile overview, were inspected. A discovered oversized unstyled SVG was fixed and the browser checks/captures rerun. Tables and mobile navigation intentionally scroll within their own containers. This is not exhaustive accessibility or cross-browser validation.

**Syntax:** Python byte-compilation and `node --check` for both JavaScript files were performed. A localhost HTTP server answered its health endpoint successfully.

## Not performed / not established

No OpenAI account access, live GPT-Live session, real model inference, actual speech recognition, actual microphone capture, audible playback, interruption behavior, latency measurement, long-duration stability, provider billing, real Twilio call, real Twilio webhook/Media Stream handshake, telephone routing/voicemail behavior, or external outcome webhook delivery was tested.

The UI test's offline harness does not establish normal browser networking, browser CSP enforcement, CORS behavior, real browser WebSockets, microphone permissions, or actual browser file-download completion. These need an ordinary browser test on the chosen localhost/HTTPS deployment. HTTP authorization/origin/host checks were separately tested at the server API layer.

No clean-environment dependency installation was tested; the pinned core packages were already installed in the development environment. No multi-user, multitenant, multi-worker, high-load, penetration, mobile-device, jurisdictional legal-compliance, or production deployment review was performed. No paid hosting account, tunnel, calendar, CRM OAuth connection, or user account was configured.

## Before the first customer call

Use your own allowlisted number, verify both provider accounts and the public HTTPS/WSS route, test audio in both directions, review the opening disclosure and interruption behavior, make opt-out/hangup requests, check the actual provider stop and usage, inspect transcript accuracy, and verify that meeting requests are never presented as bookings. Assess the applicable rules for the real jurisdiction and use case. Expand only after measured, supervised tests.
