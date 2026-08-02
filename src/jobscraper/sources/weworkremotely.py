"""We Work Remotely — public RSS feed, no key required.

WWR entry titles are formatted as "Company: Job Title"; we split on the
first colon to recover both fields. All WWR listings are remote by design.
"""

from __future__ import annotations

import logging

import feedparser

from jobscraper.http_client import HttpClient
from jobscraper.models import Job

logger = logging.getLogger(__name__)

_DEFAULT_FEED_URL = "https://weworkremotely.com/categories/remote-programming-jobs.rss"


def fetch_jobs(client: HttpClient, feed_url: str = _DEFAULT_FEED_URL) -> list[Job]:
    try:
        resp = client.get(feed_url)
        if resp.status_code != 200:
            logger.warning("WeWorkRemotely: HTTP %s", resp.status_code)
            return []
        parsed = feedparser.parse(resp.content)
    except Exception:
        logger.warning("WeWorkRemotely fetch failed", exc_info=True)
        return []

    jobs: list[Job] = []
    for entry in parsed.entries:
        raw_title = (entry.get("title") or "").strip()
        if not raw_title:
            continue

        if ":" in raw_title:
            company, _, title = raw_title.partition(":")
            company, title = company.strip(), title.strip()
        else:
            company, title = "Unknown", raw_title

        jobs.append(
            Job(
                company_name=company,
                title=title,
                apply_url=entry.get("link", ""),
                source="weworkremotely",
                location="Remote",
                remote=True,
                ats_platform=None,
                posted_date=entry.get("published"),
                description=entry.get("summary", "") or "",
            )
        )
    return jobs
