"""Jobicy — free public JSON API, no key required.

https://github.com/Jobicy/remote-jobs-api

Uses the "Data Science & Analytics" industry filter (verified: real,
working server-side filtering, unlike Remotive's currently-broken query
params) rather than paging through the unfiltered feed and matching
client-side.
"""

from __future__ import annotations

import logging

from jobscraper.http_client import HttpClient
from jobscraper.models import Job

logger = logging.getLogger(__name__)

_API_URL = "https://jobicy.com/api/v2/remote-jobs"


def fetch_jobs(client: HttpClient, industry: str = "data-science", count: int = 50) -> list[Job]:
    try:
        resp = client.get(_API_URL, params={"count": count, "industry": industry})
        if resp.status_code != 200:
            logger.warning("Jobicy: HTTP %s", resp.status_code)
            return []
        data = resp.json()
    except Exception:
        logger.warning("Jobicy fetch failed", exc_info=True)
        return []

    jobs: list[Job] = []
    for item in data.get("jobs", []):
        title = (item.get("jobTitle") or "").strip()
        if not title:
            continue

        jobs.append(
            Job(
                company_name=(item.get("companyName") or "").strip(),
                title=title,
                apply_url=item.get("url", ""),
                source="jobicy",
                location=item.get("jobGeo", "") or "",
                remote=True,
                ats_platform=None,
                posted_date=item.get("pubDate"),
                description=item.get("jobExcerpt", "") or "",
            )
        )
    return jobs
