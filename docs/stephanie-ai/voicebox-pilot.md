# Stephanie.ai Open-Source Voicebox Pilot

**Status:** STAGED CODE INTEGRATION — RUNTIME VOICE NOT YET VERIFIED  
**Owner:** NoblePort Systems / Stephanie.ai  
**Repository:** `GCagent/nobleport-ecosystem`  
**Pilot branch:** `feature/stephanie-voicebox-pilot`

## Objective

Evaluate and integrate an open-source, self-hosted voice layer for Stephanie.ai that reduces vendor lock-in while preserving a path for a managed-provider fallback. The pilot must not be represented as live, production-ready, or deployed until runtime evidence, latency tests, licensing review, security review, and human approval gates are complete.

## Current Staged Architecture

```text
Client / Avatar WebSocket
        |
        v
Stephanie.ai Orchestrator
        |
        +--> deterministic avatar reply
        |
        +--> non-blocking VoiceboxSpeaker
                |
                +--> Voicebox POST /speak
                +--> configured voice profile or Voicebox default binding
```

The existing `/ws/avatar` text response remains fail-open. When `STEPHANIE_VOICE_ENABLED=true`, the same reply is also queued to Voicebox. If Voicebox is disabled or unavailable, the text response still returns normally.

## Implemented Configuration

```text
STEPHANIE_VOICE_ENABLED=false
VOICEBOX_URL=http://host.docker.internal:17493
VOICEBOX_PROFILE=
VOICEBOX_CLIENT_ID=stephanie-ai
VOICEBOX_PERSONALITY=false
VOICEBOX_TIMEOUT_SECONDS=10
```

For a direct local orchestrator run outside Docker, `VOICEBOX_URL` can use `http://127.0.0.1:17493`.

## Implemented Surfaces

- `orchestrator/nobleport/voice.py`
  - `VoiceSettings`
  - `VoiceboxSpeaker`
  - `POST /speak` adapter
  - Voicebox `/health` reachability check
  - timeout handling
  - fail-open result handling
- `GET /voice/status`
  - reports whether the provider is enabled and reachable
  - does not expose the configured Voicebox endpoint
- `WS /ws/avatar`
  - returns the normal Stephanie text response
  - queues the same response for voice when enabled
  - returns provider/enabled/queued metadata
- Docker Compose
  - passes Voicebox configuration into the orchestrator
  - adds `host.docker.internal` host-gateway routing for a separately running local Voicebox service
- Test coverage
  - disabled/fail-open speaker behavior
  - provider summary privacy
  - voice status endpoint
  - avatar voice metadata

## Not Yet Implemented or Verified

- managed TTS fallback routing
- provider-neutral multi-provider interface beyond the current Voicebox adapter
- circuit breaker and retry policy
- AuditBeacon voice-provider events
- streaming audio to a remote browser or phone client
- STT / microphone input
- barge-in / interruption handling
- LiveKit or Pipecat realtime transport
- benchmark harness and measured latency
- runtime validation against an actual Voicebox instance and authorized Stephanie voice profile

## Required Acceptance Gates

The pilot remains **STAGED** until all gates pass with reproducible evidence.

| Gate | Requirement |
|---|---|
| G1 | Voicebox instance reachable from the running Stephanie orchestrator |
| G2 | Authorized Stephanie voice profile/default binding confirmed |
| G3 | First successful `/ws/avatar` message produces audible speech |
| G4 | Time-to-first-audio and end-to-end latency measured under representative load |
| G5 | Interruption / barge-in behavior validated before realtime conversational use |
| G6 | Voice consistency and prosody reviewed by a human |
| G7 | Underlying model licenses reviewed for intended commercial use |
| G8 | Voice consent / authorization documented |
| G9 | Secrets, logs, retention, and access controls reviewed |
| G10 | Explicit production approval recorded before public or customer-facing rollout |

## Benchmark Metrics

Capture at minimum:

- time to first audio
- total synthesis latency
- realtime factor
- p50 / p95 / p99 latency
- error rate
- concurrent-session capacity
- CPU / GPU / memory utilization
- interruption response time when realtime transport is added

## Security and Governance

- No voice-cloning workflow may be enabled without documented authorization from the voice owner.
- Do not commit API keys, model credentials, voice samples, or private recordings.
- Keep Voicebox on a local or private network path; do not expose its unauthenticated local API directly to the public internet.
- Public broadcasting, outbound calling, publishing, or customer-facing autonomous voice actions remain subject to the Stephanie.ai Authority Matrix and applicable human-approval requirements.
- Treat third-party model licenses separately from the Voicebox application license.
- Any future recording or transcription feature must follow applicable consent, privacy, and retention requirements.

## Activation Procedure

1. Start Voicebox and confirm its health endpoint is reachable from the environment running the Stephanie orchestrator.
2. Confirm an authorized Stephanie voice profile exists or configure the `stephanie-ai` Voicebox client binding/default voice.
3. Set `STEPHANIE_VOICE_ENABLED=true`.
4. Set `VOICEBOX_URL` to the reachable private Voicebox endpoint.
5. Optionally set `VOICEBOX_PROFILE` to the authorized profile name or ID.
6. Restart the orchestrator.
7. Check `GET /api/voice/status` through the NoblePort gateway.
8. Connect to `/ws/avatar`, send a test prompt, and verify both the JSON reply and audible speech.
9. Capture latency/error evidence before changing the status from STAGED.

## Engineering Task Status

- [x] Locate current Stephanie.ai avatar integration point.
- [x] Add Voicebox configuration schema.
- [x] Implement Voicebox HTTP `/speak` adapter.
- [x] Connect Voicebox output to the existing avatar WebSocket path.
- [x] Add voice provider health/status endpoint.
- [x] Add timeout and fail-open behavior.
- [x] Add unit/integration test cases to the repository.
- [x] Add a focused GitHub Actions orchestrator test workflow.
- [ ] Obtain a passing GitHub Actions test run for the branch.
- [ ] Connect and verify a running Voicebox instance.
- [ ] Confirm the authorized Stephanie voice profile/default binding.
- [ ] Implement managed-provider fallback.
- [ ] Add provider circuit breaker and retry policy.
- [ ] Add AuditBeacon voice events.
- [ ] Add benchmark harness and attach evidence.
- [ ] Validate model-license matrix for the selected TTS engine.

## Upstream Project

- Voicebox: `jamiepine/voicebox`

LiveKit and Pipecat remain optional future evaluation candidates for realtime browser/phone transport. They are not part of the current staged implementation.

## Truth Status

**Current classification:** CODE INTEGRATED ON DRAFT PR / STAGED — ACTUAL AUDIBLE SPEECH, RUNTIME CONNECTIVITY, PERFORMANCE, AND PRODUCTION DEPLOYMENT NOT YET VERIFIED.
