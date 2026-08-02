"""Lever ATS adapter — public postings API, no key required.

API: https://api.lever.co/v0/postings/{company}?mode=json
"""

from __future__ import annotations

import logging

from jobscraper.http_client import HttpClient
from jobscraper.models import Job

logger = logging.getLogger(__name__)


def fetch_jobs(client: HttpClient, identifier: str, company_name: str) -> list[Job]:
    url = f"https://api.lever.co/v0/postings/{identifier}?mode=json"
    try:
        resp = client.get(url)
        if resp.status_code != 200:
            logger.warning("Lever %s: HTTP %s", identifier, resp.status_code)
            return []
        data = resp.json()
    except Exception:
        logger.warning("Lever fetch failed for %s", identifier, exc_info=True)
        return []

    jobs: list[Job] = []
    for item in data:
        title = (item.get("text") or "").strip()
        if not title:
            continue
        categories = item.get("categories") or {}
        location = categories.get("location", "") or ""
        commitment = categories.get("commitment", "") or ""
        posted_ms = item.get("createdAt")
        posted_date = str(posted_ms) if posted_ms else None

        jobs.append(
            Job(
                company_name=company_name,
                title=title,
                apply_url=item.get("hostedUrl", ""),
                source="company_ats",
                location=location,
                remote="remote" in location.lower() or "remote" in commitment.lower(),
                ats_platform="lever",
                posted_date=posted_date,
                description=item.get("descriptionPlain", "") or "",
            )
        )
    return jobs
