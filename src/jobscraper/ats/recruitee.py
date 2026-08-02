"""Recruitee (Tellent) ATS adapter — public offers API, no key required.

API: https://{company}.recruitee.com/api/offers/
"""

from __future__ import annotations

import logging

from jobscraper.http_client import HttpClient
from jobscraper.models import Job

logger = logging.getLogger(__name__)


def fetch_jobs(client: HttpClient, identifier: str, company_name: str) -> list[Job]:
    url = f"https://{identifier}.recruitee.com/api/offers/"
    try:
        resp = client.get(url)
        if resp.status_code != 200:
            logger.warning("Recruitee %s: HTTP %s", identifier, resp.status_code)
            return []
        data = resp.json()
    except Exception:
        logger.warning("Recruitee fetch failed for %s", identifier, exc_info=True)
        return []

    jobs: list[Job] = []
    for item in data.get("offers", []):
        title = (item.get("title") or "").strip()
        if not title:
            continue

        jobs.append(
            Job(
                company_name=company_name,
                title=title,
                apply_url=item.get("careers_apply_url", "") or item.get("careers_url", ""),
                source="company_ats",
                location=item.get("location", "") or "",
                remote=bool(item.get("remote")),
                ats_platform="recruitee",
                posted_date=item.get("published_at"),
                description=item.get("sharing_description", "") or "",
            )
        )
    return jobs
