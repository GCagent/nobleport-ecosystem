"""Provider-neutral voice output for Stephanie.ai.

The first implementation targets the local Voicebox REST API. Voice output is
opt-in and fail-open: if Voicebox is disabled or unavailable, Stephanie's text
WebSocket response still works.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

import httpx


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _env_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        value = float(raw)
    except ValueError:
        return default
    return value if value > 0 else default


@dataclass(frozen=True)
class VoiceSettings:
    enabled: bool
    base_url: str
    profile: str | None
    client_id: str
    personality: bool
    timeout_seconds: float

    @classmethod
    def from_env(cls) -> "VoiceSettings":
        profile = os.getenv("VOICEBOX_PROFILE", "").strip() or None
        return cls(
            enabled=_env_bool("STEPHANIE_VOICE_ENABLED", False),
            base_url=os.getenv("VOICEBOX_URL", "http://127.0.0.1:17493").rstrip("/"),
            profile=profile,
            client_id=os.getenv("VOICEBOX_CLIENT_ID", "stephanie-ai").strip() or "stephanie-ai",
            personality=_env_bool("VOICEBOX_PERSONALITY", False),
            timeout_seconds=_env_float("VOICEBOX_TIMEOUT_SECONDS", 10.0),
        )


class VoiceboxSpeaker:
    """Thin async adapter for Voicebox ``POST /speak``.

    The adapter deliberately does not own voice cloning, profile creation, or
    recording. Those operations require separate consent and asset-management
    workflows. This surface only speaks text through an already configured
    Voicebox profile/default binding.
    """

    provider = "voicebox"

    def __init__(self, settings: VoiceSettings | None = None) -> None:
        self.settings = settings or VoiceSettings.from_env()

    @property
    def enabled(self) -> bool:
        return self.settings.enabled

    def summary(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "enabled": self.enabled,
            "profile_configured": self.settings.profile is not None,
        }

    async def status(self) -> dict[str, Any]:
        if not self.enabled:
            return {**self.summary(), "reachable": False, "status": "disabled"}

        try:
            async with httpx.AsyncClient(timeout=self.settings.timeout_seconds) as client:
                response = await client.get(f"{self.settings.base_url}/health")
                response.raise_for_status()
            return {**self.summary(), "reachable": True, "status": "ok"}
        except (httpx.HTTPError, ValueError) as exc:
            return {
                **self.summary(),
                "reachable": False,
                "status": "unavailable",
                "error": type(exc).__name__,
            }

    async def speak(self, text: str) -> dict[str, Any]:
        text = text.strip()
        if not text:
            return {**self.summary(), "spoken": False, "reason": "empty_text"}
        if not self.enabled:
            return {**self.summary(), "spoken": False, "reason": "disabled"}

        payload: dict[str, Any] = {
            "text": text,
            "personality": self.settings.personality,
        }
        if self.settings.profile:
            payload["profile"] = self.settings.profile

        headers = {"X-Voicebox-Client-Id": self.settings.client_id}
        try:
            async with httpx.AsyncClient(timeout=self.settings.timeout_seconds) as client:
                response = await client.post(
                    f"{self.settings.base_url}/speak",
                    json=payload,
                    headers=headers,
                )
                response.raise_for_status()
            return {**self.summary(), "spoken": True, "status": "accepted"}
        except (httpx.HTTPError, ValueError) as exc:
            return {
                **self.summary(),
                "spoken": False,
                "status": "unavailable",
                "error": type(exc).__name__,
            }
