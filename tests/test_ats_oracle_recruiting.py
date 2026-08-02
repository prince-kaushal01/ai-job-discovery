import json
from pathlib import Path

import responses

from jobscraper.ats import oracle_recruiting
from jobscraper.http_client import HttpClient

FIXTURES = Path(__file__).parent / "fixtures"


@responses.activate
def test_oracle_recruiting_parses_requisitions_and_skips_blank_titles():
    payload = json.loads((FIXTURES / "oracle_recruiting_reqs.json").read_text())
    responses.add(
        responses.GET,
        "https://acme.fa.us2.oraclecloud.com/hcmRestApi/resources/latest/recruitingCEJobRequisitions",
        json=payload,
        status=200,
    )

    client = HttpClient()
    jobs = oracle_recruiting.fetch_jobs(client, "acme.fa.us2.oraclecloud.com|CX_1001", "Acme Inc")

    assert len(jobs) == 1
    job = jobs[0]
    assert job.title == "Senior AI Engineer"
    assert job.remote is True
    assert job.ats_platform == "oracle_recruiting"
    assert "334643" in job.apply_url


def test_oracle_recruiting_handles_malformed_identifier():
    client = HttpClient()
    jobs = oracle_recruiting.fetch_jobs(client, "no-pipe-here", "Acme Inc")
    assert jobs == []


@responses.activate
def test_oracle_recruiting_handles_http_error_gracefully():
    responses.add(
        responses.GET,
        "https://missing.fa.us2.oraclecloud.com/hcmRestApi/resources/latest/recruitingCEJobRequisitions",
        status=404,
    )
    client = HttpClient(max_retries=1)
    jobs = oracle_recruiting.fetch_jobs(client, "missing.fa.us2.oraclecloud.com|CX_1", "Missing Co")
    assert jobs == []
