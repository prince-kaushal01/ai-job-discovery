"""Teamtailor ATS adapter.

Teamtailor doesn't offer a no-key public JSON API for arbitrary boards, so
this adapter parses the public jobs listing page's HTML directly (its
markup is far more consistent than an arbitrary company site, which is why
it gets its own adapter rather than going through generic_html.py).
"""

from __future__ import annotations

import logging
import re

from bs4 import BeautifulSoup

from jobscraper.http_client import HttpClient
from jobscraper.models import Job

logger = logging.getLogger(__name__)

_JOB_LINK_RE = re.compile(r"/jobs/\d+")


def fetch_jobs(client: HttpClient, identifier: str, company_name: str) -> list[Job]:
    url = f"https://{identifier}.teamtailor.com/jobs"
    try:
        resp = client.get(url)
        if resp.status_code != 200:
            logger.warning("Teamtailor %s: HTTP %s", identifier, resp.status_code)
            return []
        soup = BeautifulSoup(resp.text, "lxml")
    except Exception:
        logger.warning("Teamtailor fetch failed for %s", identifier, exc_info=True)
        return []

    jobs: list[Job] = []
    seen_urls: set[str] = set()

    for link in soup.find_all("a", href=_JOB_LINK_RE):
        href = link.get("href", "")
        if not href:
            continue
        full_url = href if href.startswith("http") else f"https://{identifier}.teamtailor.com{href}"
        if full_url in seen_urls:
            continue
        seen_urls.add(full_url)

        title = link.get_text(strip=True)
        if not title:
            continue

        jobs.append(
            Job(
                company_name=company_name,
                title=title,
                apply_url=full_url,
                source="company_ats",
                location="",
                remote="remote" in title.lower(),
                ats_platform="teamtailor",
                posted_date=None,
                description="",
            )
        )
    return jobs
