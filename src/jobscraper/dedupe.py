"""Duplicate detection: stable per-job hashing plus previously-seen /
previously-applied exclusion, so the same posting is never recommended
twice — whether it showed up again tomorrow, or was cross-posted on a
second source today.
"""

from __future__ import annotations

import hashlib
import re

from jobscraper.models import Job

_WHITESPACE_RE = re.compile(r"\s+")


def _normalize(text: str) -> str:
    return _WHITESPACE_RE.sub(" ", text.strip().lower())


def compute_job_hash(job: Job) -> str:
    key = f"{_normalize(job.company_name)}|{_normalize(job.title)}|{_normalize(job.location)}"
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


def dedupe_and_mark(
    jobs: list[Job], known_hashes: set[str], applied_hashes: set[str]
) -> list[Job]:
    """Assigns job_hash + is_new to each job, drops applied jobs and
    in-batch duplicates (e.g. the same posting from two sources today)."""
    result: list[Job] = []
    seen_in_batch: set[str] = set()

    for job in jobs:
        job.job_hash = compute_job_hash(job)

        if job.job_hash in applied_hashes:
            continue
        if job.job_hash in seen_in_batch:
            continue

        seen_in_batch.add(job.job_hash)
        job.is_new = job.job_hash not in known_hashes
        result.append(job)

    return result
