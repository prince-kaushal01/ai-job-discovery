from jobscraper.config import ProfileConfig, RolesConfig
from jobscraper.models import Job
from jobscraper.ranking import cap_per_company, score_job

PROFILE = ProfileConfig(
    years_experience=1,
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
    score, stars, reason = score_job(job, PROFILE, ROLES)
    assert stars == 5
    assert "AI Engineer" in reason or "title matches" in reason


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
    score, stars, reason = score_job(job, PROFILE, ROLES)
    assert stars <= 2


def test_higher_score_ranks_above_lower():
    strong = Job(
        company_name="Acme", title="AI Engineer", apply_url="u1", source="test",
        location="Remote, India", remote=True, description="Python LLM RAG PyTorch 0-2 years",
    )
    weak = Job(
        company_name="Acme", title="Machine Learning Engineer", apply_url="u2", source="test",
        location="Germany", remote=False, description="10+ years required",
    )
    strong_score, _, _ = score_job(strong, PROFILE, ROLES)
    weak_score, _, _ = score_job(weak, PROFILE, ROLES)
    assert strong_score > weak_score


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
