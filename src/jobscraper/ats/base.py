"""Common interface every ATS adapter implements.

Each adapter module exposes a single module-level function:

    fetch_jobs(client: HttpClient, identifier: str, company_name: str) -> list[Job]

`identifier` is whatever `detect.py` extracted from the company's career page
(a board token, company slug, subdomain, etc.) — adapter-specific.
Adapters must never raise; on any failure they log a warning and return [].
"""

from __future__ import annotations

from typing import Protocol

from jobscraper.http_client import HttpClient
from jobscraper.models import Job


class ATSAdapter(Protocol):
    def __call__(
        self, client: HttpClient, identifier: str, company_name: str
    ) -> list[Job]: ...
