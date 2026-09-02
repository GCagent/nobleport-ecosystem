from __future__ import annotations

import os
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Config:
    database_url: str = field(
        default_factory=lambda: os.environ.get(
            "DATABASE_URL", "sqlite+aiosqlite:///./contractor_intake.db"
        )
    )
    stripe_secret_key: str = field(
        default_factory=lambda: os.environ.get("STRIPE_SECRET_KEY", "")
    )
    stripe_webhook_secret: str = field(
        default_factory=lambda: os.environ.get("STRIPE_WEBHOOK_SECRET", "")
    )
    stripe_price_id: str = field(
        default_factory=lambda: os.environ.get("STRIPE_PRICE_ID", "")
    )
    mercury_api_key: str = field(
        default_factory=lambda: os.environ.get("MERCURY_API_KEY", "")
    )
    mercury_account_id: str = field(
        default_factory=lambda: os.environ.get("MERCURY_ACCOUNT_ID", "")
    )
    anthropic_api_key: str = field(
        default_factory=lambda: os.environ.get("ANTHROPIC_API_KEY", "")
    )
    app_base_url: str = field(
        default_factory=lambda: os.environ.get("APP_BASE_URL", "http://localhost:8000")
    )
    secret_key: str = field(
        default_factory=lambda: os.environ.get("SECRET_KEY", "change-me-in-production")
    )


def get_config() -> Config:
    return Config()
