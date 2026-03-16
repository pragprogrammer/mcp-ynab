import sys
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def _default_db_path() -> str:
    """Platform-appropriate default cache DB path."""
    if sys.platform == "win32":
        base = Path.home() / "AppData" / "Local" / "ynab-mcp-server"
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support" / "ynab-mcp-server"
    else:
        base = Path.home() / ".local" / "share" / "ynab-mcp-server"
    base.mkdir(parents=True, exist_ok=True)
    return str(base / "cache.db")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env.local",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    ynab_api_key: str = Field(alias="YNAB_API_KEY")
    cache_db_path: str = Field(default_factory=_default_db_path)
    http_timeout: float = 30.0

    # TTL for non-delta endpoints (seconds)
    ttl_budgets: int = 300
    ttl_scheduled_transactions: int = 300
    ttl_month_detail: int = 120
    ttl_single_entity: int = 60

    # Delta sync
    delta_min_interval: int = 30

    # Retry
    retry_max_attempts: int = 3
    retry_base_delay: float = 1.0
    retry_max_delay: float = 30.0
