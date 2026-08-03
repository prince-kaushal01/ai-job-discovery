from jobscraper.models import Job
from jobscraper.report import ReportData
from jobscraper.report.html import render_html
from jobscraper.report.markdown import render_markdown


def _sample_data() -> ReportData:
    job = Job(
        company_name="Acme",
        title="AI Engineer",
        apply_url="https://acme.com/apply",
        source="company_ats",
        location="Remote, India",
        remote=True,
        ats_platform="greenhouse",
        posted_date="2026-08-01",
        company_priority="Tier 1",
        rank_score=88.0,
        rank_stars=5,
        rank_reason='title matches "AI Engineer"; fully remote',
    )
    return ReportData(
        run_date="2026-08-02",
        total_jobs_found=42,
        new_jobs_found=3,
        companies_checked=215,
        companies_failed=2,
        sources_checked=4,
        sources_failed=0,
        recommendations=[job],
    )


def test_markdown_report_contains_key_fields():
    md = render_markdown(_sample_data())
    assert "AI Job Digest" in md
    assert "AI Engineer" in md
    assert "Acme" in md
    assert "https://acme.com/apply" in md
    assert "★★★★★" in md


def test_html_report_renders_without_error_and_escapes_content():
    html = render_html(_sample_data())
    assert "AI Job Digest" in html
    assert "AI Engineer" in html
    assert "https://acme.com/apply" in html
    assert "★" in html


def test_empty_recommendations_render_gracefully():
    data = _sample_data()
    data.recommendations = []
    md = render_markdown(data)
    html = render_html(data)
    assert "No new jobs met the ranking threshold" in md
    assert "No new jobs met the ranking threshold" in html


def test_worth_looking_at_renders_as_collapsible_section_in_html():
    data = _sample_data()
    data.worth_looking_at = [
        Job(
            company_name="Beta Inc",
            title="ML Engineer",
            apply_url="https://beta.com/apply",
            source="company_ats",
            rank_score=55.0,
            rank_stars=3,
            rank_reason="needs ~7+ yrs experience (above your 3-yr preference)",
        )
    ]
    html = render_html(data)
    assert "<details" in html
    assert "<summary" in html
    assert "Other jobs worth looking at (1)" in html
    assert "ML Engineer" in html
    assert "Beta Inc" in html
    assert "https://beta.com/apply" in html


def test_worth_looking_at_omitted_from_html_when_empty():
    html = render_html(_sample_data())
    assert "<details" not in html


def test_worth_looking_at_renders_in_markdown():
    data = _sample_data()
    data.worth_looking_at = [
        Job(
            company_name="Beta Inc",
            title="ML Engineer",
            apply_url="https://beta.com/apply",
            source="company_ats",
            rank_stars=3,
            rank_reason="on-site / not remote",
        )
    ]
    md = render_markdown(data)
    assert "Other jobs worth looking at (1)" in md
    assert "ML Engineer" in md
    assert "https://beta.com/apply" in md
    assert "on-site / not remote" in md
