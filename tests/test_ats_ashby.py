import json
from pathlib import Path

import responses

from jobscraper.ats import ashby
from jobscraper.http_client import HttpClient

FIXTURES = Path(__file__).parent / "fixtures"


@responses.activate
def test_ashby_parses_jobs():
    payload = json.loads((FIXTURES / "ashby_jobs.json").read_text())
    responses.add(
        responses.GET,
        "https://api.ashbyhq.com/posting-api/job-board/acme",
        json=payload,
        status=200,
    )

    client = HttpClient()
    jobs = ashby.fetch_jobs(client, "acme", "Acme Inc")

    assert len(jobs) == 1
    job = jobs[0]
    assert job.title == "GenAI Engineer"
    assert job.remote is True
    assert job.ats_platform == "ashby"
    assert job.apply_url == "https://jobs.ashbyhq.com/acme/genai-engineer"
