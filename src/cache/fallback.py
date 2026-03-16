import asyncio
import logging
from collections.abc import Callable, Coroutine
from typing import Any

import httpx

from src.ynab_client import YNABError

logger = logging.getLogger(__name__)


def _is_retryable(exc: Exception) -> bool:
    if isinstance(exc, httpx.RequestError):
        return True
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code in (429, 500, 502, 503, 504)
    if isinstance(exc, YNABError):
        return exc.status_code in (429, 500, 502, 503, 504)
    return False


class RetryWithFallback:
    def __init__(self, max_attempts: int = 3, base_delay: float = 1.0, max_delay: float = 30.0):
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.max_delay = max_delay

    async def execute(
        self,
        api_call: Callable[[], Coroutine[Any, Any, Any]],
        cache_key: str | None = None,
    ) -> Any:
        last_exc: Exception | None = None

        for attempt in range(self.max_attempts):
            try:
                return await api_call()
            except Exception as exc:
                last_exc = exc
                if not _is_retryable(exc):
                    raise
                if attempt < self.max_attempts - 1:
                    delay = min(self.base_delay * (2 ** attempt), self.max_delay)
                    logger.warning(f"Retry {attempt + 1}/{self.max_attempts} after {delay}s: {exc}")
                    await asyncio.sleep(delay)

        raise last_exc  # type: ignore[misc]
