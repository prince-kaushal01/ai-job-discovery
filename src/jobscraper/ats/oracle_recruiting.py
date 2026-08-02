"""Oracle Recruiting Cloud (Fusion HCM) adapter — public candidate-experience
REST API, no key required. Every tenant hosts its own Fusion Applications
instance, so `identifier` (from detect.py) has the form:
    "{api_host}|{site_number}"
e.g. "eeho.fa.us2.oraclecloud.com|CX_45001"
"""

from __future__ import annotations

import logging

from jobscraper.http_client import HttpClient
from jobscraper.models import Job

logger = logging.getLogger(__name__)


def fetch_jobs(client: HttpClient, identifier: str, company_name: str) -> list[Job]:
    try:
        api_host, site_number = identifier.split("|", 1)
    except ValueError:
        logger.warning("Oracle Recruiting: malformed identifier %r", identifier)
        return []

    url = (
        f"https://{api_host}/hcmRestApi/resources/latest/recruitingCEJobRequisitions"
        f"?onlyData=true&expand=requisitionList&finder=findReqs;siteNumber={site_number},limit=50"
    )
    try:
        resp = client.get(url, headers={"Accept": "application/json"})
        if resp.status_code != 200:
            logger.warning("Oracle Recruiting %s: HTTP %s", identifier, resp.status_code)
            return []
        data = resp.json()
    except Exception:
        logger.warning("Oracle Recruiting fetch failed for %s", identifier, exc_info=True)
        return []

    jobs: list[Job] = []
    items = data.get("items") or []
    requisitions = items[0].get("requisitionList", []) if items else []

    for req in requisitions:
        title = (req.get("Title") or "").strip()
        if not title:
            continue
        req_id = req.get("Id", "")
        location = req.get("PrimaryLocation", "") or ""
        workplace_type = (req.get("WorkplaceType") or "").lower()

        jobs.append(
            Job(
                company_name=company_name,
                title=title,
                apply_url=f"https://{api_host}/hcmUI/CandidateExperience/en/sites/{site_number}/job/{req_id}",
                source="company_ats",
                location=location,
                remote="remote" in workplace_type or "remote" in location.lower(),
                ats_platform="oracle_recruiting",
                posted_date=req.get("PostedDate"),
                description=req.get("ShortDescriptionStr", "") or "",
            )
        )
    return jobs
