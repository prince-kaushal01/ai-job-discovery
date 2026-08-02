"""Orchestrates one full daily run: fetch -> filter -> dedupe -> rank ->
store -> report -> email. This is the single entrypoint scripts/run_daily.py
calls; nothing here should be GitHub-Actions-specific.
"""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

from jobscraper.companies import load_companies
from jobscraper.company_fetcher import fetch_company_jobs
from jobscraper.config import Settings
from jobscraper.db import Database
from jobscraper.dedupe import dedupe_and_mark
from jobscraper.email_sender import send_email
from jobscraper.filtering import filter_jobs
from jobscraper.http_client import HttpClient
from jobscraper.models import Job
from jobscraper.ranking import rank_jobs
from jobscraper.report import ReportData
from jobscraper.report.html import render_html
from jobscraper.report.markdown import render_markdown
from jobscraper.sources import remoteok, weworkremotely

logger = logging.getLogger(__name__)


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


def _run_global_sources_pass(client: HttpClient, settings: Settings) -> list[Job]:
    jobs: list[Job] = []

    for rss in settings.sources.rss:
        if rss.name == "weworkremotely":
            jobs.extend(weworkremotely.fetch_jobs(client, rss.url))
        else:
            logger.warning("No adapter registered for RSS source %r", rss.name)

    remoteok_url = settings.sources.apis.get("remoteok")
    if remoteok_url:
        jobs.extend(remoteok.fetch_jobs(client, remoteok_url))

    logger.info("Global source pass done: %d jobs found", len(jobs))
    return jobs


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
    global_jobs = _run_global_sources_pass(client, settings)
    all_jobs = company_jobs + global_jobs

    relevant_jobs = filter_jobs(all_jobs, settings.roles)
    logger.info("%d jobs after role/keyword filtering", len(relevant_jobs))

    applied_hashes = db.all_applied_hashes()
    known_hashes = db.all_known_hashes()
    deduped_jobs = dedupe_and_mark(relevant_jobs, known_hashes, applied_hashes)
    logger.info("%d jobs after dedupe", len(deduped_jobs))

    ranked_jobs = rank_jobs(deduped_jobs, settings.profile, settings.roles)
    for job in ranked_jobs:
        db.upsert_job(job)

    new_jobs = [j for j in ranked_jobs if j.is_new]
    recommendations = [
        j for j in new_jobs if j.rank_stars >= settings.email.min_stars_in_email
    ][: settings.email.top_n_in_email]

    run_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    report_data = ReportData(
        run_date=run_date,
        total_jobs_found=len(ranked_jobs),
        new_jobs_found=len(new_jobs),
        companies_checked=companies_checked,
        companies_failed=companies_failed,
        recommendations=recommendations,
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
        report_html_path=str(html_path),
        report_md_path=str(md_path),
        email_sent=email_sent,
    )

    return report_data
