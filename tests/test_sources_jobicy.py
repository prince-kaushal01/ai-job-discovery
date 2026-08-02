import json
from pathlib import Path

import responses

from jobscraper.http_client import HttpClient
from jobscraper.sources import jobicy

FIXTURES = Path(__file__).parent / "fixtures"


@responses.activate
def test_jobicy_parses_jobs_and_skips_blank_titles():
    payload = json.loads((FIXTURES / "jobicy_jobs.json").read_text())
    responses.add(
        responses.GET,
        "https://jobicy.com/api/v2/remote-jobs",
        json=payload,
        status=200,
    )

    client = HttpClient()
    jobs = jobicy.fetch_jobs(client)

    assert len(jobs) == 1
    job = jobs[0]
    assert job.title == "Principal ML Engineer"
    assert job.company_name == "Acme Remote"
    assert job.remote is True
    assert job.location == "Europe"
    assert job.apply_url == "https://jobicy.com/jobs/148056-principal-ml-engineer"
    assert job.source == "jobicy"


@responses.activate
def test_jobicy_handles_http_error_gracefully():
    responses.add(
        responses.GET,
        "https://jobicy.com/api/v2/remote-jobs",
        status=500,
    )
    client = HttpClient(max_retries=1)
    jobs = jobicy.fetch_jobs(client)
    assert jobs == []
