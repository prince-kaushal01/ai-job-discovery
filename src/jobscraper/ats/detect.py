"""Sniffs a fetched career page (HTML + final URL) for known ATS signatures.

Most companies in the target list link to their own domain
(e.g. careers.adobe.com) which then embeds or links out to an ATS-hosted
board. So detection works on the *fetched page content*, not the CSV URL.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# Order matters only in that first match for a given provider wins; providers
# are checked independently so a page could in theory match >1 (first one in
# this list is preferred).
_PATTERNS: list[tuple[str, re.Pattern]] = [
    # Embed-widget form must come first: boards.greenhouse.io/embed/job_board?for=<token>
    # — the generic pattern below would otherwise capture the literal "embed" path segment.
    ("greenhouse", re.compile(r"greenhouse\.io/embed/job_board(?:/js)?\?for=([a-zA-Z0-9_%-]+)")),
    ("greenhouse", re.compile(r"(?:boards|job-boards)\.greenhouse\.io/([a-zA-Z0-9_%-]+)")),
    ("greenhouse", re.compile(r"boards-api\.greenhouse\.io/v1/boards/([a-zA-Z0-9_%-]+)")),
    ("lever", re.compile(r"jobs\.lever\.co/([a-zA-Z0-9_%-]+)")),
    # Board slugs can contain URL-encoded spaces etc. (e.g. "Jasper%20AI") —
    # the % must be in the character class or the match truncates mid-token.
    ("ashby", re.compile(r"jobs\.ashbyhq\.com/([a-zA-Z0-9_%-]+)")),
    ("smartrecruiters", re.compile(r"careers\.smartrecruiters\.com/([a-zA-Z0-9_%-]+)")),
    # Only skip a genuine locale code (e.g. "en-US/"), not any word — Workday
    # site names directly followed by a subpage (".../AccentureCareers/userHome")
    # would otherwise get misread as "<locale>/<site>" and capture the subpage.
    ("workday", re.compile(r"([a-zA-Z0-9_-]+)\.(wd\d+)\.myworkdayjobs\.com/(?:[a-z]{2}-[A-Z]{2}/)?([a-zA-Z0-9_-]+)")),
    ("teamtailor", re.compile(r"([a-zA-Z0-9_-]+)\.teamtailor\.com")),
    ("bamboohr", re.compile(r"([a-zA-Z0-9_-]+)\.bamboohr\.com")),
]

# Hosts that indicate the platform itself, even without a full match above
# (used as a secondary generic-domain check).
_GENERIC_EXCLUDE_HOSTS = {
    "teamtailor.com",
    "bamboohr.com",
}


@dataclass
class DetectionResult:
    provider: str
    identifier: str


def detect_ats(html: str, final_url: str) -> DetectionResult | None:
    """Scan page HTML (and the final resolved URL) for an ATS signature."""
    haystacks = [final_url, html]

    for provider, pattern in _PATTERNS:
        for haystack in haystacks:
            match = pattern.search(haystack)
            if not match:
                continue

            if provider == "workday":
                tenant, wd_host, site = match.group(1), match.group(2), match.group(3)
                identifier = f"{tenant}.{wd_host}.myworkdayjobs.com/{site}"
            else:
                identifier = match.group(1)

            # Skip false positives like "teamtailor.com/blog" as a bare identifier
            if provider in {"teamtailor", "bamboohr"} and identifier in {"www", "app", "api"}:
                continue
            if provider == "greenhouse" and identifier in {"embed", "job_board", "job-boards"}:
                continue

            return DetectionResult(provider=provider, identifier=identifier)

    return None
