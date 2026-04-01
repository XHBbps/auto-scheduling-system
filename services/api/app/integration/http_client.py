import asyncio
import logging
import time
from collections.abc import Iterable

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

DEFAULT_RETRY_STATUS_CODES = frozenset({408, 429, 500, 502, 503, 504})


class ExternalHttpClient:
    def __init__(
        self,
        service_name: str,
        timeout_seconds: float | None = None,
        max_retries: int | None = None,
        retry_backoff_seconds: float | None = None,
    ):
        self.service_name = service_name
        self.timeout = timeout_seconds or settings.external_http_timeout_seconds
        self.max_retries = max_retries if max_retries is not None else settings.external_http_max_retries
        self.retry_backoff_seconds = (
            retry_backoff_seconds
            if retry_backoff_seconds is not None
            else settings.external_http_retry_backoff_seconds
        )
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=self.timeout)
        return self._client

    async def aclose(self) -> None:
        if self._client is not None and not self._client.is_closed:
            await self._client.aclose()

    async def request(
        self,
        method: str,
        url: str,
        *,
        retry_on_status_codes: Iterable[int] | None = None,
        **kwargs,
    ) -> httpx.Response:
        retry_status_codes = (
            set(DEFAULT_RETRY_STATUS_CODES)
            if retry_on_status_codes is None
            else set(retry_on_status_codes)
        )

        for attempt in range(1, self.max_retries + 2):
            started = time.perf_counter()
            try:
                client = await self._get_client()
                response = await client.request(method, url, **kwargs)
                duration_ms = round((time.perf_counter() - started) * 1000, 2)

                if response.status_code in retry_status_codes and attempt <= self.max_retries:
                    logger.warning(
                        "[%s] retryable response status=%s attempt=%s/%s duration_ms=%s method=%s url=%s",
                        self.service_name,
                        response.status_code,
                        attempt,
                        self.max_retries + 1,
                        duration_ms,
                        method.upper(),
                        url,
                    )
                    await asyncio.sleep(self._backoff(attempt))
                    continue

                if response.is_success:
                    logger.debug(
                        "[%s] request success status=%s duration_ms=%s method=%s url=%s",
                        self.service_name,
                        response.status_code,
                        duration_ms,
                        method.upper(),
                        url,
                    )
                else:
                    logger.warning(
                        "[%s] request completed with non-success status=%s duration_ms=%s method=%s url=%s",
                        self.service_name,
                        response.status_code,
                        duration_ms,
                        method.upper(),
                        url,
                    )
                return response
            except httpx.RequestError as exc:
                duration_ms = round((time.perf_counter() - started) * 1000, 2)
                if attempt <= self.max_retries:
                    logger.warning(
                        "[%s] request exception retry attempt=%s/%s duration_ms=%s method=%s url=%s error=%s",
                        self.service_name,
                        attempt,
                        self.max_retries + 1,
                        duration_ms,
                        method.upper(),
                        url,
                        repr(exc),
                    )
                    await asyncio.sleep(self._backoff(attempt))
                    continue
                logger.error(
                    "[%s] request failed after retries duration_ms=%s method=%s url=%s error=%s",
                    self.service_name,
                    duration_ms,
                    method.upper(),
                    url,
                    repr(exc),
                )
                raise

        raise RuntimeError(f"{self.service_name} request failed unexpectedly")

    def _backoff(self, attempt: int) -> float:
        return max(self.retry_backoff_seconds, 0) * (2 ** (attempt - 1))
