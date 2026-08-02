"""Shared HTTP client: timeouts, retries with backoff, and per-host rate limiting.

One instance is shared across the whole pipeline run so the per-host rate
limit is actually enforced across all callers, not just within one adapter.
"""

from __future__ import annotations

import logging
import threading
import time
from urllib.parse import urlparse

import requests
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

logger = logging.getLogger(__name__)


class RateLimiter:
    """Simple per-host minimum-interval rate limiter, thread-safe."""

    def __init__(self, min_interval_seconds: float) -> None:
        self._min_interval = min_interval_seconds
        self._lock = threading.Lock()
        self._last_call: dict[str, float] = {}

    def wait(self, host: str) -> None:
        with self._lock:
            now = time.monotonic()
            last = self._last_call.get(host, 0.0)
            elapsed = now - last
            sleep_for = self._min_interval - elapsed
            if sleep_for > 0:
                time.sleep(sleep_for)
            self._last_call[host] = time.monotonic()


class HttpClient:
    def __init__(
        self,
        timeout_seconds: int = 15,
        max_retries: int = 3,
        backoff_seconds: int = 2,
        rate_limit_per_host_seconds: float = 1.0,
        user_agent: str = (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        ),
    ) -> None:
        self.timeout_seconds = timeout_seconds
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": user_agent,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
            }
        )
        self._rate_limiter = RateLimiter(rate_limit_per_host_seconds)
        self._max_retries = max_retries
        self._backoff_seconds = backoff_seconds

    def get(self, url: str, **kwargs) -> requests.Response:
        return self._request("get", url, **kwargs)

    def post(self, url: str, **kwargs) -> requests.Response:
        return self._request("post", url, **kwargs)

    def _request(self, method: str, url: str, **kwargs) -> requests.Response:
        host = urlparse(url).netloc

        @retry(
            reraise=True,
            stop=stop_after_attempt(self._max_retries),
            wait=wait_exponential(multiplier=self._backoff_seconds, min=1, max=30),
            retry=retry_if_exception_type(
                (requests.ConnectionError, requests.Timeout, requests.HTTPError)
            ),
        )
        def _do_request() -> requests.Response:
            self._rate_limiter.wait(host)
            resp = self.session.request(method, url, timeout=self.timeout_seconds, **kwargs)
            if resp.status_code == 429:
                retry_after = resp.headers.get("Retry-After")
                if retry_after and retry_after.isdigit():
                    time.sleep(min(int(retry_after), 30))
                resp.raise_for_status()
            elif resp.status_code >= 500:
                resp.raise_for_status()
            return resp

        return _do_request()
