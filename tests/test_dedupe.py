from jobscraper.dedupe import compute_job_hash, dedupe_and_mark
from jobscraper.models import Job


def _job(company="Acme", title="AI Engineer", location="Remote", url="https://acme.com/1"):
    return Job(company_name=company, title=title, apply_url=url, source="test", location=location)


def test_hash_is_stable_and_case_insensitive():
    a = compute_job_hash(_job(title="AI Engineer"))
    b = compute_job_hash(_job(title="ai engineer"))
    assert a == b


def test_hash_differs_for_different_location():
    a = compute_job_hash(_job(location="Remote"))
    b = compute_job_hash(_job(location="Bengaluru"))
    assert a != b


def test_dedupe_drops_previously_applied_jobs():
    job = _job()
    known_hash = compute_job_hash(job)
    result = dedupe_and_mark([job], known_hashes=set(), applied_hashes={known_hash})
    assert result == []


def test_dedupe_drops_in_batch_duplicates_from_multiple_sources():
    job_a = _job(url="https://acme.com/apply-1")
    job_b = _job(url="https://someboard.com/acme-ai-engineer")  # same company/title/location
    result = dedupe_and_mark([job_a, job_b], known_hashes=set(), applied_hashes=set())
    assert len(result) == 1


def test_dedupe_marks_is_new_correctly():
    job = _job()
    h = compute_job_hash(job)
    result = dedupe_and_mark([job], known_hashes={h}, applied_hashes=set())
    assert result[0].is_new is False

    job2 = _job(title="Different Title")
    result2 = dedupe_and_mark([job2], known_hashes={h}, applied_hashes=set())
    assert result2[0].is_new is True
