"""Workday ATS adapter — uses the (undocumented but widely relied upon)
public CXS search endpoint that Workday's own career site JS calls.

`identifier` (from detect.py) has the form:
    "{tenant}.{wd_host}.myworkdayjobs.com/{site}"
e.g. "nvidia.wd5.myworkdayjobs.com/NVIDIAExternalCareerSite"
"""

from __future__ import annotations

import logging

from jobscraper.http_client import HttpClient
from jobscraper.models import Job

logger = logging.getLogger(__name__)


def fetch_jobs(client: HttpClient, identifier: str, company_name: str) -> list[Job]:
    try:
        host_part, site = identifier.split("/", 1)
        tenant = host_part.split(".")[0]
    except ValueError:
        logger.warning("Workday: malformed identifier %r", identifier)
        return []

    base = f"https://{host_part}"
    api_url = f"{base}/wday/cxs/{tenant}/{site}/jobs"

    try:
        resp = client.post(
            api_url,
            json={"appliedFacets": {}, "limit": 20, "offset": 0, "searchText": ""},
            headers={"Content-Type": "application/json"},
        )
        if resp.status_code != 200:
            logger.warning("Workday %s: HTTP %s", identifier, resp.status_code)
            return []
        data = resp.json()
    except Exception:
        logger.warning("Workday fetch failed for %s", identifier, exc_info=True)
        return []

    jobs: list[Job] = []
    for item in data.get("jobPostings", []):
        title = (item.get("title") or "").strip()
        if not title:
            continue
        location = item.get("locationsText", "") or ""
        external_path = item.get("externalPath", "") or ""

        jobs.append(
            Job(
                company_name=company_name,
                title=title,
                apply_url=f"{base}/en-US/{site}{external_path}",
                source="company_ats",
                location=location,
                remote="remote" in location.lower(),
                ats_platform="workday",
                posted_date=item.get("postedOn"),
                description="",
            )
        )
    return jobs
