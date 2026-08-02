"""Role/keyword include-exclude filtering, applied before ranking.

This enforces the categorical "ignore these functions entirely" rules
(frontend, marketing, HR, sales, ... and internships unless enabled) and the
"only these role families" allowlist. Ranking (ranking.py) only ever sees
jobs that already passed this filter.
"""

from __future__ import annotations

from jobscraper.config import RolesConfig
from jobscraper.models import Job


def is_relevant(job: Job, roles: RolesConfig) -> bool:
    title_lower = job.title.lower()

    for excluded in roles.exclude_keywords:
        if excluded.lower().strip() in title_lower:
            return False

    if not roles.include_internships:
        for kw in roles.internship_keywords:
            if kw.lower() in title_lower:
                return False

    return any(role.lower() in title_lower for role in roles.include)


def filter_jobs(jobs: list[Job], roles: RolesConfig) -> list[Job]:
    return [job for job in jobs if is_relevant(job, roles)]
