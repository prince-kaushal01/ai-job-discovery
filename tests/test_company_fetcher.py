import json
from pathlib import Path

import responses

from jobscraper.company_fetcher import fetch_company_jobs
from jobscraper.http_client import HttpClient
from jobscraper.models import Company

FIXTURES = Path(__file__).parent / "fixtures"


@responses.activate
def test_cached_ats_skips_career_page_fetch():
    """When Company already has ats_provider/ats_identifier (from the CSV
    cache), fetch_company_jobs must call the ATS API directly and never
    touch career_page at all."""
    payload = json.loads((FIXTURES / "greenhouse_jobs.json").read_text())
    responses.add(
        responses.GET,
        "https://boards-api.greenhouse.io/v1/boards/acme/jobs",
        json=payload,
        status=200,
    )
    # No mock registered for the career page itself — if fetch_company_jobs
    # tried to fetch it, responses would raise ConnectionError.

    company = Company(
        name="Acme Inc",
        career_page="https://acme.com/careers",
        ats_provider="greenhouse",
        ats_identifier="acme",
    )
    client = HttpClient()
    result = fetch_company_jobs(client, company, role_keywords=["AI Engineer"])

    assert result.status == "ok:cached"
    assert result.ats_provider == "greenhouse"
    assert len(result.jobs) == 1
    assert result.jobs[0].title == "AI Engineer"


@responses.activate
def test_no_cached_ats_falls_back_to_detection():
    html = '<a href="https://boards.greenhouse.io/acme/jobs/1">AI Engineer</a>'
    responses.add(responses.GET, "https://acme.com/careers", body=html, status=200)
    payload = json.loads((FIXTURES / "greenhouse_jobs.json").read_text())
    responses.add(
        responses.GET,
        "https://boards-api.greenhouse.io/v1/boards/acme/jobs",
        json=payload,
        status=200,
    )

    company = Company(name="Acme Inc", career_page="https://acme.com/careers")
    client = HttpClient()
    result = fetch_company_jobs(client, company, role_keywords=["AI Engineer"])

    assert result.status == "ok"
    assert result.ats_provider == "greenhouse"
    assert len(result.jobs) == 1


@responses.activate
def test_unknown_cached_provider_falls_back_to_detection():
    """A provider name in the CSV that isn't one of our adapters (e.g. a typo)
    must not break the run — it should fall back to full detection."""
    html = "<html><body>no ATS here</body></html>"
    responses.add(responses.GET, "https://acme.com/careers", body=html, status=200)

    company = Company(
        name="Acme Inc",
        career_page="https://acme.com/careers",
        ats_provider="some_unsupported_provider",
        ats_identifier="acme",
    )
    client = HttpClient()
    result = fetch_company_jobs(client, company, role_keywords=["AI Engineer"])

    assert result.status == "ok:generic"
    assert result.jobs == []
