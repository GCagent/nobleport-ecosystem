"""Stephanie.ai — core orchestrator agent.

Owns intake, estimating, jobs, finance workflow support, comms, real-estate
concierge, and the live avatar session surface. Constitutional constraints
(human-gated financial/legal actions) are enforced upstream by the engine.
"""

from __future__ import annotations

from typing import Any

from nobleport.agents.base import BaseAgent


class StephanieAgent(BaseAgent):
    name = "stephanie"

    def register_handlers(self) -> None:
        self.on("intake.lead_capture", self._lead_capture)
        self.on("estimating.project_brief", self._project_brief)
        self.on("estimating.cost_model", self._cost_model)
        self.on("estimating.bid_package", self._bid_package)
        self.on("finance.invoice_builder", self._invoice_builder)
        self.on("avatar.session", self._avatar_session)

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
        return (f"Noted: \"{text}\". I coordinate intake, estimating, permits, "
                "compliance, jobs, and invoicing workflows — which one should "
                "we start?")
