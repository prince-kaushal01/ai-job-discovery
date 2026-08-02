import json
from pathlib import Path

import responses

from jobscraper.http_client import HttpClient
from jobscraper.sources import himalayas

FIXTURES = Path(__file__).parent / "fixtures"


@responses.activate
def test_himalayas_parses_jobs_and_skips_blank_titles():
    payload = json.loads((FIXTURES / "himalayas_search.json").read_text())
    responses.add(
        responses.GET,
        "https://himalayas.app/jobs/api/search",
        json=payload,
        status=200,
    )

    client = HttpClient()
    jobs = himalayas.fetch_jobs(client, role_keywords=["AI Engineer"])

    assert len(jobs) == 1
    job = jobs[0]
    assert job.title == "AI Engineer"
    assert job.company_name == "Acme Remote"
    assert job.remote is True
    assert job.location == "Poland, Ukraine"
    assert job.apply_url == "https://himalayas.app/companies/acme-remote/jobs/ai-engineer-1"
    assert job.source == "himalayas"


@responses.activate
def test_himalayas_dedupes_across_multiple_role_queries():
    payload = json.loads((FIXTURES / "himalayas_search.json").read_text())
    responses.add(
        responses.GET,
        "https://himalayas.app/jobs/api/search",
        json=payload,
        status=200,
    )

    client = HttpClient()
    # Same fixture returned for both queries -> same guid -> deduped to 1 job.
    jobs = himalayas.fetch_jobs(client, role_keywords=["AI Engineer", "ML Engineer"])

    assert len(jobs) == 1


@responses.activate
def test_himalayas_handles_http_error_gracefully():
    responses.add(
        responses.GET,
        "https://himalayas.app/jobs/api/search",
        status=500,
    )
    client = HttpClient(max_retries=1)
    jobs = himalayas.fetch_jobs(client, role_keywords=["AI Engineer"])
    assert jobs == []
