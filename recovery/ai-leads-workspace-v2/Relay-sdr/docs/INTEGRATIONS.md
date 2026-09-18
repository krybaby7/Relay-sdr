# Integration contracts

## 1. Lead intake — data only

Configure an independent `INBOUND_LEAD_TOKEN` with a cryptographically random value. This endpoint does not use the workspace token, does not start calls, and does not grant lead-read access.

```http
POST /integrations/leads
Authorization: Bearer YOUR_INBOUND_LEAD_TOKEN
Content-Type: application/json
```

```json
{
  "name": "Consenting test contact",
  "company": "Your own company",
  "phone": "+12025550121",
  "timezone": "Africa/Cairo",
  "language": "English",
  "notes": "Operator-provided context. Treated as untrusted by the agent.",
  "consent": false,
  "consent_note": ""
}
```

Use only real permission evidence when setting `consent: true`; include source, date, and scope in `consent_note`. This record is an assertion, not a legal determination. Phone numbers are normalized only for presentation characters; country codes are never guessed. Unknown fields are rejected.

Response:

```json
{"id":"lead_...","created":true,"dialed":false}
```

A duplicate number returns its existing ID with `created: false`; it does not replace notes or re-enable a suppressed contact. Rate limit: 60 intake requests/minute per source address in this single-process pilot. HTTP bodies are limited to 256 KiB. For bulk work use the operator's CSV flow; there is no public bulk-dial endpoint.

## 2. Outcome delivery — reviewed, signed, fixed destination

Set `OUTCOME_WEBHOOK_URL` to your trusted HTTPS endpoint and `OUTCOME_WEBHOOK_SECRET` to an independent random secret. No redirect is followed. The application never accepts a model-selected endpoint.

Only provider-confirmed terminal **telephone** calls enter the outbox. Browser practice and scripted demos are excluded. The operator reviews the call and clicks **Approve delivery**. A non-2xx/network response is marked uncertain, because the receiver may have processed the request before the response was lost. No automatic retry occurs.

Payload outline:

```json
{
  "id": "call_stable_id",
  "type": "call.completed",
  "data": {
    "call_id": "call_stable_id",
    "lead_id": "lead_id_from_intake",
    "kind": "twilio",
    "status": "completed",
    "provider_sid": "CA...",
    "outcome": "qualified",
    "summary": "A factual, operator-reviewable summary.",
    "next_step": "A human should confirm a requested time.",
    "requests": [
      {
        "type": "meeting",
        "details": "Preferred time and timezone, if actually provided.",
        "status": "needs_human_confirmation",
        "created_at": "UTC timestamp",
        "tool_call_id": "provider_tool_call_id"
      }
    ],
    "ended_at": "UTC timestamp"
  }
}
```

`type: call.completed` means the local attempt has reached a provider terminal state, which can also be failed/busy/no-answer/canceled. Inspect `data.status` and `data.outcome`; never infer a sale from the event type. No complete transcript, audio, or consent evidence is included in this payload.

Headers:

```text
X-Relay-Event-Id: same stable call ID
X-Relay-Timestamp: Unix seconds, generated on this delivery attempt
X-Relay-Signature: sha256=<hex digest>
Content-Type: application/json
```

The HMAC-SHA256 input is `timestamp + "." + exact_raw_body_bytes`. Receivers should verify using a constant-time comparison, reject stale timestamps (for example outside a five-minute tolerance after accounting for clock skew), and **deduplicate the stable event ID durably** before external side effects. JSON reserialization before validation will change the signed bytes.

Minimal verification logic for a receiver:

```python
import hashlib
import hmac
import time

def verify(secret: str, raw_body: bytes, timestamp: str, supplied: str) -> bool:
    try:
        if abs(time.time() - int(timestamp)) > 300:
            return False
    except (TypeError, ValueError):
        return False
    expected = "sha256=" + hmac.new(
        secret.encode(), timestamp.encode() + b"." + raw_body, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected.encode(), supplied.encode())
```

This helper alone does not implement replay protection: a receiving application still needs a durable processed-event table and transactionally safe side effects. Delivery is not guaranteed exactly once.

## 3. A new calling connector — implementation requirements

A data webhook is not a phone connector. Before implementing another provider, verify that its official APIs actually support the desired account/app/region and expose both outbound call control and real-time bidirectional audio.

Keep `app/live.py` as the voice/backend orchestration layer and implement a provider adapter analogous to `app/telephony.py` plus routes analogous to `/twilio/*`. The adapter must provide call creation without automatic network retries, status reconciliation, explicit hangup, verified provider webhooks, a call-bound media handshake, supported audio conversion, duration limits, callback ordering, restart behavior, and test isolation.

The media bridge interface is:

```python
await run_bridge(
    config, store, call_id,
    receive_audio,  # async -> {"type": "audio", "audio": "base64"}, control, or None
    emit,           # async consumes safe audio/transcript/ready/error/ended events
    stop_event,
)
```

For browser calls, the selected codec is PCM16 LE mono 24 kHz. Twilio uses PCMU mono 8 kHz. A new codec/provider needs an explicit configuration branch and tests; do not label arbitrary audio as PCMU or assume old Realtime protocol events work with GPT-Live.

The current implementation is intentionally concrete rather than a fictional universal SDK. `Config.connectors()` reports configured credentials, not connection verification. Add a dedicated connector ID and account-backed tests before displaying a new app as supported.

## 4. Calendar and human handoff

`request_meeting` and `request_human` only persist requests. Their responses explicitly prohibit claiming a booking or transfer.

A later calendar connector must check actual availability, timezone, attendee identity, consent, idempotency, and event-create success before telling the prospect that a meeting is booked. A later warm-transfer connector must check the target's availability and provider bridge status before promising that a human is connected. Neither exists in this release.
