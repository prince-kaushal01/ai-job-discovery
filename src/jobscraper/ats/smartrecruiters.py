"""SmartRecruiters ATS adapter — public postings API, no key required.

API: https://api.smartrecruiters.com/v1/companies/{company}/postings
"""

from __future__ import annotations

import logging

from jobscraper.http_client import HttpClient
from jobscraper.models import Job

logger = logging.getLogger(__name__)


def fetch_jobs(client: HttpClient, identifier: str, company_name: str) -> list[Job]:
    url = f"https://api.smartrecruiters.com/v1/companies/{identifier}/postings"
    try:
        resp = client.get(url)
        if resp.status_code != 200:
            logger.warning("SmartRecruiters %s: HTTP %s", identifier, resp.status_code)
            return []
        data = resp.json()
    except Exception:
        logger.warning("SmartRecruiters fetch failed for %s", identifier, exc_info=True)
        return []

    jobs: list[Job] = []
    for item in data.get("content", []):
        title = (item.get("name") or "").strip()
        if not title:
            continue
        location_info = item.get("location") or {}
        city = location_info.get("city", "") or ""
        country = location_info.get("country", "") or ""
        location = ", ".join(p for p in (city, country) if p)
        is_remote = bool(location_info.get("remote"))
        posting_id = item.get("id", "")

        jobs.append(
            Job(
                company_name=company_name,
                title=title,
                apply_url=f"https://jobs.smartrecruiters.com/{identifier}/{posting_id}",
                source="company_ats",
                location=location,
                remote=is_remote,
                ats_platform="smartrecruiters",
                posted_date=item.get("releasedDate"),
                description="",
            )
        )
    return jobs
