# Stephanie.ai Open-Source Voicebox Pilot

**Status:** STAGED & READY FOR RUNTIME ACTIVATION — AUDIBLE VOICE NOT YET VERIFIED  
**Owner:** NoblePort Systems / Stephanie.ai  
**Repository:** `GCagent/nobleport-ecosystem`  
**Pilot branch:** `feature/stephanie-voicebox-pilot`  
**Pull request:** `#18` — draft / mergeable

## Objective

Add a self-hosted Voicebox speech layer to Stephanie.ai without making the existing avatar text path depend on TTS availability. The code and configuration are staged, and the focused orchestrator CI run has passed. Runtime connectivity, authorized voice binding, audible output, performance, and production activation remain unverified.

## Current State

| Layer | Status |
|---|---|
| Code integration — Voicebox `POST /speak`, fail-open text path, `/voice/status` | STAGED |
| Configuration and Docker routing | STAGED |
| Unit/integration tests | ADDED |
| Focused GitHub Actions workflow | PASSED |
| PR #18 | DRAFT / MERGEABLE |
| Voicebox service reachable from Stephanie runtime | PENDING VERIFICATION |
| Authorized Stephanie voice profile/default binding | PENDING VERIFICATION |
| Audible speech from `/ws/avatar` | PENDING VERIFICATION |
| Production activation | NOT APPROVED / NOT VERIFIED |

## Current Staged Architecture

```text
Client / Avatar WebSocket
        |
        v
Stephanie.ai Orchestrator
        |
        +--> deterministic avatar text reply
        |
        +--> non-blocking VoiceboxSpeaker
                |
                +--> Voicebox POST /speak
                +--> authorized profile or configured default binding
```

The existing `/ws/avatar` text response remains fail-open. When `STEPHANIE_VOICE_ENABLED=true`, Stephanie queues the same reply to Voicebox. If Voicebox is disabled or unavailable, the text reply continues to work.

## Implemented Configuration

```text
STEPHANIE_VOICE_ENABLED=false
VOICEBOX_URL=http://host.docker.internal:17493
VOICEBOX_PROFILE=
VOICEBOX_CLIENT_ID=stephanie-ai
VOICEBOX_PERSONALITY=false
VOICEBOX_TIMEOUT_SECONDS=10
```

For a direct local orchestrator run outside Docker, `VOICEBOX_URL` may use `http://127.0.0.1:17493`.

## Verified Upstream API Assumptions

The current upstream Voicebox documentation shows:

- `GET /health` for service health.
- `GET /profiles` for listing voice profiles.
- `POST /speak` for agent voice output.
- `X-Voicebox-Client-Id` for per-client voice binding.
- `profile` may be a profile name or id; Voicebox resolves explicit profile first, then client binding, then the configured global default.
- Native Bearer-token authentication is not documented for the local REST examples. If NoblePort places Voicebox behind an authenticated reverse proxy, that proxy authentication is deployment-specific and separate from the native Voicebox API.
- `POST /speak` is used to trigger playback through Voicebox. It must not be treated as a direct MP3-download endpoint unless the deployed version is independently verified to behave that way.

## Runtime Activation and Verification

### 1. Verify Voicebox reachability

Run this from the same runtime/network context as the Stephanie orchestrator:

```bash
curl -f "$VOICEBOX_URL/health"
```

Expected result: successful HTTP response from the deployed Voicebox service.

If NoblePort intentionally adds authentication at a reverse proxy, include the proxy-required credentials there. Do not assume native Voicebox Bearer authentication unless the deployed environment has explicitly added it.

### 2. Verify the authorized Stephanie profile or client binding

List profiles:

```bash
curl -f "$VOICEBOX_URL/profiles"
```

Confirm the authorized Stephanie voice by exact profile name or id. Do not require a `status: active` field unless the deployed API actually returns one.

The current Stephanie adapter can also use the `stephanie-ai` client binding when `VOICEBOX_PROFILE` is empty.

### 3. Verify direct Voicebox speech

```bash
curl -f -X POST "$VOICEBOX_URL/speak" \
  -H "Content-Type: application/json" \
  -H "X-Voicebox-Client-Id: stephanie-ai" \
  -d '{"text":"Hello, this is Stephanie. Voice connection verified.","profile":"stephanie","personality":false}'
```

