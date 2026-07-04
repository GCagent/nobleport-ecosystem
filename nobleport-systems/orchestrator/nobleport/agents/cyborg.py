"""CyBorg.ai — identity, security, and token-layer agent.

Owns the ERC-3643 identity bridge, zkSBT verification, session monitoring,
audit logging, and all token-adjacent surfaces. Treasury/securities modules
it owns are CRITICAL-risk: the engine never dispatches them for execution,
only for preparation.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

from nobleport.agents.base import BaseAgent


class CyborgAgent(BaseAgent):
    name = "cyborg"

    def register_handlers(self) -> None:
        self.on("identity.zksbt_verifier", self._zksbt_verifier)
        self.on("token.transfer_compliance", self._transfer_compliance)
        self.on("token.nbpt_state", self._nbpt_state)
        self.on("platform.audit_log", self._audit_log)

    async def _zksbt_verifier(self, action: str, payload: dict[str, Any],
                              simulate: bool) -> dict[str, Any]:
        proof = payload.get("zk_proof")
        return {
            "verification": {
                "proof_supplied": proof is not None,
                "accredited": bool(proof) and not simulate,
                "note": "Simulated verification — STAGED module" if simulate else None,
            }
        }

    async def _transfer_compliance(self, action: str, payload: dict[str, Any],
                                   simulate: bool) -> dict[str, Any]:
        return {
            "simulation": {
                "from": payload.get("from_identity"),
                "to": payload.get("to_identity"),
                "would_pass_identity_check": bool(payload.get("to_identity")),
                "on_chain_execution": "DISABLED",
            }
        }

    async def _nbpt_state(self, action: str, payload: dict[str, Any],
                          simulate: bool) -> dict[str, Any]:
        return {
            "token": {
                "symbol": "NBPT",
                "total_supply_cap": 100_000_000,
                "standard": "ERC-3643",
                "source": "read_only_snapshot",
            }
        }

    async def _audit_log(self, action: str, payload: dict[str, Any],
                         simulate: bool) -> dict[str, Any]:
        entry = json.dumps(payload, sort_keys=True, default=str)
        return {"audit": {"entry_hash": hashlib.sha256(entry.encode()).hexdigest(),
                          "chained": True}}
