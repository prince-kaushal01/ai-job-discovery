"""BambooHR ATS adapter — public careers list JSON endpoint, no key required.

Endpoint: https://{company}.bamboohr.com/careers/list
"""

from __future__ import annotations

import logging

from jobscraper.http_client import HttpClient
from jobscraper.models import Job

logger = logging.getLogger(__name__)


def fetch_jobs(client: HttpClient, identifier: str, company_name: str) -> list[Job]:
    url = f"https://{identifier}.bamboohr.com/careers/list"
    try:
        resp = client.get(url, headers={"Accept": "application/json"})
        if resp.status_code != 200:
            logger.warning("BambooHR %s: HTTP %s", identifier, resp.status_code)
            return []
        data = resp.json()
    except Exception:
        logger.warning("BambooHR fetch failed for %s", identifier, exc_info=True)
        return []

    jobs: list[Job] = []
    for item in data.get("result", []):
        title = (item.get("jobOpeningName") or "").strip()
        if not title:
            continue
        location = item.get("locationLabel", "") or ""
        job_id = item.get("id", "")

        jobs.append(
            Job(
                company_name=company_name,
                title=title,
                apply_url=f"https://{identifier}.bamboohr.com/careers/{job_id}",
                source="company_ats",
                location=location,
                remote="remote" in location.lower(),
                ats_platform="bamboohr",
                posted_date=None,
                description=item.get("departmentLabel", "") or "",
            )
        )
    return jobs
