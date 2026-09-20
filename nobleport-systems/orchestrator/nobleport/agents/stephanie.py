"""Stephanie.ai — core orchestrator agent.

Owns intake, estimating, jobs, finance workflow support, comms, real-estate
concierge, the live avatar session surface, and the nano-ecosystem infill
chain (site selection through five-harness). Constitutional constraints
(human-gated financial/legal/acquisition actions) are enforced upstream by
the engine. Stephanie never authorizes acquisition.
"""

from __future__ import annotations

from typing import Any

from nobleport.agents.base import BaseAgent
from nobleport import nano_demo


class StephanieAgent(BaseAgent):
    name = "stephanie"

    def register_handlers(self) -> None:
        self.on("intake.lead_capture", self._lead_capture)
        self.on("estimating.project_brief", self._project_brief)
        self.on("estimating.cost_model", self._cost_model)
        self.on("estimating.bid_package", self._bid_package)
        self.on("finance.invoice_builder", self._invoice_builder)
        self.on("avatar.session", self._avatar_session)
        self.on("nano.site_selector", self._nano_site)
        self.on("nano.feasibility", self._nano_feasibility)
        self.on("nano.generative_design", self._nano_design)
        self.on("nano.sequence_optimizer", self._nano_sequence)
        self.on("nano.draw_manager", self._nano_draw)
        self.on("nano.stress_tester", self._nano_stress)
        self.on("nano.property_ops", self._nano_ops)
        self.on("nano.orchestrator", self._nano_orchestrator)
        self.on("nano.five_harness", self._nano_harness)

    async def _lead_capture(self, action: str, payload: dict[str, Any],
                            simulate: bool) -> dict[str, Any]:
        lead = payload.get("lead", {})
        return {
            "lead": {
                "name": lead.get("name", "unknown"),
                "source": lead.get("source", "web"),
                "property_address": lead.get("property_address"),
                "scope_hint": lead.get("scope_hint"),
            },
            "normalized": True,
        }

    async def _project_brief(self, action: str, payload: dict[str, Any],
                             simulate: bool) -> dict[str, Any]:
        return {
            "brief": {
                "title": payload.get("title", "Untitled project"),
                "scope_hint": payload.get("lead", {}).get("scope_hint"),
                "sections": ["scope", "assumptions", "exclusions", "schedule"],
            }
        }

    async def _cost_model(self, action: str, payload: dict[str, Any],
                          simulate: bool) -> dict[str, Any]:
        line_items = payload.get("line_items", [])
        subtotal = sum(float(i.get("amount", 0)) for i in line_items)
        overhead = round(subtotal * 0.10, 2)
        return {
            "cost_model": {
                "line_items": len(line_items),
                "subtotal": subtotal,
                "overhead": overhead,
                "total": round(subtotal + overhead, 2),
            }
        }

    async def _bid_package(self, action: str, payload: dict[str, Any],
                           simulate: bool) -> dict[str, Any]:
        return {"bid_package": {"format": "pdf", "requires_client_signature": True}}

    async def _invoice_builder(self, action: str, payload: dict[str, Any],
                               simulate: bool) -> dict[str, Any]:
        return {"invoice": {"basis": "progress_billing",
                            "awo_refs": payload.get("awo_refs", [])}}

    async def _avatar_session(self, action: str, payload: dict[str, Any],
                              simulate: bool) -> dict[str, Any]:
        return {"session": {"persona": "stephanie", "transport": "websocket"}}

    async def _nano_site(self, action: str, payload: dict[str, Any],
                         simulate: bool) -> dict[str, Any]:
        return {"screen": nano_demo.site_screen(payload)}

    async def _nano_feasibility(self, action: str, payload: dict[str, Any],
                                simulate: bool) -> dict[str, Any]:
        return {"feasibility": nano_demo.feasibility_model(payload)}

    async def _nano_design(self, action: str, payload: dict[str, Any],
                           simulate: bool) -> dict[str, Any]:
        return {"design": nano_demo.design_concepts(payload)}

    async def _nano_sequence(self, action: str, payload: dict[str, Any],
                             simulate: bool) -> dict[str, Any]:
        return {"sequence": nano_demo.construction_sequence(payload)}

    async def _nano_draw(self, action: str, payload: dict[str, Any],
                         simulate: bool) -> dict[str, Any]:
        return {"draw": nano_demo.draw_package(payload)}

    async def _nano_stress(self, action: str, payload: dict[str, Any],
                           simulate: bool) -> dict[str, Any]:
        return {"stress": nano_demo.stress_tests(payload)}

    async def _nano_ops(self, action: str, payload: dict[str, Any],
                        simulate: bool) -> dict[str, Any]:
        return {"ops": nano_demo.property_ops(payload)}

    async def _nano_orchestrator(self, action: str, payload: dict[str, Any],
                                 simulate: bool) -> dict[str, Any]:
        return {"graph": nano_demo.evidence_graph(payload)}

    async def _nano_harness(self, action: str, payload: dict[str, Any],
                            simulate: bool) -> dict[str, Any]:
        return {"control_plane": nano_demo.five_harness(payload)}

    def avatar_reply(self, message: str) -> str:
        """Deterministic avatar dialog stub; the model-backed pipeline is a
        STAGED integration and slots in behind this interface."""
        text = message.strip()
        if not text:
            return "I'm Stephanie, the NoblePort orchestrator. How can I help?"
        lowered = text.lower()
        if "permit" in lowered:
            return ("Permit workflows run through PermitStream. I can start a "
                    "permit_submission workflow for your project — filing "
                    "itself always waits for human sign-off.")
        if "estimate" in lowered or "bid" in lowered:
            return ("I can run lead_to_estimate to produce a project brief, "
                    "takeoff, and cost model. The client-facing bid package is "
                    "human-reviewed before it goes out.")
        if "token" in lowered or "nbpt" in lowered or "invest" in lowered:
            return ("NBPT operations are staged and human-gated: I can draft "
                    "proposals and simulate transfer compliance, but all "
                    "treasury and securities actions require human multi-sig.")
        if any(k in lowered for k in ("infill", "adu", "nano", "amesbury",
                                      "newburyport", "site selector",
                                      "feasibility")):
            return ("I can run nano_infill_chain — site screen, feasibility, "
                    "entitlement, design, sequence, stress, draft draw, ops, "
                    "and the five-harness. It is STAGED due diligence. I do "
                    "not authorize acquisition; draws wait for a human.")
        return (f"Noted: \"{text}\". I coordinate intake, estimating, permits, "
                "compliance, jobs, invoicing, and the nano infill chain — "
                "which one should we start?")
