from pathlib import Path

import responses

from jobscraper.http_client import HttpClient
from jobscraper.sources import weworkremotely

FIXTURES = Path(__file__).parent / "fixtures"


@responses.activate
def test_weworkremotely_splits_company_and_title():
    xml = (FIXTURES / "wwr_feed.xml").read_text()
    responses.add(
        responses.GET,
        "https://weworkremotely.com/categories/remote-programming-jobs.rss",
        body=xml,
        status=200,
        content_type="application/rss+xml",
    )

    client = HttpClient()
    jobs = weworkremotely.fetch_jobs(client)

    assert len(jobs) == 2
    first = jobs[0]
    assert first.company_name == "Acme Inc"
    assert first.title == "AI Engineer"
    assert first.remote is True

    second = jobs[1]
    assert second.company_name == "Unknown"
    assert second.title == "No Colon Job Title"
