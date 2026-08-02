"""Report generation: a shared ReportData model rendered to Markdown, HTML,
and (for the email fallback) plain text.
"""

from __future__ import annotations

from dataclasses import dataclass

from jobscraper.models import Job


@dataclass
class ReportData:
    run_date: str
    total_jobs_found: int
    new_jobs_found: int
    companies_checked: int
    companies_failed: int
    recommendations: list[Job]
