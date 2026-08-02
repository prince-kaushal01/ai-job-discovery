"""Fallback parser for companies whose career page isn't backed by one of the
supported ATS providers. Best-effort only: it looks for anchor tags whose
link text plausibly names one of our target roles, and resolves relative
"apply" links against the base page. This intentionally has lower precision
than a dedicated ATS adapter — that's the tradeoff for supporting the long
tail of custom/JS-rendered career pages without a browser.
"""

from __future__ import annotations

import logging
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from jobscraper.http_client import HttpClient
from jobscraper.models import Job

logger = logging.getLogger(__name__)


def fetch_jobs(
    client: HttpClient,
    career_url: str,
    company_name: str,
    role_keywords: list[str],
) -> list[Job]:
    try:
        resp = client.get(career_url)
        if resp.status_code != 200:
            logger.warning("Generic HTML %s: HTTP %s", career_url, resp.status_code)
            return []
        soup = BeautifulSoup(resp.text, "lxml")
    except Exception:
        logger.warning("Generic HTML fetch failed for %s", career_url, exc_info=True)
        return []

    keywords_lower = [k.lower() for k in role_keywords]
    jobs: list[Job] = []
    seen_urls: set[str] = set()

    for link in soup.find_all("a", href=True):
        text = link.get_text(strip=True)
        if not text or len(text) > 120:
            continue

        text_lower = text.lower()
        if not any(kw in text_lower for kw in keywords_lower):
            continue

        href = link["href"]
        full_url = urljoin(career_url, href)
        if full_url in seen_urls:
            continue
        seen_urls.add(full_url)

        jobs.append(
            Job(
                company_name=company_name,
                title=text,
                apply_url=full_url,
                source="company_ats",
                location="",
                remote="remote" in text_lower,
                ats_platform="generic",
                posted_date=None,
                description="",
            )
        )

    return jobs
