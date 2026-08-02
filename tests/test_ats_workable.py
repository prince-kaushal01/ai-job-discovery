import json
from pathlib import Path

import responses

from jobscraper.ats import workable
from jobscraper.http_client import HttpClient

FIXTURES = Path(__file__).parent / "fixtures"


@responses.activate
def test_workable_parses_jobs_and_skips_blank_titles():
    payload = json.loads((FIXTURES / "workable_jobs.json").read_text())
    responses.add(
        responses.GET,
        "https://apply.workable.com/api/v1/widget/accounts/acme",
        json=payload,
        status=200,
    )

    client = HttpClient()
    jobs = workable.fetch_jobs(client, "acme", "Acme Inc")

    assert len(jobs) == 1
    job = jobs[0]
    assert job.title == "AI Engineer"
    assert job.location == "Paris, France"
    assert job.remote is True
    assert job.ats_platform == "workable"
    assert job.apply_url == "https://apply.workable.com/acme/j/ABC123"


@responses.activate
def test_workable_handles_http_error_gracefully():
    responses.add(
        responses.GET,
        "https://apply.workable.com/api/v1/widget/accounts/missing",
        status=404,
    )
    client = HttpClient(max_retries=1)
    jobs = workable.fetch_jobs(client, "missing", "Missing Co")
    assert jobs == []
