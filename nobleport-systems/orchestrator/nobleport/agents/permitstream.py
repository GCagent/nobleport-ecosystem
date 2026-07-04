"""PermitStream.ai — permit workflow agent.

Owns permit intake, parsing, package assembly, filing (human-gated), and
status tracking. All modules are currently STAGED, so the engine invokes
them in simulation until API validation completes.
"""

from __future__ import annotations

from typing import Any

from nobleport.agents.base import BaseAgent


class PermitStreamAgent(BaseAgent):
    name = "permitstream"

    def register_handlers(self) -> None:
        self.on("permits.intake", self._intake)
        self.on("permits.checklist", self._checklist)
        self.on("permits.submission", self._submission)

    async def _intake(self, action: str, payload: dict[str, Any],
                      simulate: bool) -> dict[str, Any]:
        return {
            "jurisdiction": payload.get("jurisdiction", "unresolved"),
            "permit_types": payload.get("permit_types",
                                        ["building"]),
        }

    async def _checklist(self, action: str, payload: dict[str, Any],
                         simulate: bool) -> dict[str, Any]:
        base = ["application_form", "site_plan", "construction_drawings",
                "contractor_license", "workers_comp_certificate"]
        if "electrical" in payload.get("permit_types", []):
            base.append("electrical_load_calculation")
        return {"checklist": base}

    async def _submission(self, action: str, payload: dict[str, Any],
                          simulate: bool) -> dict[str, Any]:
        return {
            "filing": {
                "portal": payload.get("portal", "municipal_portal"),
                "submitted": not simulate,
                "note": ("Simulated filing — STAGED module" if simulate
                         else "Filed after human approval"),
            }
        }
