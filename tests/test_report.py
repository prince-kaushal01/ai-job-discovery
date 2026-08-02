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
