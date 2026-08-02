import json
from pathlib import Path

import responses

from jobscraper.ats import recruitee
from jobscraper.http_client import HttpClient

FIXTURES = Path(__file__).parent / "fixtures"


@responses.activate
def test_recruitee_parses_offers_and_skips_blank_titles():
    payload = json.loads((FIXTURES / "recruitee_offers.json").read_text())
    responses.add(
        responses.GET,
        "https://acme.recruitee.com/api/offers/",
        json=payload,
        status=200,
    )

    client = HttpClient()
    jobs = recruitee.fetch_jobs(client, "acme", "Acme Inc")

    assert len(jobs) == 1
    job = jobs[0]
    assert job.title == "AI Engineer"
    assert job.remote is True
    assert job.ats_platform == "recruitee"
    assert job.apply_url == "https://careers.acme.com/o/ai-engineer/c/new"


@responses.activate
def test_recruitee_handles_http_error_gracefully():
    responses.add(
        responses.GET,
        "https://missing.recruitee.com/api/offers/",
        status=404,
    )
    client = HttpClient(max_retries=1)
    jobs = recruitee.fetch_jobs(client, "missing", "Missing Co")
    assert jobs == []
