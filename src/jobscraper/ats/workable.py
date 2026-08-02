"""Workable ATS adapter — public widget API, no key required.

API: https://apply.workable.com/api/v1/widget/accounts/{account_slug}
"""

from __future__ import annotations

import logging

from jobscraper.http_client import HttpClient
from jobscraper.models import Job

logger = logging.getLogger(__name__)


def fetch_jobs(client: HttpClient, identifier: str, company_name: str) -> list[Job]:
    url = f"https://apply.workable.com/api/v1/widget/accounts/{identifier}"
    try:
        resp = client.get(url)
        if resp.status_code != 200:
            logger.warning("Workable %s: HTTP %s", identifier, resp.status_code)
            return []
        data = resp.json()
    except Exception:
        logger.warning("Workable fetch failed for %s", identifier, exc_info=True)
        return []

    jobs: list[Job] = []
    for item in data.get("jobs", []):
        title = (item.get("title") or "").strip()
        if not title:
            continue

        city = item.get("city", "") or ""
        country = item.get("country", "") or ""
        location = ", ".join(p for p in (city, country) if p)

        jobs.append(
            Job(
                company_name=company_name,
                title=title,
                apply_url=item.get("url", "") or item.get("shortlink", ""),
                source="company_ats",
                location=location,
                remote=bool(item.get("telecommuting")),
                ats_platform="workable",
                posted_date=item.get("published_on"),
                description=item.get("description", "") or "",
            )
        )
    return jobs
