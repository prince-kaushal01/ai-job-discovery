from jobscraper.config import ProfileConfig, RolesConfig
from jobscraper.models import Job
from jobscraper.ranking import _extract_min_years_required, _score_yoe, cap_per_company, rank_jobs, score_job

PROFILE = ProfileConfig(
    max_years_experience=3,
    preferred_countries=["India", "Remote"],
    remote_preference="strong",
    preferred_keywords=["python", "llm", "rag", "pytorch"],
)
ROLES = RolesConfig(include=["AI Engineer", "Machine Learning Engineer"])


def test_perfect_match_scores_five_stars():
    job = Job(
        company_name="Acme",
        title="AI Engineer",
        apply_url="https://acme.com/1",
        source="test",
        location="Remote, India",
        remote=True,
        description="Use Python, LLM, RAG and PyTorch. Requires 1-2 years of experience.",
    )
    score, stars, reason, yoe_favorable = score_job(job, PROFILE, ROLES)
    assert stars == 5
    assert "AI Engineer" in reason or "title matches" in reason
    assert yoe_favorable is True


def test_weak_match_scores_low():
    job = Job(
        company_name="Acme",
        title="AI Engineer",
        apply_url="https://acme.com/2",
        source="test",
        location="Germany",
        remote=False,
        description="Requires 8+ years of experience with obscure tools.",
    )
    score, stars, reason, yoe_favorable = score_job(job, PROFILE, ROLES)
    assert stars <= 2
    assert yoe_favorable is False


def test_higher_score_ranks_above_lower():
    strong = Job(
        company_name="Acme", title="AI Engineer", apply_url="u1", source="test",
        location="Remote, India", remote=True, description="Python LLM RAG PyTorch 0-2 years",
    )
    weak = Job(
        company_name="Acme", title="Machine Learning Engineer", apply_url="u2", source="test",
        location="Germany", remote=False, description="10+ years required",
    )
    strong_score, _, _, _ = score_job(strong, PROFILE, ROLES)
    weak_score, _, _, _ = score_job(weak, PROFILE, ROLES)
    assert strong_score > weak_score


def test_extract_min_years_from_range_takes_lower_bound():
    assert _extract_min_years_required("Requires 3-5 years of experience") == 3


def test_extract_min_years_from_plus_form():
    assert _extract_min_years_required("5+ years in ML") == 5


def test_extract_min_years_from_single_number():
    assert _extract_min_years_required("2 years of Python experience") == 2


def test_extract_min_years_from_yrs_abbreviation():
    assert _extract_min_years_required("Requires 2 yrs of experience") == 2


def test_extract_min_years_from_yr_abbreviation():
    assert _extract_min_years_required("Requires 2 yr experience") == 2


def test_extract_min_years_from_yoe_shorthand():
    assert _extract_min_years_required("3 YOE required") == 3
    assert _extract_min_years_required("3+ yoe") == 3


def test_extract_min_years_from_hyphenated_adjective_form():
    assert _extract_min_years_required("3-year experience requirement") == 3


def test_extract_min_years_from_minimum_at_least_phrasing():
    assert _extract_min_years_required("minimum of 2 years experience") == 2
    assert _extract_min_years_required("at least 2 years of experience") == 2


def test_extract_min_years_avoids_false_positives():
    assert _extract_min_years_required("Series Y funding round") is None
    assert _extract_min_years_required("Python 3.9+ required") is None
    assert _extract_min_years_required("team of 25 engineers") is None


def test_extract_min_years_returns_none_when_not_mentioned():
    assert _extract_min_years_required("Great team, competitive pay") is None


def test_yoe_at_or_under_threshold_scores_favorably():
    score, reason = _score_yoe("requires 2-3 years of experience", max_years_experience=3)
    assert score == 10.0
    assert "within your 3-yr preference" in reason


def test_yoe_over_threshold_scores_low():
    score, reason = _score_yoe("requires 7+ years of experience", max_years_experience=3)
    assert score == 2.0
    assert "above your 3-yr preference" in reason


def test_yoe_exactly_at_threshold_is_still_favorable():
    score, _ = _score_yoe("3 years of experience required", max_years_experience=3)
    assert score == 10.0


def test_yoe_not_mentioned_is_neutral_not_penalized():
    score, reason = _score_yoe("great benefits, flexible hours", max_years_experience=3)
    assert score == 5.0
    assert reason == ""


def test_rank_jobs_sets_yoe_favorable_on_the_job_object():
    favorable = Job(
        company_name="Acme", title="AI Engineer", apply_url="u1", source="test",
        description="1-2 years of experience",
    )
    unfavorable = Job(
        company_name="Acme", title="AI Engineer", apply_url="u2", source="test",
        description="8+ years of experience",
    )
    ranked = rank_jobs([favorable, unfavorable], PROFILE, ROLES)
    by_url = {j.apply_url: j for j in ranked}
    assert by_url["u1"].yoe_favorable is True
    assert by_url["u2"].yoe_favorable is False


def test_cap_per_company_keeps_best_n_and_preserves_order():
    jobs = [
        Job(company_name="Reddit", title=f"ML Engineer {i}", apply_url=f"u{i}", source="test", rank_score=100 - i)
        for i in range(8)
    ] + [
        Job(company_name="OpenAI", title="AI Engineer", apply_url="u-openai", source="test", rank_score=95),
    ]
    jobs.sort(key=lambda j: j.rank_score, reverse=True)

    capped = cap_per_company(jobs, max_per_company=5)

    reddit_jobs = [j for j in capped if j.company_name == "Reddit"]
    assert len(reddit_jobs) == 5
    assert [j.rank_score for j in reddit_jobs] == sorted((j.rank_score for j in reddit_jobs), reverse=True)
    assert any(j.company_name == "OpenAI" for j in capped)
    assert len(capped) == 6
