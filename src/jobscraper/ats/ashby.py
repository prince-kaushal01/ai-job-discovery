"""Ashby ATS adapter — public job board posting API, no key required.

API: https://api.ashbyhq.com/posting-api/job-board/{board}
"""

from __future__ import annotations

import logging

from jobscraper.http_client import HttpClient
from jobscraper.models import Job

logger = logging.getLogger(__name__)


def fetch_jobs(client: HttpClient, identifier: str, company_name: str) -> list[Job]:
    url = f"https://api.ashbyhq.com/posting-api/job-board/{identifier}"
    try:
        resp = client.get(url)
        if resp.status_code != 200:
            logger.warning("Ashby %s: HTTP %s", identifier, resp.status_code)
            return []
        data = resp.json()
    except Exception:
        logger.warning("Ashby fetch failed for %s", identifier, exc_info=True)
        return []

    jobs: list[Job] = []
    for item in data.get("jobs", []):
        title = (item.get("title") or "").strip()
        if not title:
            continue
        location = item.get("location", "") or ""
        is_remote = bool(item.get("isRemote"))

        jobs.append(
            Job(
                company_name=company_name,
                title=title,
                apply_url=item.get("jobUrl", ""),
                source="company_ats",
                location=location,
                remote=is_remote or "remote" in location.lower(),
                ats_platform="ashby",
                posted_date=item.get("publishedAt"),
                description=item.get("descriptionHtml", "") or "",
            )
        )
    return jobs
