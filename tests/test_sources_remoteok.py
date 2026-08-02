import json
from pathlib import Path

import responses

from jobscraper.http_client import HttpClient
from jobscraper.sources import remoteok

FIXTURES = Path(__file__).parent / "fixtures"


@responses.activate
def test_remoteok_filters_to_ai_ml_tagged_jobs():
    payload = json.loads((FIXTURES / "remoteok_api.json").read_text())
    responses.add(
        responses.GET,
        "https://remoteok.com/api",
        json=payload,
        status=200,
    )

    client = HttpClient()
    jobs = remoteok.fetch_jobs(client)

    titles = {job.title for job in jobs}
    assert "AI Engineer" in titles
    assert "Sales Executive" not in titles
    assert all(job.remote for job in jobs)
