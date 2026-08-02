from jobscraper.config import RolesConfig
from jobscraper.filtering import filter_jobs, is_relevant
from jobscraper.models import Job

ROLES = RolesConfig(
    include=["AI Engineer", "Machine Learning Engineer", "ML Engineer"],
    exclude_keywords=["frontend", "marketing", "sales", "product manager"],
    include_internships=False,
    internship_keywords=["intern", "internship"],
)


def _job(title: str) -> Job:
    return Job(company_name="Acme", title=title, apply_url="https://acme.com/x", source="test")


def test_matches_included_role():
    assert is_relevant(_job("Senior AI Engineer"), ROLES) is True


def test_excludes_ignored_function_even_if_role_word_present():
    assert is_relevant(_job("AI Engineer - Marketing Growth"), ROLES) is False


def test_excludes_internship_by_default():
    assert is_relevant(_job("AI Engineer Internship"), ROLES) is False


def test_allows_internship_when_enabled():
    roles = ROLES.model_copy(update={"include_internships": True})
    assert is_relevant(_job("AI Engineer Internship"), roles) is True


def test_drops_unrelated_role():
    assert is_relevant(_job("Frontend Developer"), ROLES) is False


def test_filter_jobs_keeps_only_relevant():
    jobs = [_job("AI Engineer"), _job("Sales Executive"), _job("ML Engineer")]
    kept = filter_jobs(jobs, ROLES)
    assert {j.title for j in kept} == {"AI Engineer", "ML Engineer"}
