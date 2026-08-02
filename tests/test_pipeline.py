from jobscraper.models import Job
from jobscraper.pipeline import _not_recommended_reason, _qualifies_for_recommendation


def _job(remote=True, has_stack_overlap=True, required_years_experience=None):
    return Job(
        company_name="Acme",
        title="AI Engineer",
        apply_url="u1",
        source="test",
        remote=remote,
        has_stack_overlap=has_stack_overlap,
        required_years_experience=required_years_experience,
    )


def test_qualifies_when_remote_stack_overlap_and_within_yoe():
    job = _job(remote=True, has_stack_overlap=True, required_years_experience=2)
    assert _qualifies_for_recommendation(job, max_years_experience=3) is True


def test_qualifies_when_yoe_not_mentioned_at_all():
    job = _job(remote=True, has_stack_overlap=True, required_years_experience=None)
    assert _qualifies_for_recommendation(job, max_years_experience=3) is True


def test_disqualified_when_over_experienced():
    job = _job(remote=True, has_stack_overlap=True, required_years_experience=7)
    assert _qualifies_for_recommendation(job, max_years_experience=3) is False


def test_disqualified_when_not_remote():
    job = _job(remote=False, has_stack_overlap=True, required_years_experience=1)
    assert _qualifies_for_recommendation(job, max_years_experience=3) is False


def test_disqualified_when_no_stack_overlap():
    job = _job(remote=True, has_stack_overlap=False, required_years_experience=1)
    assert _qualifies_for_recommendation(job, max_years_experience=3) is False


def test_disqualified_at_exactly_the_yoe_threshold_still_qualifies():
    job = _job(remote=True, has_stack_overlap=True, required_years_experience=3)
    assert _qualifies_for_recommendation(job, max_years_experience=3) is True


def test_not_recommended_reason_reports_over_experience():
    job = _job(remote=True, has_stack_overlap=True, required_years_experience=7)
    reason = _not_recommended_reason(job, max_years_experience=3)
    assert "needs ~7+ yrs experience" in reason
    assert "above your 3-yr preference" in reason


def test_not_recommended_reason_reports_not_remote():
    job = _job(remote=False, has_stack_overlap=True, required_years_experience=1)
    reason = _not_recommended_reason(job, max_years_experience=3)
    assert "on-site / not remote" in reason


def test_not_recommended_reason_reports_no_stack_overlap():
    job = _job(remote=True, has_stack_overlap=False, required_years_experience=1)
    reason = _not_recommended_reason(job, max_years_experience=3)
    assert "no direct tech-stack overlap detected" in reason


def test_not_recommended_reason_combines_multiple_issues():
    job = _job(remote=False, has_stack_overlap=False, required_years_experience=10)
    reason = _not_recommended_reason(job, max_years_experience=3)
    assert "needs ~10+ yrs experience" in reason
    assert "on-site / not remote" in reason
    assert "no direct tech-stack overlap detected" in reason


def test_not_recommended_reason_falls_back_when_nothing_specific():
    job = _job(remote=True, has_stack_overlap=True, required_years_experience=1)
    reason = _not_recommended_reason(job, max_years_experience=3)
    assert reason == "ranked below your top picks"