A successful HTTP response is not enough. Verify that the intended Voicebox host/output target actually produces audible speech in the authorized Stephanie voice.

If the authorized profile uses a different name or id, replace `stephanie` with the verified runtime identifier. If the `stephanie-ai` client already has a verified default binding, the explicit `profile` field may be omitted.

### 4. Enable Stephanie voice in staging

```text
STEPHANIE_VOICE_ENABLED=true
```

Set `VOICEBOX_URL` to the reachable private endpoint and, if needed, set `VOICEBOX_PROFILE` to the verified authorized profile. Restart the orchestrator after changing runtime environment configuration.

### 5. Verify the full Stephanie path

1. Check `GET /api/voice/status` through the NoblePort gateway.
2. Connect to `/ws/avatar`.
3. Send a controlled test prompt.
4. Verify the JSON response.
5. Verify audible Stephanie speech.
6. Record success/failure and latency evidence.

## Runtime Evidence Package

Capture at minimum:

| Evidence | Method |
|---|---|
| Voicebox health | Save the successful `/health` response and HTTP status |
| Profile/binding proof | Save the relevant `/profiles` result or verified client-binding evidence |
| Direct speech proof | Record the test result showing audible playback from `POST /speak` |
| Stephanie integration status | Save the `/api/voice/status` response |
| Full flow proof | Record the `/ws/avatar` test and confirmed audible output |
| Runtime logs | Capture relevant Voicebox and orchestrator logs for the test window |
| Performance | Capture time-to-first-audio, end-to-end latency, and errors |

Do not store private voice samples or unnecessary raw recordings in the repository.

## Merge and Production Gates

PR #18 may move from draft to review after the runtime evidence package is captured and reviewed. Merging and production activation are separate decisions.

Before production activation:

- [ ] Runtime evidence reviewed.
- [ ] Authorized voice profile/default binding confirmed.
- [ ] Full staging conversation smoke test passed.
- [ ] Rollback confirmed: `STEPHANIE_VOICE_ENABLED=false`.
- [ ] Selected TTS model license reviewed for intended commercial use.
- [ ] Privacy, logging, retention, and access controls reviewed.
- [ ] Explicit production approval recorded.

Only after those gates should production set:

```text
STEPHANIE_VOICE_ENABLED=true
```

## Not Yet Implemented or Verified

- managed TTS fallback routing
- provider-neutral multi-provider implementation beyond the current Voicebox adapter
- provider circuit breaker and retry policy
- AuditBeacon voice-provider events
- streaming audio to a remote browser or phone client
- STT / microphone input
- barge-in / interruption handling
- LiveKit or Pipecat realtime transport
- benchmark harness and measured production-grade latency
- runtime validation against an actual Voicebox instance
- authorized Stephanie voice profile/default binding confirmation
- first verified audible response generated from Stephanie's `/ws/avatar` flow

## Engineering Task Status

- [x] Locate Stephanie.ai avatar integration point.
- [x] Add Voicebox configuration schema.
- [x] Implement Voicebox HTTP `/speak` adapter.
- [x] Connect voice output to the existing avatar WebSocket path.
- [x] Add voice provider health/status endpoint.
- [x] Add timeout and fail-open behavior.
- [x] Add repository test cases.
- [x] Add focused GitHub Actions orchestrator test workflow.
- [x] Obtain passing GitHub Actions evidence for the branch.
- [ ] Connect and verify a running Voicebox instance.
- [ ] Confirm authorized Stephanie voice profile/default binding.
- [ ] Verify first audible Stephanie response end-to-end.
- [ ] Capture runtime evidence package.
- [ ] Implement managed-provider fallback.
- [ ] Add circuit breaker/retry policy.
- [ ] Add AuditBeacon voice events.
- [ ] Add benchmark harness and evidence.
- [ ] Validate the selected TTS model license.

## Truth Status

**Current classification:** STAGED & READY FOR RUNTIME ACTIVATION — CODE, CONFIGURATION, AND CI ARE VERIFIED AT THE REPOSITORY LEVEL; ACTUAL AUDIBLE SPEECH, RUNTIME CONNECTIVITY, AUTHORIZED VOICE BINDING, PERFORMANCE, AND PRODUCTION DEPLOYMENT ARE NOT YET VERIFIED.
