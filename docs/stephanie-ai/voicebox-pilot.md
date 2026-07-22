# Stephanie.ai Open-Source Voicebox Pilot

**Status:** TARGET / SANDBOX PILOT — NOT PRODUCTION VERIFIED  
**Owner:** NoblePort Systems / Stephanie.ai  
**Repository:** `GCagent/nobleport-ecosystem`  
**Pilot branch:** `feature/stephanie-voicebox-pilot`

## Objective

Evaluate an open-source, self-hosted voice layer for Stephanie.ai that reduces vendor lock-in while preserving a managed-provider fallback. The pilot must not be represented as live, production-ready, or deployed until runtime evidence, latency tests, licensing review, security review, and human approval gates are complete.

## Proposed Architecture

```text
Client / Phone / WebRTC
        |
        v
Stephanie Voice Gateway
        |
        +--> Local Voicebox adapter (primary pilot path)
        |      +--> TTS engine selected by policy
        |      +--> STT / transcription where supported
        |      +--> local voice-profile storage
        |
        +--> Managed TTS adapter (fallback; e.g. ElevenLabs)
        |
        +--> Realtime transport/orchestration (LiveKit or Pipecat)
        |
        v
Stephanie.ai Orchestrator
        |
        +--> Governance / Authority Matrix
        +--> AuditBeacon
        +--> CRM / scheduling / intake workflows
```

## Integration Rule

All voice providers must sit behind a common `StephanieVoiceGateway` interface. Business logic must never depend directly on a single TTS vendor.

Suggested provider contract:

```python
from typing import AsyncIterator, Protocol


class VoiceProvider(Protocol):
    async def synthesize(self, text: str, voice_id: str, **options) -> bytes:
        ...

    async def stream(self, text: str, voice_id: str, **options) -> AsyncIterator[bytes]:
        ...

    async def health(self) -> dict:
        ...
```

## Pilot Scope

1. Add a Voicebox provider adapter without removing the existing managed TTS path.
2. Add configuration-based provider routing:
   - `VOICE_PROVIDER=voicebox`
   - `VOICE_FALLBACK_PROVIDER=elevenlabs`
3. Keep all API keys and voice assets outside source control.
4. Use only voices NoblePort has explicit rights and consent to use.
5. Add health checks, timeout handling, circuit breaking, and fallback behavior.
6. Record provider, latency, success/failure, and fallback events in the audit layer without storing unnecessary raw voice data.
7. Benchmark local inference before any production designation.

## Required Acceptance Gates

The pilot remains **STAGED** until all gates pass with reproducible evidence.

| Gate | Requirement |
|---|---|
| G1 | Time-to-first-audio and end-to-end latency measured under representative load |
| G2 | Interruption / barge-in behavior validated |
| G3 | Voice consistency and prosody reviewed by a human |
| G4 | Realtime transport stability tested across at least 10 representative sessions |
| G5 | Underlying model licenses reviewed for intended commercial use |
| G6 | Voice consent / authorization documented |
| G7 | Secrets, logs, retention, and access controls reviewed |
| G8 | Managed fallback tested with forced local-provider failure |
| G9 | Governance and audit events verified |
| G10 | Explicit production approval recorded before public or customer-facing rollout |

## Benchmark Metrics

Capture at minimum:

- time to first audio byte
- total synthesis latency
- realtime factor
- p50 / p95 / p99 latency
- interruption response time
- transcription latency where applicable
- word error rate for STT tests where applicable
- GPU / CPU / memory utilization
- error rate
- fallback rate
- concurrent-session capacity

## Security and Governance

- No voice-cloning workflow may be enabled without documented authorization from the voice owner.
- Do not commit API keys, model credentials, voice samples, or private recordings.
- Public broadcasting, outbound calling, publishing, or customer-facing autonomous voice actions remain subject to the Stephanie.ai Authority Matrix and applicable human-approval requirements.
- Treat third-party model licenses separately from the application framework license.
- Any recording or transcription feature must follow applicable consent, privacy, and retention requirements.

## Recommended Implementation Sequence

### Phase 1 — Adapter and Configuration

Create a provider-neutral voice gateway and a Voicebox adapter. Keep the existing provider as fallback.

### Phase 2 — Realtime Transport

Connect the gateway to the existing Stephanie.ai avatar/WebSocket channel or a dedicated LiveKit/Pipecat session layer.

### Phase 3 — Benchmark Harness

Run repeatable local and staged tests and publish evidence-backed metrics into the repository.

### Phase 4 — Controlled Pilot

Use an internal Stephanie.ai test environment only. Do not claim production deployment until all acceptance gates pass.

## Initial Engineering Tasks

- [ ] Locate current Stephanie.ai voice and avatar integration points in the repository.
- [ ] Define `VoiceProvider` interface.
- [ ] Add Voicebox configuration schema.
- [ ] Implement Voicebox HTTP adapter.
- [ ] Preserve managed TTS fallback.
- [ ] Add health endpoint and circuit breaker.
- [ ] Add benchmark command / test harness.
- [ ] Add audit events for provider selection and fallback.
- [ ] Document model-license matrix.
- [ ] Run staged benchmark and attach evidence.

## Upstream Projects for Evaluation

- Voicebox: `jamiepine/voicebox`
- LiveKit Agents: `livekit/agents`
- Pipecat: `pipecat-ai/pipecat`

These upstream projects are evaluation candidates. Their presence in this document does not establish that they are installed, integrated, security-reviewed, license-approved, or deployed in NoblePort infrastructure.

## Truth Status

**Current classification:** APPROVED PILOT ARCHITECTURE / IMPLEMENTATION TRACK — CODE INTEGRATION AND RUNTIME VERIFICATION PENDING.
