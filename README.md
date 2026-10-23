# NoblePort Ecosystem

AI-assisted construction and real estate workflow software with human-gated decision support.

NoblePort connects intake, estimating, authorized work orders (AWOs), billing,
permit preparation, compliance review, and property due diligence. Stephanie.ai
coordinates workflows with GCagent.ai, PermitStream.ai, and CyBorg.ai.

This repository contains the public website, platform services, demonstrations,
and proposed token infrastructure. Implementation, catalog status, and deployment
evidence are distinct: a module marked `LIVE` does not by itself establish that
a production service or external integration is running.

## Start here

- [Platform core and deployment guide](nobleport-systems/README.md)
- [Module catalog](nobleport-systems/orchestrator/nobleport/modules.py)
- [Workflow definitions](nobleport-systems/orchestrator/nobleport/workflows/definitions.py)
- [Launch gates and restrictions](core/config/launch-gates.json)
- [Arbitrum / NBPT / KUZO configuration](nobleport-systems/config/nbpt-arbitrum.json)

## Project status

The table summarizes repository classifications, not a fresh production audit.
The previous root README referenced the April 2026 whitepaper and Deep Truth
Audit `TA-2026-05-23`; those references are historical context, not current
runtime verification. Readiness percentages are omitted because they do not
define measurable acceptance criteria.

| Area | Repository classification | Meaning and limits |
| --- | --- | --- |
| Intake, estimating, jobs/AWOs, billing support | `LIVE` modules in the catalog | Operational workflow surfaces; handlers and deployment evidence must be checked for each capability. |
| Human approval routing | Implemented in the workflow engine | HIGH/CRITICAL-risk steps pause for approval; critical treasury/securities steps are never dispatched in-platform. |
| Stephanie.ai | Mixed module statuses | Workflow coordination exists; its catalog includes operational, staged, and simulated capabilities. |
| GCagent.ai / PermitStream.ai | Compliance and permit modules are `STAGED` | Simulation and preparation; municipal integration and licensed human review remain necessary. |
| CyBorg.ai identity layer | Identity modules are `STAGED` | Identity, accreditation, and security integration are not established as production services. |
| Nano infill chain | `STAGED` | Evidence-graph demonstration for infill/ADU due diligence; does not authorize acquisition or establish permit approval. |
| KUZO quotes / NBPT reads / Solana observation | `READ_ONLY` | Workflow engine forces simulation; no state-changing execution. |
| NBPT contracts | Source implementation and proposed infrastructure | Deployment, on-chain verification, and offering approval are not established by this repository. |
| Arbitrum / Uniswap configuration | Configured, verification pending | Read-only intent; transaction preparation and autonomous trading disabled. |

Unhandled modules can return simulated acknowledgments. Catalog breadth is not
evidence that every listed integration has an operational implementation.

## Architecture

The main platform lives in [`nobleport-systems/`](nobleport-systems/README.md):

```text
Browser / API client
        |
Caddy (TLS; VPS configuration)
        |
Rust gateway (axum, :8080)
  rate limiting / API proxy / avatar WebSocket bridge
        |
Python orchestrator (FastAPI, :8000)
  module registry / workflow engine / human approval gate
        |
  Stephanie.ai / GCagent.ai / PermitStream.ai / CyBorg.ai

Compose also provisions Postgres 15 and Redis 7.
```

The API currently constructs workflow runs and approval state in memory.
Provisioning Postgres and migrations does not establish durable persistence for
those objects. Verify persistence and recovery before relying on the stack for
production records.

| Path | Purpose |
| --- | --- |
| [`index.html`](index.html) | Public website and static preview entry point |
| [`nobleport-systems/gateway/`](nobleport-systems/gateway/) | Rust edge gateway |
| [`nobleport-systems/orchestrator/`](nobleport-systems/orchestrator/) | Python API, agents, registry, and workflows |
| [`nobleport-systems/migrations/`](nobleport-systems/migrations/) | Database schema |
| [`core/gateway/`](core/gateway/README.md) | Separate Python gateway implementation and documentation |
| [`noble-port-verification/`](noble-port-verification/) | Verification service and tests |
| [`contracts/`](contracts/) | Solidity token, identity, and compliance sources |
| [`tokenomics/`](tokenomics/) | Historical models and projections; not verified token state |

## Quick start

### Static website preview

Requires Git and Python 3. From a terminal:

```bash
git clone https://github.com/GCagent/nobleport-ecosystem.git
cd nobleport-ecosystem
python3 -m http.server 8000 --bind 127.0.0.1
```

Open <http://127.0.0.1:8000>. Stop the server with Ctrl+C.
This serves static files only; it does not start APIs, agents, or blockchain
integrations.

### Local orchestrator

Requires Python 3.11 or newer. From the repository root:

