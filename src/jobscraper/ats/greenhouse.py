"""Greenhouse ATS adapter — public Job Board API, no key required.

API docs: https://developers.greenhouse.io/job-board.html
"""

from __future__ import annotations

import logging

from jobscraper.http_client import HttpClient
from jobscraper.models import Job

logger = logging.getLogger(__name__)


def fetch_jobs(client: HttpClient, identifier: str, company_name: str) -> list[Job]:
    url = f"https://boards-api.greenhouse.io/v1/boards/{identifier}/jobs?content=true"
    try:
        resp = client.get(url)
        if resp.status_code != 200:
            logger.warning("Greenhouse %s: HTTP %s", identifier, resp.status_code)
            return []
        data = resp.json()
    except Exception:
        logger.warning("Greenhouse fetch failed for %s", identifier, exc_info=True)
        return []

    jobs: list[Job] = []
    for item in data.get("jobs", []):
        title = item.get("title", "").strip()
        if not title:
            continue
        location = (item.get("location") or {}).get("name", "") or ""
        jobs.append(
            Job(
                company_name=company_name,
                title=title,
                apply_url=item.get("absolute_url", ""),
                source="company_ats",
                location=location,
                remote="remote" in location.lower(),
                ats_platform="greenhouse",
                posted_date=item.get("updated_at"),
                description=item.get("content", "") or "",
            )
        )
    return jobs
