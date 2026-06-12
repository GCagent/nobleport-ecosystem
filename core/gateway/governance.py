"""Governance gate — L0 through L4, fail-closed.

This is the enforcement layer that blocks bad calls before execution. It does
NOT do string filtering in isolation; it ties into the existing Compliance
Bridge config (core/config/launch-gates.json) so the prohibited-claim list,
the RED-gate scopes, and the NY geo-block are all driven from one place that
counsel already reviews.

Gate ladder (first failure wins):
  L0  topology / schema      unknown target agent -> BLOCK
  L4  prohibited claim        danger word in message -> BLOCK
  L4  RED-gate scope          securities/treasury/etc. scope -> BLOCK
  L3  NY geo-block            NY resident + blocked activity -> BLOCK
  L2  payload size            message too large -> BLOCK
  L3/L4 human approval        write needs a signature it does not have -> PARK
  ----                        otherwise -> PERMIT
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from .envelope import GateOutcome, McpEnvelope
from .registry import AGENT_NAMES, HUMAN_APPROVAL_LEVELS

log = logging.getLogger("nobleport.gateway.governance")

# Used only if launch-gates.json cannot be read — still fail-closed.
_FALLBACK_PROHIBITED = (
    "guaranteed returns", "risk-free", "sec approved", "sec-compliant",
    "guarantees permit approval", "guarantees compliance", "autonomous execution",
)
_FALLBACK_RED = (
    "nbpt_sale", "tokenized_fractional_ownership", "kuzo_swap_execution",
    "hosted_wallet", "ai_trade_execution", "yield_staking", "stablecoin_issuance",
    "public_secondary_market",
)
_FALLBACK_NY = (
    "nbpt_purchase", "kuzo_swap", "tokenized_real_estate", "hosted_wallet",
    "virtual_currency_business",
)
_NY_CODES = frozenset({"ny", "new_york", "new york", "nyc"})


def _norm(value: str) -> str:
    return value.strip().lower().replace(" ", "_").replace("-", "_")


class GovernanceGate:
    def __init__(self, config_path: str, max_message_chars: int = 2000):
        self.max_message_chars = max_message_chars
        self.prohibited: tuple[str, ...] = _FALLBACK_PROHIBITED
        self.red_scopes: frozenset[str] = frozenset(_FALLBACK_RED)
        self.ny_blocked: frozenset[str] = frozenset(_FALLBACK_NY)
        self._load(config_path)

    def _load(self, config_path: str) -> None:
        try:
            data = json.loads(Path(config_path).read_text())
        except Exception as exc:
            log.warning("launch-gates config unreadable (%s); using fail-closed fallbacks", exc)
            return
        words = (
            data.get("danger_words", {})
            .get("prohibited_in_public_materials", [])
        )
        if words:
            self.prohibited = tuple(w.lower() for w in words)
        red = data.get("launch_gates", {}).get("red", {}).get("modules", {})
        if red:
            self.red_scopes = frozenset(_norm(k) for k in red)
        ny = data.get("geo_blocks", {}).get("new_york", {}).get("blocked_activities", [])
        if ny:
            self.ny_blocked = frozenset(_norm(a) for a in ny)

    def evaluate(self, env: McpEnvelope) -> GateOutcome:
        try:
            return self._evaluate(env)
        except Exception as exc:  # fail-closed on any unexpected error
            log.error("governance gate raised, failing closed: %s", exc)
            return GateOutcome(decision="BLOCK", level="L0",
                               reason=f"gate_error_fail_closed:{type(exc).__name__}")

    def _evaluate(self, env: McpEnvelope) -> GateOutcome:
        level = env.normalized_level()

        # L0 — topology: the target must be a known internal agent.
        if env.target_agent not in AGENT_NAMES:
            return GateOutcome(decision="BLOCK", level="L0",
                               reason=f"unknown_target_agent:{env.target_agent}")

        # L4 — prohibited claim screen.
        msg = env.message.lower()
        for term in self.prohibited:
            if term in msg:
                return GateOutcome(decision="BLOCK", level="L4",
                                   reason=f"prohibited_claim:{term}")

        # L4 — RED-gate scope. Match across action, module, project and payload.
        haystack = {
            _norm(env.action), _norm(env.module),
            _norm(env.project_id or ""), _norm(str(env.payload.get("action", ""))),
            _norm(str(env.payload.get("scope", ""))),
        }
        hit = haystack & self.red_scopes
        if hit:
            return GateOutcome(decision="BLOCK", level="L4",
                               reason=f"red_gate_blocked:{sorted(hit)[0]}")

        # L3 — NY geo-block.
        if _norm(env.requestor_region or "") in {_norm(c) for c in _NY_CODES}:
            if haystack & self.ny_blocked:
                return GateOutcome(decision="BLOCK", level="L3",
                                   reason="ny_geo_block")

        # L2 — payload size.
        if len(env.message) > self.max_message_chars:
            return GateOutcome(decision="BLOCK", level="L2",
                               reason="message_too_large")

        # L3 / L4 — human approval required for sensitive writes.
        needs_human = level in HUMAN_APPROVAL_LEVELS or env.human_approval_required
        if needs_human and not env.human_signature:
            return GateOutcome(decision="PARK", level=level, requires_human=True,
                               reason="human_approval_required")

        return GateOutcome(decision="PERMIT", level=level, reason="permitted")
