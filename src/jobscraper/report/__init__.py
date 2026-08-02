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
    # New jobs requiring <= profile.max_years_experience that didn't make
    # the cut into `recommendations` (lower star rating / past top_n) —
    # shown in a collapsible "see more" section instead of the main list.
    yoe_favorable_extra: list[Job] = field(default_factory=list)
