"""Orchestrates one full daily run: fetch -> filter -> dedupe -> rank ->
store -> report -> email. This is the single entrypoint scripts/run_daily.py
calls; nothing here should be GitHub-Actions-specific.

Two independent fetch passes feed the same filter/rank/report pipeline:
  - Company pass: per-company ATS scraping against data/companies.csv
    (curated, genuine ATS provider + identifier per company — see
    scripts/detect_ats.py). This is the high-volume source.
  - Global pass: cross-company aggregators (RemoteOK, WeWorkRemotely,
    Himalayas, Jobicy) that need no company list, date-windowed via
    `since` (see _compute_since) so repeat runs only look at what's new.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
from pathlib import Path

from jobscraper.companies import load_companies
from jobscraper.company_fetcher import fetch_company_jobs
from jobscraper.config import Settings
from jobscraper.db import Database
from jobscraper.dedupe import dedupe_and_mark
from jobscraper.email_sender import send_email
from jobscraper.filtering import filter_jobs
from jobscraper.http_client import HttpClient
from jobscraper.models import Job, utcnow_iso
from jobscraper.ranking import cap_per_company, rank_jobs
from jobscraper.report import ReportData
from jobscraper.report.html import render_html
from jobscraper.report.markdown import render_markdown
from jobscraper.sources import himalayas, jobicy, remoteok, weworkremotely

logger = logging.getLogger(__name__)

_LAST_RUN_STATE_KEY = "last_run_completed_at"


def _qualifies_for_recommendation(job: Job, max_years_experience: int) -> bool:
    """Hard requirements for the main Top N Recommendations: remote, real
    tech-stack overlap, and within the YOE ceiling (or YOE simply isn't
    mentioned — we don't penalize a job just for not stating it)."""
    within_yoe = (
        job.required_years_experience is None
        or job.required_years_experience <= max_years_experience
    )
    return job.remote and job.has_stack_overlap and within_yoe


def _not_recommended_reason(job: Job, max_years_experience: int) -> str:
    """Explains why a job landed in "worth looking at" instead of the main
    list, so it's a visible classification, not a silent drop."""
    notes: list[str] = []
    if job.required_years_experience is not None and job.required_years_experience > max_years_experience:
        notes.append(
            f"needs ~{job.required_years_experience}+ yrs experience "
            f"(above your {max_years_experience}-yr preference)"
        )
    if not job.remote:
        notes.append("on-site / not remote")
    if not job.has_stack_overlap:
        notes.append("no direct tech-stack overlap detected")
    return "; ".join(notes) if notes else "ranked below your top picks"


def _compute_since(db: Database, settings: Settings) -> tuple[datetime, bool]:
    """First run (nothing recorded yet): look back a few days. Every run
    after that: only since the previous run completed."""
    now = datetime.now(timezone.utc)
    last_run_raw = db.get_state(_LAST_RUN_STATE_KEY)
    if last_run_raw is None:
        since = now - timedelta(days=settings.sources.first_run_lookback_days)
        return since, True
    return datetime.fromisoformat(last_run_raw), False


def _run_company_pass(
    client: HttpClient, db: Database, settings: Settings, company_limit: int | None
) -> tuple[list[Job], int, int]:
    companies = load_companies(settings.sources.companies_csv)
    if company_limit is not None:
        companies = companies[:company_limit]

    # Upsert every company up front so companies table stays complete even
    # if the run is interrupted mid-way through fetching.
    company_ids = {c.name: db.upsert_company(c) for c in companies}

    all_jobs: list[Job] = []
    companies_failed = 0

    logger.info(
        "Checking %d companies (concurrency=%d)", len(companies), settings.http.concurrency
    )
    with ThreadPoolExecutor(max_workers=settings.http.concurrency) as pool:
        futures = {
            pool.submit(fetch_company_jobs, client, company, settings.roles.include): company
            for company in companies
        }
        for future in as_completed(futures):
            company = futures[future]
            company_id = company_ids[company.name]
            try:
                result = future.result()
            except Exception as exc:
                logger.warning("Unexpected failure for %s: %s", company.name, exc)
                db.record_company_check(company_id, None, None, f"error: {exc}")
                companies_failed += 1
                continue

            db.record_company_check(
                company_id, result.ats_provider, result.ats_identifier, result.status
            )
            if result.status.startswith("error"):
                companies_failed += 1

            for job in result.jobs:
                job.company_id = company_id
                job.company_priority = company.priority
            all_jobs.extend(result.jobs)

    logger.info(
        "Company pass done: %d jobs found, %d companies failed",
        len(all_jobs),
        companies_failed,
    )
    return all_jobs, len(companies), companies_failed


def _run_global_sources_pass(
    client: HttpClient, settings: Settings, since: datetime
) -> tuple[list[Job], int, int]:
    calls: list[tuple[str, Callable[[], list[Job]]]] = []

    for rss in settings.sources.rss:
        if rss.name == "weworkremotely":
            calls.append(
                ("weworkremotely", lambda url=rss.url: weworkremotely.fetch_jobs(client, url, since=since))
            )
        else:
            logger.warning("No adapter registered for RSS source %r", rss.name)

    remoteok_url = settings.sources.apis.get("remoteok")
    if remoteok_url:
        calls.append(
            ("remoteok", lambda url=remoteok_url: remoteok.fetch_jobs(client, url, since=since))
        )

    if "himalayas" in settings.sources.apis:
        calls.append(
            ("himalayas", lambda: himalayas.fetch_jobs(client, settings.roles.include, since=since))
        )

    if "jobicy" in settings.sources.apis:
        calls.append(("jobicy", lambda: jobicy.fetch_jobs(client, since=since)))

    jobs: list[Job] = []
    sources_failed = 0
    for name, call in calls:
        try:
            jobs.extend(call())
        except Exception as exc:
            logger.warning("Unexpected failure from source %s: %s", name, exc)
            sources_failed += 1

    logger.info(
        "Global source pass done: %d jobs found across %d sources (%d failed)",
        len(jobs), len(calls), sources_failed,
    )
    return jobs, len(calls), sources_failed


def run_pipeline(
    settings: Settings,
    db: Database,
    company_limit: int | None = None,
    send_email_flag: bool = True,
) -> ReportData:
    client = HttpClient(
        timeout_seconds=settings.http.timeout_seconds,
        max_retries=settings.http.max_retries,
        backoff_seconds=settings.http.backoff_seconds,
        rate_limit_per_host_seconds=settings.http.rate_limit_per_host_seconds,
        user_agent=settings.http.user_agent,
    )

    company_jobs, companies_checked, companies_failed = _run_company_pass(
        client, db, settings, company_limit
    )

    since, is_first_run = _compute_since(db, settings)
    logger.info(
        "Fetching global-source jobs posted since %s (%s)",
        since.isoformat(), "first run, lookback window" if is_first_run else "since last run",
    )
    global_jobs, sources_checked, sources_failed = _run_global_sources_pass(client, settings, since)

    all_jobs = company_jobs + global_jobs
    relevant_jobs = filter_jobs(all_jobs, settings.roles)
    logger.info("%d jobs after role/keyword filtering", len(relevant_jobs))

    applied_hashes = db.all_applied_hashes()
    known_hashes = db.all_known_hashes()
    deduped_jobs = dedupe_and_mark(relevant_jobs, known_hashes, applied_hashes)
    logger.info("%d jobs after dedupe", len(deduped_jobs))

    ranked_jobs = rank_jobs(deduped_jobs, settings.profile, settings.roles)
    ranked_jobs = cap_per_company(ranked_jobs, settings.limits.max_jobs_per_company)
    for job in ranked_jobs:
        db.upsert_job(job)

    new_jobs = [j for j in ranked_jobs if j.is_new]
    recommendations = [
        j
        for j in new_jobs
        if j.rank_stars >= settings.email.min_stars_in_email
        and _qualifies_for_recommendation(j, settings.profile.max_years_experience)
    ][: settings.email.top_n_in_email]

    recommended_hashes = {j.job_hash for j in recommendations}
    worth_looking_at: list[Job] = []
    for j in new_jobs:
        if j.job_hash in recommended_hashes:
            continue
        # Overwrite rank_reason for display in this report only — already
        # upserted to the DB above, so this doesn't touch stored history.
        j.rank_reason = _not_recommended_reason(j, settings.profile.max_years_experience)
        worth_looking_at.append(j)
    worth_looking_at = worth_looking_at[: settings.email.worth_looking_at_limit]

    run_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    report_data = ReportData(
        run_date=run_date,
        total_jobs_found=len(ranked_jobs),
        new_jobs_found=len(new_jobs),
        companies_checked=companies_checked,
        companies_failed=companies_failed,
        sources_checked=sources_checked,
        sources_failed=sources_failed,
        recommendations=recommendations,
        worth_looking_at=worth_looking_at,
    )

    output_dir = Path(settings.report.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    html_path = output_dir / f"{run_date}.html"
    md_path = output_dir / f"{run_date}.md"

    html_body = render_html(report_data)
    md_body = render_markdown(report_data)
    html_path.write_text(html_body, encoding="utf-8")
    md_path.write_text(md_body, encoding="utf-8")

    email_sent = False
    if send_email_flag and settings.email.enabled:
        sender, password = settings.email.sender, settings.email.password
        if not sender or not password:
            logger.warning("Email credentials not configured (env vars unset); skipping send")
        else:
            subject = f"AI Job Digest — {run_date} — {len(new_jobs)} new opportunities"
            email_sent = send_email(
                settings.email.smtp_host,
                settings.email.smtp_port,
                sender,
                password,
                settings.email.recipient,
                subject,
                html_body,
                md_body,
            )

    db.record_daily_report(
        run_date=run_date,
        total_jobs_found=report_data.total_jobs_found,
        new_jobs_found=report_data.new_jobs_found,
        companies_checked=report_data.companies_checked,
        companies_failed=report_data.companies_failed,
        sources_checked=report_data.sources_checked,
        sources_failed=report_data.sources_failed,
        report_html_path=str(html_path),
        report_md_path=str(md_path),
        email_sent=email_sent,
    )
    db.set_state(_LAST_RUN_STATE_KEY, utcnow_iso())

    return report_data
