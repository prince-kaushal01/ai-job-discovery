"""Report generation: a shared ReportData model rendered to Markdown, HTML,
and (for the email fallback) plain text.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from jobscraper.models import Job


@dataclass
class ReportData:
    run_date: str
    total_jobs_found: int
    new_jobs_found: int
    companies_checked: int
    companies_failed: int
    recommendations: list[Job]
    # New jobs that didn't qualify for `recommendations` (over-experienced,
    # not remote, no direct stack overlap, or just ranked lower) — shown in
    # a collapsible "worth looking at" section instead of being dropped
    # silently. job.rank_reason is overwritten to explain why for each one.
    worth_looking_at: list[Job] = field(default_factory=list)
