"""Relevance ranking: a weighted score (0-100) mapped to a 1-5 star rating,
plus a short human-readable "why it matches" string for the email report.

Weights:
    title match against target roles      0-40
    preferred tech-stack keyword overlap  0-25
    remote fit                            0-15
    country/region fit                    0-10
    years-of-experience fit               0-10

Note: YOE/remote/stack-overlap also feed *hard* filters in pipeline.py for
what counts as a top recommendation (see _qualifies_for_recommendation) —
the weighted score alone isn't enough to keep an over-experienced or
on-site job out of the top picks if its title/stack match is strong.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from jobscraper.config import ProfileConfig, RolesConfig
from jobscraper.models import Job

# Unit covers "years"/"year", the "yrs"/"yr" abbreviation, and the "YOE"
# shorthand (word boundary at the end so it doesn't match inside a longer
# word). The separator between the number and unit allows a hyphen too, so
# adjective forms like "3-year experience requirement" match as well as
# "3 years" / "3+ yrs".
_YOE_UNIT = r"(?:years?|yrs?|yoe)\b"
_YOE_RANGE_RE = re.compile(rf"(\d+)\s*(?:-|to)\s*(\d+)\s*\+?\s*{_YOE_UNIT}", re.IGNORECASE)
_YOE_SINGLE_RE = re.compile(rf"(\d+)[\s-]*\+?\s*{_YOE_UNIT}", re.IGNORECASE)


@dataclass
class ScoreResult:
    score: float
    stars: int
    reason: str
    required_years_experience: int | None
    has_stack_overlap: bool


def score_job(job: Job, profile: ProfileConfig, roles: RolesConfig) -> ScoreResult:
    title_lower = job.title.lower()
    text = job.searchable_text()
    reasons: list[str] = []
    score = 0.0

    matched_role = next((r for r in roles.include if r.lower() in title_lower), None)
    if matched_role:
        score += 40
        reasons.append(f'title matches "{matched_role}"')

    matched_keywords = [kw for kw in profile.preferred_keywords if kw.lower() in text]
    has_stack_overlap = bool(matched_keywords)
    if has_stack_overlap:
        score += min(25, 5 * len(matched_keywords))
        shown = ", ".join(matched_keywords[:5])
        reasons.append(f"stack overlap: {shown}")

    if job.remote:
        if profile.remote_preference == "strong":
            score += 15
            reasons.append("fully remote")
        elif profile.remote_preference == "soft":
            score += 8
            reasons.append("remote")

    location_lower = job.location.lower()
    country_match = next(
        (c for c in profile.preferred_countries if c.lower() in location_lower), None
    )
    if country_match:
        score += 10
        reasons.append(f"location fits ({job.location})")
    elif job.remote:
        score += 5

    yoe_score, yoe_reason, required_years = _score_yoe(text, profile.max_years_experience)
    score += yoe_score
    if yoe_reason:
        reasons.append(yoe_reason)

    stars = _score_to_stars(score)
    reason_text = "; ".join(reasons) if reasons else "General AI/ML role match"
    return ScoreResult(score, stars, reason_text, required_years, has_stack_overlap)


def _score_to_stars(score: float) -> int:
    if score >= 80:
        return 5
    if score >= 65:
        return 4
    if score >= 50:
        return 3
    if score >= 30:
        return 2
    return 1


def _extract_min_years_required(text: str) -> int | None:
    """Finds the years-of-experience requirement mentioned in a job's title
    or description. For a range ("3-5 years") returns the lower bound —
    that's the actual minimum a candidate needs to qualify. Returns None if
    no YOE requirement is mentioned at all (checked before falling back to
    the single-number pattern, which would otherwise match part of a range
    like the "5" in "3-5 years")."""
    range_match = _YOE_RANGE_RE.search(text)
    if range_match:
        return int(range_match.group(1))

    single_match = _YOE_SINGLE_RE.search(text)
    if single_match:
        return int(single_match.group(1))

    return None


def _score_yoe(text: str, max_years_experience: int) -> tuple[float, str, int | None]:
    """A job requiring at most `max_years_experience` (default 3) is scored
    favorably; one requiring more is scored low. No YOE mentioned at all is
    neutral — we can't tell either way, so it shouldn't be penalized."""
    required = _extract_min_years_required(text)

    if required is None:
        return 5.0, "", None  # neutral half-credit when YOE isn't mentioned

    if required <= max_years_experience:
        return (
            10.0,
            f"needs ~{required} yrs experience (within your {max_years_experience}-yr preference)",
            required,
        )

    return (
        2.0,
        f"needs ~{required}+ yrs experience (above your {max_years_experience}-yr preference)",
        required,
    )


def rank_jobs(jobs: list[Job], profile: ProfileConfig, roles: RolesConfig) -> list[Job]:
    for job in jobs:
        result = score_job(job, profile, roles)
        job.rank_score = result.score
        job.rank_stars = result.stars
        job.rank_reason = result.reason
        job.required_years_experience = result.required_years_experience
        job.has_stack_overlap = result.has_stack_overlap
    return sorted(jobs, key=lambda j: j.rank_score, reverse=True)


def cap_per_company(jobs: list[Job], max_per_company: int) -> list[Job]:
    """Keeps at most `max_per_company` jobs per company, preferring the
    highest-ranked ones. Expects `jobs` to already be sorted by rank_score
    descending (as rank_jobs returns), so this keeps each company's best."""
    counts: dict[str, int] = {}
    capped: list[Job] = []
    for job in jobs:
        key = job.company_name.strip().lower()
        counts[key] = counts.get(key, 0) + 1
        if counts[key] <= max_per_company:
            capped.append(job)
    return capped
