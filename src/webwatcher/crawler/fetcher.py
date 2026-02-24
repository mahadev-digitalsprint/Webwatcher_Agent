import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from webwatcher.core.config import get_settings
from webwatcher.security.security_utils import prevent_ssrf


@dataclass
class FetchResponse:
    url: str
    status_code: int
    content: bytes
    headers: dict[str, str]
    fetched_at: datetime

    @property
    def text(self) -> str:
        return self.content.decode("utf-8", errors="ignore")


class DomainRateLimiter:
    def __init__(self, per_minute: int) -> None:
        self._interval_seconds = max(1, int(60 / max(per_minute, 1)))
        self._last_hit: dict[str, float] = {}
        self._lock = asyncio.Lock()

    async def wait(self, domain: str) -> None:
        async with self._lock:
            loop = asyncio.get_running_loop()
            now = loop.time()
            last = self._last_hit.get(domain, 0.0)
            delay = self._interval_seconds - (now - last)
            if delay > 0:
                await asyncio.sleep(delay)
            self._last_hit[domain] = loop.time()


class Fetcher:
    def __init__(self) -> None:
        settings = get_settings()
        self.timeout = settings.webwatch_request_timeout_seconds
        self.max_retries = settings.webwatch_max_retries
        self.rate_limiter = DomainRateLimiter(settings.webwatch_rate_limit_per_domain)
        self._client = httpx.AsyncClient(
            timeout=self.timeout,
            follow_redirects=True,
            headers={"User-Agent": "webwatcher-agent/0.1"},
        )

    async def close(self) -> None:
        await self._client.aclose()

    @retry(wait=wait_exponential(min=1, max=8), stop=stop_after_attempt(3), reraise=True)
    async def _request(self, method: str, url: str, headers: dict[str, str] | None = None) -> httpx.Response:
        response = await self._client.request(method, url, headers=headers)
        response.raise_for_status()
        return response

    async def head(self, url: str) -> dict[str, Any]:
        if not prevent_ssrf(url):
            raise ValueError(f"Rejected URL by SSRF policy: {url}")
        domain = httpx.URL(url).host or ""
        await self.rate_limiter.wait(domain)
        response = await self._request("HEAD", url)
        return {
            "etag": response.headers.get("ETag"),
            "last_modified": response.headers.get("Last-Modified"),
            "content_type": response.headers.get("Content-Type"),
            "content_length": int(response.headers["Content-Length"])
            if "Content-Length" in response.headers
            else None,
            "status_code": response.status_code,
        }

    async def get(
        self,
        url: str,
        if_none_match: str | None = None,
        if_modified_since: str | None = None,
    ) -> FetchResponse:
        if not prevent_ssrf(url):
            raise ValueError(f"Rejected URL by SSRF policy: {url}")
        domain = httpx.URL(url).host or ""
        await self.rate_limiter.wait(domain)
        headers: dict[str, str] = {}
        if if_none_match:
            headers["If-None-Match"] = if_none_match
        if if_modified_since:
            headers["If-Modified-Since"] = if_modified_since
        response = await self._client.get(url, headers=headers)
        return FetchResponse(
            url=str(response.url),
            status_code=response.status_code,
            content=response.content,
            headers=dict(response.headers),
            fetched_at=datetime.now(timezone.utc),
        )

