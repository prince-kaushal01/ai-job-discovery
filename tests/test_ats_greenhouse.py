import json
from pathlib import Path

import responses

from jobscraper.ats import greenhouse
from jobscraper.http_client import HttpClient

FIXTURES = Path(__file__).parent / "fixtures"


@responses.activate
def test_greenhouse_parses_jobs_and_skips_blank_titles():
    payload = json.loads((FIXTURES / "greenhouse_jobs.json").read_text())
    responses.add(
        responses.GET,
        "https://boards-api.greenhouse.io/v1/boards/acme/jobs",
        json=payload,
        status=200,
    )

    client = HttpClient()
    jobs = greenhouse.fetch_jobs(client, "acme", "Acme Inc")

    assert len(jobs) == 1
    job = jobs[0]
    assert job.title == "AI Engineer"
    assert job.company_name == "Acme Inc"
    assert job.ats_platform == "greenhouse"
    assert job.remote is True
    assert job.apply_url == "https://boards.greenhouse.io/acme/jobs/1"


@responses.activate
def test_greenhouse_handles_http_error_gracefully():
    responses.add(
        responses.GET,
        "https://boards-api.greenhouse.io/v1/boards/missing/jobs",
        status=404,
    )
    client = HttpClient(max_retries=1)
    jobs = greenhouse.fetch_jobs(client, "missing", "Missing Co")
    assert jobs == []
