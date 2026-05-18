"""Heuristic moderation stub.

Pluggable interface: anything implementing `moderate(text) -> Verdict`.
Swap the heuristic backend for a real model later without touching callers.
"""
from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from typing import Protocol


# Conservative, intentionally small wordlists. Real deployments should
# load these from config or a managed list service.
_PROFANITY = {"damn", "shit", "fuck", "asshole", "bitch", "bastard"}
_DEFAMATION = {
    "scammer", "fraudster", "thief", "crook", "criminal", "fraud",
    "rugpull", "rug pull", "ponzi", "money laundering",
}

_PII_PATTERNS = {
    "email": re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"),
    "phone": re.compile(r"\b(?:\+?\d{1,3}[-.\s]?)?(?:\(?\d{3}\)?[-.\s]?){2}\d{4}\b"),
    "ssn": re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
    "sol_address": re.compile(r"\b[1-9A-HJ-NP-Za-km-z]{32,44}\b"),
}


@dataclass
class Verdict:
    label: str           # ok | flagged | block
    score: float         # 0.0–1.0 (higher = riskier)
    hits: dict           # {category: [matches...]}

    def dict(self) -> dict:
        return asdict(self)


class Moderator(Protocol):
    def moderate(self, text: str) -> Verdict: ...


class HeuristicModerator:
    """Cheap regex / wordlist scoring. No network calls."""

    def moderate(self, text: str) -> Verdict:
        if not text:
            return Verdict(label="ok", score=0.0, hits={})

        low = text.lower()
        hits: dict[str, list[str]] = {}

        prof = sorted({w for w in _PROFANITY if re.search(rf"\b{re.escape(w)}\b", low)})
        if prof:
            hits["profanity"] = prof

        defam = sorted({w for w in _DEFAMATION if w in low})
        if defam:
            hits["defamation"] = defam

        for name, pat in _PII_PATTERNS.items():
            found = pat.findall(text)
            if found:
                hits[f"pii:{name}"] = sorted(set(found))[:5]

        score = 0.0
        if "profanity" in hits:
            score += 0.2 * min(1, len(hits["profanity"]))
        if "defamation" in hits:
            score += 0.5 * min(1, len(hits["defamation"]))
        if any(k.startswith("pii:") for k in hits):
            score += 0.4
        score = min(1.0, score)

        if score >= 0.7 or "defamation" in hits:
            label = "block"
        elif score >= 0.3 or hits:
            label = "flagged"
        else:
            label = "ok"

        return Verdict(label=label, score=round(score, 3), hits=hits)


# Default singleton; tests/main can swap.
moderator: Moderator = HeuristicModerator()
