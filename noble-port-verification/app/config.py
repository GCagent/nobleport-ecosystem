from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    helius_api_key: str = ""
    birdeye_api_key: str = ""
    solscan_api_key: str = ""

    database_url: str = "postgresql://noble:noble@postgres:5432/noble"
    redis_url: str = "redis://redis:6379/0"

    provider_timeout_s: float = 3.0
    rate_limit_per_min: int = 60

    breaker_fail_threshold: int = 5
    breaker_reset_s: int = 30

    evidence_dir: str = "/var/lib/noble-port/evidence"
    evidence_max_bytes: int = 25 * 1024 * 1024  # 25 MiB
    evidence_allowed_mime: str = "image/png,image/jpeg,image/webp,application/pdf,text/plain"

    log_level: str = "INFO"


settings = Settings()
