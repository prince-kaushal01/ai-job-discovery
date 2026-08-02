import json
from pathlib import Path

import responses

from jobscraper.ats import lever
from jobscraper.http_client import HttpClient

FIXTURES = Path(__file__).parent / "fixtures"


@responses.activate
def test_lever_parses_postings_and_skips_blank_titles():
    payload = json.loads((FIXTURES / "lever_postings.json").read_text())
    responses.add(
        responses.GET,
        "https://api.lever.co/v0/postings/acme",
        json=payload,
        status=200,
    )

    client = HttpClient()
    jobs = lever.fetch_jobs(client, "acme", "Acme Inc")

    assert len(jobs) == 1
    job = jobs[0]
    assert job.title == "Machine Learning Engineer"
    assert job.location == "Bengaluru, India"
    assert job.ats_platform == "lever"
    assert job.apply_url == "https://jobs.lever.co/acme/abc-123"
