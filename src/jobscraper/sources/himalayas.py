"""Himalayas — free public JSON search API, no key required.

https://himalayas.app/docs/remote-jobs-api

Unlike RemoteOK's single unfiltered feed, Himalayas' /search endpoint takes a
free-text query and ranks by relevance, so we run one search per configured
role phrase (e.g. "AI Engineer", "ML Engineer") rather than paging through
its full ~95k-job feed and filtering client-side.
"""

from __future__ import annotations

import logging

from jobscraper.http_client import HttpClient
from jobscraper.models import Job

logger = logging.getLogger(__name__)

_SEARCH_URL = "https://himalayas.app/jobs/api/search"


def fetch_jobs(
    client: HttpClient, role_keywords: list[str], per_query_limit: int = 20
) -> list[Job]:
    jobs: list[Job] = []
    seen_guids: set[str] = set()

    for role in role_keywords:
        try:
            resp = client.get(
                _SEARCH_URL,
                params={"q": role, "limit": per_query_limit, "sort": "recent"},
            )
            if resp.status_code != 200:
                logger.warning("Himalayas search %r: HTTP %s", role, resp.status_code)
                continue
            data = resp.json()
        except Exception:
            logger.warning("Himalayas search %r failed", role, exc_info=True)
            continue

        for item in data.get("jobs", []):
            guid = item.get("guid", "")
            if not guid or guid in seen_guids:
                continue
            seen_guids.add(guid)

            title = (item.get("title") or "").strip()
            if not title:
                continue

            locations = item.get("locationRestrictions") or []
            location = ", ".join(locations[:3]) if locations else "Worldwide"
            posted = item.get("pubDate")

            jobs.append(
                Job(
                    company_name=(item.get("companyName") or "").strip(),
                    title=title,
                    apply_url=item.get("applicationLink", "") or guid,
                    source="himalayas",
                    location=location,
                    remote=True,
                    ats_platform=None,
                    posted_date=str(posted) if posted else None,
                    description=item.get("description", "") or item.get("excerpt", "") or "",
                )
            )

    return jobs
