"""GCagent.ai — compliance and document agent.

Owns regulation matching, code lookup, licensing, safety, legal-document
drafting (always human-gated), and document anchoring integrations.
"""

from __future__ import annotations

from typing import Any

from nobleport.agents.base import BaseAgent


class GCAgent(BaseAgent):
    name = "gcagent"

    def register_handlers(self) -> None:
        self.on("compliance.regulation_matcher", self._regulation_matcher)
        self.on("compliance.code_lookup", self._code_lookup)
        self.on("compliance.lien_waiver", self._lien_waiver)

    async def _regulation_matcher(self, action: str, payload: dict[str, Any],
                                  simulate: bool) -> dict[str, Any]:
        jurisdiction = payload.get("jurisdiction", "unknown")
        scope = payload.get("scope", [])
        return {
            "matches": [
                {"jurisdiction": jurisdiction, "trade": t,
                 "requires_licensed_trade": t in ("electrical", "plumbing", "gas")}
                for t in scope
            ],
            "jurisdiction": jurisdiction,
        }

    async def _code_lookup(self, action: str, payload: dict[str, Any],
                           simulate: bool) -> dict[str, Any]:
        return {"code_sections": [], "query": payload.get("code_query")}

    async def _lien_waiver(self, action: str, payload: dict[str, Any],
                           simulate: bool) -> dict[str, Any]:
        return {
            "document": {
                "type": "lien_waiver",
                "waiver_kind": payload.get("waiver_kind", "conditional_progress"),
                "counsel_review_required": True,
            }
        }
