"""Common interface every global job source implements.

Each source module exposes a single module-level function:

    fetch_jobs(client: HttpClient) -> list[Job]

Sources must never raise; on failure they log a warning and return [].
"""

from __future__ import annotations

from typing import Protocol

from jobscraper.http_client import HttpClient
from jobscraper.models import Job


class JobSource(Protocol):
    def __call__(self, client: HttpClient) -> list[Job]: ...
