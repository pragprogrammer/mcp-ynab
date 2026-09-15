import sys
from pathlib import Path

from pydantic import Field, PrivateAttr, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from src.security import credentials


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


class MissingCredentialsError(RuntimeError):
    """Raised when no YNAB token could be resolved from any permitted source."""


_ENV_DEPRECATION = (
    "WARNING: using YNAB_API_KEY from the environment. Anything that can read "
    "the MCP client's config file or this process's environment can read the "
    "token. Run `mcp-ynab auth login` to move it into the OS credential store; "
    "set YNAB_ALLOW_ENV_KEY=0 to refuse the environment variable outright."
)

_MISSING = (
    "No YNAB token found. Run `mcp-ynab auth login` to store one in the OS "
    "credential store."
)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env.local",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Resolved in _resolve_api_key below, which prefers the credential store over
    # this field. SecretStr so the token cannot land in a repr, a log line, or a
    # pydantic validation error; .get_secret_value() is called at exactly one site.
    ynab_api_key: SecretStr | None = Field(default=None, alias="YNAB_API_KEY")

    # Set to 0/false for a strict setup that accepts the credential store only.
    allow_env_key: bool = Field(default=True, alias="YNAB_ALLOW_ENV_KEY")

    cache_db_path: str = Field(default_factory=_default_db_path)
    # Off only for debugging: the cache holds payees, memos and amounts.
    cache_encryption: bool = Field(default=True, alias="YNAB_CACHE_ENCRYPTION")
    # Opt-in. Writes stay enabled by default; see mutating_tool() in _shared.py.
    read_only: bool = Field(default=False, alias="YNAB_READ_ONLY")
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

    _api_key_source: str = PrivateAttr(default="none")

    @model_validator(mode="after")
    def _resolve_api_key(self) -> "Settings":
        """Resolve the token: credential store, then environment, else fail.

        The credential store wins so that `mcp-ynab auth login` takes effect even
        when a stale YNAB_API_KEY is still sitting in an MCP client config.
        """
        stored = credentials.load_token()
        if stored:
            self.ynab_api_key = SecretStr(stored)
            self._api_key_source = "keyring"
            return self

        if self.ynab_api_key is not None:
            if not self.allow_env_key:
                raise MissingCredentialsError(
                    "YNAB_API_KEY is set but YNAB_ALLOW_ENV_KEY=0 refuses it. "
                    "Run `mcp-ynab auth login` to store the token in the OS "
                    "credential store."
                )
            # stderr, never stdout: stdout is the MCP transport.
            print(_ENV_DEPRECATION, file=sys.stderr)
            self._api_key_source = "env"
            return self

        raise MissingCredentialsError(_MISSING)

    @property
    def api_key_source(self) -> str:
        """Where the live token came from: 'keyring', 'env', or 'none'."""
        return self._api_key_source