```bash
cd nobleport-systems/orchestrator
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
pytest
uvicorn nobleport.api:app --host 127.0.0.1 --port 8000
```

Use a different port or stop the static preview first if port 8000 is occupied.
In another terminal:

```bash
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/modules
curl http://127.0.0.1:8000/workflows
```

### Local Rust gateway

In another terminal, from the repository root, with the Rust toolchain installed:

```bash
cd nobleport-systems/gateway
ORCHESTRATOR_URL=http://127.0.0.1:8000 cargo run
```

Query the orchestrator through the gateway at
`http://127.0.0.1:8080/api/modules`. The avatar WebSocket route is
`ws://127.0.0.1:8080/ws/avatar`.

### Docker / VPS setup

The Compose stack includes Caddy with project-specific public domains. Follow
the [platform deployment instructions](nobleport-systems/README.md#deploy-hostinger-vps)
for DNS and VPS setup; it is a separate path from the localhost preview.

From the repository root on the configured host:

```bash
cd nobleport-systems
cp .env.example .env
# Edit .env and replace POSTGRES_PASSWORD before continuing.
docker compose config --quiet
docker compose up -d --build
docker compose ps
```

The stack requires Docker Engine and the Compose plugin. Keep `.env` out of
version control. Public deployment requires access controls and operational
validation: the current approval API accepts an actor string and does not
authenticate the approver in its route handlers.

## Execution and review policy

The [workflow engine](nobleport-systems/orchestrator/nobleport/workflows/engine.py)
uses catalog risk and status to control execution:

- HIGH/CRITICAL-risk steps enter `AWAITING_APPROVAL`; rejection ends the run.
- Critical treasury/securities steps produce `PREPARED_FOR_MULTISIG` after
  approval. Execution remains off-platform through human multi-signature control.
- `STAGED` and `READ_ONLY` modules are invoked in simulation.
- Permit and compliance outputs support human review; municipal authorities
  determine approvals.
- The [launch-gate policy](core/config/launch-gates.json) blocks NBPT sales,
  fractional ownership offerings, swap execution, hosted wallets, and other
  regulated activities until their stated requirements are met.

Workflow approval policy does not establish authenticated authorization,
regulatory clearance, or a deployed multi-signature arrangement.

## NBPT token details

NBPT is proposed token infrastructure. The repository includes an ERC-3643-style
identity/compliance-restricted token implementation; this description is not a
certification of standards compliance.

| Item | Repository evidence |
| --- | --- |
| Model supply | Historical materials specify 100,000,000 NBPT. |
| Source behavior | `NBPTSecurityToken.sol` supports agent-controlled mint/burn and does not implement a fixed 100 million supply cap. |
| Transfer controls | Source checks recipient identity, compliance rules, freeze status, and pause state. |
| Mint/burn authority | Solidity uses approved agent addresses; platform human gates are a separate control layer. |
| Deployment status | No verified deployment or current circulating supply is established here. |
| Offering status | Blocked by repository launch policy pending required review. |

See the [token source](contracts/src/token/NBPTSecurityToken.sol) and
[historical tokenomics materials](tokenomics/). Historical release schedules,
burn schedules, price projections, and asset-backing claims are not evidence of
executed transactions or current valuation.

### Networks and public references

- **Ethereum / EVM:** proposed identity, token, and attestation infrastructure.
- **Arbitrum One (chain ID 42161):** current public NBPT/KUZO configuration,
  explicitly marked `CONFIGURED_IN_REPOSITORY_NOT_DEPLOYED_OR_ONCHAIN_VERIFIED`.
- **Solana:** read-only USDC rail observation in the module catalog.
- **IPFS / Arweave:** staged document-anchoring integration.
- **Stellar:** under evaluation in the platform documentation.

| Reference | Address / name | Verification status |
| --- | --- | --- |
| Configured Arbitrum NBPT | `0xf72dfcab3889ecd409eeea2c21b7eebd6de79a47` | User-provided; on-chain verification pending |
| Configured KUZO wallet | `0x5108b22204f214352ad500719344E1C865B1dbDb` | Ownership verification pending signed message |
| Historical Ethereum wallet | `0xc59e66BB2b6E19699F82A72a1569821cb1711504` | Retained from previous README; not independently verified |
| Historical Solana reference | `6fbr88Qmc1LSh5XATjcaGzvVnq1H7QmB57wAyxrKMXas` | Retained from previous README; not independently verified |
| Historical NBPT contract reference | `0x3778E67655Ec26D6bC8294C6F7a1e754AFD2C91C` | Network/deployment relationship to current configuration not established |
| ENS / contact | `nobleport.eth` | Project reference |

The historical NBPT reference and configured Arbitrum address are distinct;
the repository does not establish a migration or equivalence between them.
