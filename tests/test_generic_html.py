from pathlib import Path

import responses

from jobscraper.ats import generic_html
from jobscraper.http_client import HttpClient

FIXTURES = Path(__file__).parent / "fixtures"


@responses.activate
def test_generic_html_matches_role_keywords_and_resolves_relative_links():
    html = (FIXTURES / "generic_careers.html").read_text()
    responses.add(
        responses.GET,
        "https://acme.com/careers",
        body=html,
        status=200,
        content_type="text/html",
    )

    client = HttpClient()
    jobs = generic_html.fetch_jobs(
        client,
        "https://acme.com/careers",
        "Acme Inc",
        role_keywords=["AI Engineer", "Machine Learning Engineer"],
    )

    titles = {job.title for job in jobs}
    assert "AI Engineer" in titles
    assert "Machine Learning Engineer - Remote" in titles
    assert "Frontend Developer" not in titles

    ml_job = next(j for j in jobs if "Machine Learning" in j.title)
    assert ml_job.apply_url == "https://acme.com/jobs/125"
    assert ml_job.remote is True

    ai_job = next(j for j in jobs if j.title == "AI Engineer")
    assert ai_job.apply_url == "https://acme.com/jobs/123"
