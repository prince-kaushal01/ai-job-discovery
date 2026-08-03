"""RemoteOK public JSON API — no key required.

https://remoteok.com/api returns a JSON array whose first element is a
legal/metadata notice (no "id" field), followed by job postings.

RemoteOK lists remote jobs across every discipline, so a light tag/title
pre-filter keeps volume sane before the shared filtering.py pass runs
(which enforces the real include/exclude role rules).
"""

from __future__ import annotations

import logging
from datetime import datetime

from jobscraper.http_client import HttpClient
from jobscraper.models import Job
from jobscraper.sources.date_utils import is_within_window

logger = logging.getLogger(__name__)

_AI_ML_HINTS = {
    "ai", "ml", "machine-learning", "artificial-intelligence", "nlp",
    "llm", "genai", "data-science", "deep-learning",
}


def fetch_jobs(
    client: HttpClient,
    api_url: str = "https://remoteok.com/api",
    since: datetime | None = None,
) -> list[Job]:
    try:
        resp = client.get(api_url)
        if resp.status_code != 200:
            logger.warning("RemoteOK: HTTP %s", resp.status_code)
            return []
        data = resp.json()
    except Exception:
        logger.warning("RemoteOK fetch failed", exc_info=True)
        return []

    jobs: list[Job] = []
    for item in data:
        if "id" not in item:
            continue  # first element is a legal notice, not a job

        title = (item.get("position") or "").strip()
        if not title:
            continue

        tags = {t.lower() for t in (item.get("tags") or [])}
        if not (tags & _AI_ML_HINTS) and not any(h in title.lower() for h in _AI_ML_HINTS):
            continue

        if not is_within_window(item.get("date"), since):
            continue

        company = (item.get("company") or "").strip()
        location = item.get("location", "") or ""

        jobs.append(
            Job(
                company_name=company,
                title=title,
                apply_url=item.get("url", "") or item.get("apply_url", ""),
                source="remoteok",
                location=location,
                remote=True,
                ats_platform=None,
                posted_date=item.get("date"),
                description=item.get("description", "") or "",
            )
        )
    return jobs
