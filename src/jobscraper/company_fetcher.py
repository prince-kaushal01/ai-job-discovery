"""Per-company fetch orchestration: fetch the career page, sniff for an ATS,
dispatch to the matching adapter, or fall back to generic HTML parsing.

One bad company must never abort the run — every exception is caught here
and turned into an empty result + logged status.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from jobscraper.ats import (
    ashby,
    bamboohr,
    generic_html,
    greenhouse,
    lever,
    oracle_recruiting,
    recruitee,
    smartrecruiters,
    teamtailor,
    workable,
    workday,
)
from jobscraper.ats.detect import detect_ats
from jobscraper.http_client import HttpClient
from jobscraper.models import Company, Job

logger = logging.getLogger(__name__)

_ADAPTERS = {
    "greenhouse": greenhouse.fetch_jobs,
    "lever": lever.fetch_jobs,
    "ashby": ashby.fetch_jobs,
    "workday": workday.fetch_jobs,
    "smartrecruiters": smartrecruiters.fetch_jobs,
    "teamtailor": teamtailor.fetch_jobs,
    "bamboohr": bamboohr.fetch_jobs,
    "workable": workable.fetch_jobs,
    "recruitee": recruitee.fetch_jobs,
    "oracle_recruiting": oracle_recruiting.fetch_jobs,
}


@dataclass
class CompanyFetchResult:
    company_name: str
    jobs: list[Job]
    ats_provider: str | None
    ats_identifier: str | None
    status: str  # "ok" | "ok:cached" | "ok:generic" | "error: ..."


def fetch_company_jobs(
    client: HttpClient, company: Company, role_keywords: list[str]
) -> CompanyFetchResult:
    """If data/companies.csv already has a known ATS + identifier for this
    company (from scripts/detect_ats.py), call that adapter directly and
    skip fetching the company's own career page entirely — that page is
    where most bot-blocking happens, while ATS provider APIs rarely block.

    Adapters already catch their own request/parse errors and return []
    rather than raise (see ats/base.py), so a stale cached identifier
    (company migrated ATS since last detected) won't surface as an
    exception here — it'll just quietly yield 0 jobs. Re-run
    scripts/detect_ats.py periodically to catch that. The try/except below
    is defense-in-depth for genuine bugs, not a staleness detector.
    """
    if company.ats_provider and company.ats_identifier:
        adapter = _ADAPTERS.get(company.ats_provider)
        if adapter is not None:
            try:
                jobs = adapter(client, company.ats_identifier, company.name)
                return CompanyFetchResult(
                    company.name, jobs, company.ats_provider, company.ats_identifier, "ok:cached"
                )
            except Exception as exc:
                logger.warning(
                    "Cached %s adapter failed for %s (%s), falling back to re-detection: %s",
                    company.ats_provider,
                    company.name,
                    exc.__class__.__name__,
                    exc,
                )

    return _detect_and_fetch(client, company, role_keywords)


def _detect_and_fetch(
    client: HttpClient, company: Company, role_keywords: list[str]
) -> CompanyFetchResult:
    try:
        resp = client.get(company.career_page)
    except Exception as exc:
        logger.warning("Career page fetch failed for %s: %s", company.name, exc)
        return CompanyFetchResult(company.name, [], None, None, f"error: {exc}")

    if not resp.ok:
        status = f"error: HTTP {resp.status_code}"
        logger.warning("%s: %s", company.name, status)
        return CompanyFetchResult(company.name, [], None, None, status)

    detection = detect_ats(resp.text, resp.url)

    if detection is not None:
        adapter = _ADAPTERS.get(detection.provider)
        if adapter is not None:
            try:
                jobs = adapter(client, detection.identifier, company.name)
                return CompanyFetchResult(
                    company.name, jobs, detection.provider, detection.identifier, "ok"
                )
            except Exception as exc:
                logger.warning(
                    "%s adapter failed for %s: %s", detection.provider, company.name, exc
                )
                return CompanyFetchResult(
                    company.name, [], detection.provider, detection.identifier, f"error: {exc}"
                )

    # No supported ATS detected -> generic HTML fallback.
    try:
        jobs = generic_html.fetch_jobs(client, company.career_page, company.name, role_keywords)
        return CompanyFetchResult(company.name, jobs, "generic", None, "ok:generic")
    except Exception as exc:
        logger.warning("Generic fallback failed for %s: %s", company.name, exc)
        return CompanyFetchResult(company.name, [], "generic", None, f"error: {exc}")
