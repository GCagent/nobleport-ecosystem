# Stephanie.ai Open-Source Voicebox Pilot

**Status:** STAGED & READY FOR RUNTIME ACTIVATION — AUDIBLE VOICE NOT YET VERIFIED  
**Owner:** NoblePort Systems / Stephanie.ai  
**Repository:** `GCagent/nobleport-ecosystem`  
**Pilot branch:** `feature/stephanie-voicebox-pilot`  
**Pull request:** `#18` — draft / mergeable

## Objective

Add a self-hosted Voicebox speech layer to Stephanie.ai without making the existing avatar text path depend on TTS availability. The implementation is staged and ready for runtime connection, but it must not be described as live or production-verified until an actual Voicebox instance, authorized Stephanie voice profile, audible output, and test evidence are verified.

## Current State

| Layer | Status |
|---|---|
| Code integration — Voicebox `POST /speak`, fail-open text path, `/voice/status` | STAGED |
| Configuration and Docker routing | STAGED |
| Unit/integration test cases | ADDED TO REPOSITORY |
| Focused GitHub Actions workflow | ADDED — PASSING RUN NOT YET EVIDENCED |
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

## Implemented Surfaces

- `orchestrator/nobleport/voice.py`
  - `VoiceSettings`
  - `VoiceboxSpeaker`
  - Voicebox `POST /speak` adapter
  - `/health` reachability check
  - timeout parsing and fail-open behavior
- `GET /voice/status`
  - reports enabled/reachable status without exposing the configured provider URL
- `WS /ws/avatar`
  - preserves the normal Stephanie text reply
  - queues the same reply for voice when enabled
  - returns provider/enabled/queued metadata
- Docker Compose
  - passes Voicebox configuration to the orchestrator
  - routes to a separately running host Voicebox instance through `host.docker.internal`
- Repository tests
  - disabled/fail-open behavior
  - provider summary privacy
  - voice status endpoint
  - avatar voice metadata

## Activation Path

### 1. Verify Voicebox reachability

From the same runtime/network context as the Stephanie orchestrator, confirm the Voicebox service responds:

```bash
curl "$VOICEBOX_URL/health"
```

Then inspect available profiles or configured bindings using the Voicebox API/version actually deployed. Confirm that the selected Stephanie voice is authorized for NoblePort use.

### 2. Verify direct speech behavior

Send a controlled test to the Voicebox `POST /speak` endpoint using the authorized profile or client default binding. A successful HTTP response alone is not sufficient evidence; verify that audible speech is actually produced at the intended output target.

Example payload shape used by the Stephanie adapter:

```bash
curl -X POST "$VOICEBOX_URL/speak" \
  -H "Content-Type: application/json" \
  -H "X-Voicebox-Client-Id: stephanie-ai" \
  -d '{"text":"Hello, this is Stephanie","profile":"stephanie","personality":false}'
```

If the deployed Voicebox version uses a different profile identifier or default client binding, use the verified runtime configuration rather than assuming the literal `stephanie` profile name.

### 3. Enable Stephanie voice

```text
STEPHANIE_VOICE_ENABLED=true
```

Set `VOICEBOX_URL` to the reachable private endpoint and optionally set `VOICEBOX_PROFILE` to the authorized profile identifier. Restart the orchestrator after changing runtime environment configuration.

### 4. Verify through Stephanie

1. Check `GET /api/voice/status` through the NoblePort gateway.
2. Connect to `/ws/avatar`.
3. Send a controlled test prompt.
4. Verify the JSON reply.
5. Verify audible Stephanie speech.
6. Record success/failure and latency evidence.

### 5. Merge only after evidence review

PR #18 may be merged after code/test review, but merge status and production activation are separate decisions. Do not classify Stephanie voice as production-live solely because the PR is merged.

## Not Yet Implemented or Verified

- managed TTS fallback routing
- provider-neutral multi-provider implementation beyond the current Voicebox adapter
- provider circuit breaker and retry policy
- AuditBeacon voice-provider events
- streaming audio to a remote browser or phone client
- STT / microphone input
- barge-in / interruption handling
- LiveKit or Pipecat realtime transport
- benchmark harness and measured latency
- passing GitHub Actions evidence for the current branch
- runtime validation against an actual Voicebox instance
- authorized Stephanie voice profile/default binding confirmation
- first verified audible response generated from Stephanie's `/ws/avatar` flow

## Acceptance Gates

The pilot remains **STAGED** until all gates pass with reproducible evidence.

| Gate | Requirement |
|---|---|
| G1 | Voicebox instance reachable from the running Stephanie orchestrator |
| G2 | Authorized Stephanie voice profile/default binding confirmed |
| G3 | A `/ws/avatar` test message produces verified audible speech |
| G4 | Time-to-first-audio and end-to-end latency measured |
| G5 | Voice consistency and prosody reviewed by a human |
| G6 | Selected model license reviewed for intended commercial use |
| G7 | Voice consent / authorization documented |
| G8 | Secrets, logs, retention, and access controls reviewed |
| G9 | Passing code/test evidence captured |
| G10 | Explicit production approval recorded before public/customer-facing rollout |

## Security and Governance

- No voice-cloning workflow may be enabled without documented authorization from the voice owner.
- Do not commit API keys, model credentials, voice samples, or private recordings.
- Keep Voicebox on a local/private network path; do not expose an unauthenticated local API directly to the public internet.
- Public broadcasting, outbound calling, publishing, and customer-facing autonomous voice actions remain governed by the Stephanie.ai Authority Matrix and applicable human approval requirements.
- Treat third-party TTS model licenses separately from the Voicebox application license.
- Any future recording or transcription capability must follow applicable consent, privacy, and retention requirements.

## Engineering Task Status

- [x] Locate Stephanie.ai avatar integration point.
- [x] Add Voicebox configuration schema.
- [x] Implement Voicebox HTTP `/speak` adapter.
- [x] Connect voice output to the existing avatar WebSocket path.
- [x] Add voice provider health/status endpoint.
- [x] Add timeout and fail-open behavior.
- [x] Add repository test cases.
- [x] Add focused GitHub Actions orchestrator test workflow.
- [ ] Obtain passing GitHub Actions evidence for the branch.
- [ ] Connect and verify a running Voicebox instance.
- [ ] Confirm authorized Stephanie voice profile/default binding.
- [ ] Verify first audible Stephanie response end-to-end.
- [ ] Implement managed-provider fallback.
- [ ] Add circuit breaker/retry policy.
- [ ] Add AuditBeacon voice events.
- [ ] Add benchmark harness and evidence.
- [ ] Validate the selected TTS model license.

## Truth Status

**Current classification:** STAGED & READY FOR RUNTIME ACTIVATION — CODE AND CONFIGURATION ARE IN PLACE, BUT ACTUAL AUDIBLE SPEECH, RUNTIME CONNECTIVITY, PASSING CI EVIDENCE, PERFORMANCE, AND PRODUCTION DEPLOYMENT ARE NOT YET VERIFIED.
