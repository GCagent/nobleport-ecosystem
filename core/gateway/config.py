from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


# core/config/launch-gates.json — reused as the single source of truth for
# prohibited claims, RED-gate scopes, and NY geo-blocks.
_DEFAULT_LAUNCH_GATES = str(
    (Path(__file__).resolve().parent.parent / "config" / "launch-gates.json")
)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql://noble:noble@postgres:5432/noble"
    redis_url: str = "redis://redis:6379/0"

    launch_gates_path: str = _DEFAULT_LAUNCH_GATES

    # Governance
    max_message_chars: int = 2000
    rate_limit_per_min: int = 20
    cache_ttl_s: int = 60

    # KPI snapshot worker
    kpi_interval_s: int = 600          # 5-15 min cadence
    enable_kpi_worker: bool = True

    # Tool execution
    tool_timeout_s: float = 10.0
    use_http_executor: bool = False    # default to STAGED stub executor

    # Admin (kill switch / privileged endpoints)
    admin_token: str = ""

    log_level: str = "INFO"


settings = Settings()
