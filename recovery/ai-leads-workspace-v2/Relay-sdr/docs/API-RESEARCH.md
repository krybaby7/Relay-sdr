# API contract research — 16 September 2026

Primary-source documentation was browsed during implementation. These references explain the intended protocol, not proof of live-account success. Provider contracts can evolve: recheck the pages when deploying.

## OpenAI

- GPT-Live overview: https://developers.openai.com/api/docs/guides/live
- Server WebSocket transport: https://developers.openai.com/api/docs/guides/voice-websockets
- Delegation and tools: https://developers.openai.com/api/docs/guides/live-delegation
- Primary WebSocket reference: https://developers.openai.com/api/reference/resources/live/primary-websocket
- Partner integrations: https://developers.openai.com/api/docs/guides/live-partner-integrations

Implementation decisions supported by these documents:

1. Use `wss://api.openai.com/v1/live/sessions`, with server bearer authentication and no query parameters. Send `session.start` first; wait for `session.started` before audio/application commands. Do not substitute the older Realtime turn loop.
2. Configure `gpt-live-1` with separate hosted Responses delegation. The default backend here is configurable `gpt-5.6-terra`; model/account compatibility has not been checked with credentials.
3. Use `session.input_audio.append` and `session.output_audio.delta`. Browser PCM16 is 24 kHz; Twilio-compatible PCMU is 8 kHz. Input/output use the startup session audio format.
4. The backend responses arrive under a `response.event` envelope. Track the outer delegation ID and nested response ID; collect completed `function_call` items from `response.output_item.done`. Do not rely on a terminal response's empty output list.
5. After an authorized tool batch, submit each `response.item.create` function result, then one bare `response.create`. The application—not the model—owns permission boundaries, side effects, and deduplication.
6. Transcript events are fragments, not authoritative completed speaker turns. Backend completion is not proof that speech was heard. There is no assumed output-audio-done event in this bridge. Ending tools use a brief, explicitly approximate goodbye grace period, not an invented speech-completion signal.
7. Request `session.close` on ordinary stop and wait for `session.closed` usage with a bounded timeout. Track missing finalization rather than fabricating usage. Error paths can close without final usage; this is exposed in history.
8. Voice and backend processing have separate usage/cost components. This app does not calculate an invoice, estimate unknown prices, or include provider credit.

## Twilio

- GPT-Live resources: https://www.twilio.com/en-us/blog/developers/twilio-openai-gpt-live-1-api-resources
- Outbound GPT-Live example: https://www.twilio.com/en-us/blog/developers/tutorials/integrations/outbound-calls-openai-gpt-live-1-node
- Calls resource: https://www.twilio.com/docs/voice/api/call-resource
- Request security/signatures: https://www.twilio.com/docs/usage/security

Implementation decisions:

1. Create outbound calls with the Calls REST API; supply per-call TwiML and status callback URLs, a ringing timeout, provider `TimeLimit`, and `Record=false`.
2. Wait for a validated Twilio stream start before opening the upstream Live session. Preserve native μ-law payloads between the two providers.
3. Validate `X-Twilio-Signature` using the Auth Token and exact canonical URL/form parameters; bind account, call ID, caller number, destination, stream ID, and a separate one-use media token.
4. Include every incoming form parameter in HMAC verification. The unit suite checks the documented HMAC test vector. HTTPS voice URL port handling and the optional WSS trailing slash follow the security documentation; actual deployment must still be tested.
5. Treat provider callbacks as call-lifecycle evidence, with callback sequence ordering. Do not interpret “completed” as a successful sales outcome.

The project implements direct Media Streams bridging; it does not install Twilio Agent Connect, a Twilio SDK, or a third-party voice orchestration framework.
