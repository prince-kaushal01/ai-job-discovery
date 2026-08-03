#!/usr/bin/env python
"""One-off: resolve real ATS identifiers for data/companies_sample - Sheet1.csv
(Company, ATS free-text only — no career page URL, no board token) and write a
new data/companies.csv with only LIVE-VERIFIED (provider, identifier) pairs.

Strategy per company:
  1. Classify the free-text ATS column to zero or more supported providers
     (substring match against greenhouse/lever/ashby/workable/smartrecruiters/
     workday). Rows naming only unsupported platforms (Keka, Darwinbox, Zoho
     Recruit, SAP SuccessFactors, Rippling, "Not Accessible", blank, ...) are
     skipped entirely — no adapter exists for them.
  2. Seed candidate identifiers from the previously-verified (deleted)
     data/companies.csv (recovered via `git show HEAD:data/companies.csv`) by
     exact company-name match, regardless of which provider it was filed
     under — ATS providers migrate, so a name match is worth checking even
     against a different provider than the new sheet claims.
  3. Generate slug variants from the company name for every remaining
     candidate provider (skipped for workday — a wd-instance number can't be
     guessed, only reused-from-old or found separately).
  4. Every candidate (reused or guessed) is verified with a live HTTP call to
     the adapter's real API before being accepted. A wrong guess just 404s;
     nothing goes into the output CSV without a real 200 + parseable board.

Usage:
    python scripts/resolve_new_companies.py
    python scripts/resolve_new_companies.py --workers 12
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import requests

REPO_ROOT = Path(__file__).resolve().parent.parent
SAMPLE_CSV = REPO_ROOT / "data" / "companies_sample - Sheet1.csv"
OUT_CSV = REPO_ROOT / "data" / "companies.csv"
UNRESOLVED_CSV = REPO_ROOT / "reports" / "unresolved_companies.csv"

_SUPPORTED = ["greenhouse", "lever", "ashby", "workday", "workable", "smartrecruiters"]

_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
}


def classify_providers(ats_raw: str) -> list[str]:
    text = (ats_raw or "").strip().lower()
    return [p for p in _SUPPORTED if p in text]


def slug_variants(name: str) -> list[str]:
    lower = name.lower().replace("&", "and")
    stripped = re.sub(r"[^a-z0-9\s-]", "", lower)
    words = stripped.split()
    no_space = "".join(words)
    hyphen = "-".join(words)
    first_word = words[0] if words else no_space
    first_two = "".join(words[:2]) if len(words) >= 2 else no_space
    first_two_hyphen = "-".join(words[:2]) if len(words) >= 2 else hyphen

    drop_suffixes = {"ai", "labs", "inc", "technologies", "technology", "software",
                      "systems", "india", "tech", "analytics", "solutions", "co"}
    trimmed_words = [w for w in words if w not in drop_suffixes]
    trimmed = "".join(trimmed_words) if trimmed_words else no_space
    trimmed_hyphen = "-".join(trimmed_words) if trimmed_words else hyphen

    variants = [
        no_space, hyphen, trimmed, trimmed_hyphen, first_word, first_two, first_two_hyphen,
        f"{no_space}ai", f"{trimmed}ai", f"get{no_space}", f"get{trimmed}",
        f"{no_space}hq", f"try{no_space}", f"{no_space}inc", f"{no_space}labs",
        f"{no_space}app", f"the{no_space}", f"join{no_space}",
    ]
    seen: set[str] = set()
    ordered: list[str] = []
    for v in variants:
        if v and v not in seen:
            seen.add(v)
            ordered.append(v)
    return ordered


def build_url(provider: str, identifier: str) -> str:
    if provider == "greenhouse":
        return f"https://boards-api.greenhouse.io/v1/boards/{identifier}/jobs"
    if provider == "lever":
        return f"https://api.lever.co/v0/postings/{identifier}?mode=json"
    if provider == "ashby":
        return f"https://api.ashbyhq.com/posting-api/job-board/{identifier}"
    if provider == "workable":
        return f"https://apply.workable.com/api/v1/widget/accounts/{identifier}"
    if provider == "smartrecruiters":
        return f"https://api.smartrecruiters.com/v1/companies/{identifier}/postings"
    if provider == "workday":
        try:
            host_part, site = identifier.split("/", 1)
            tenant = host_part.split(".")[0]
        except ValueError:
            return ""
        return f"https://{host_part}/wday/cxs/{tenant}/{site}/jobs"
    return ""


def build_career_url(provider: str, identifier: str) -> str:
    """A human-facing career-page URL derived from the verified identifier.
    load_companies() requires a non-blank URL per row; company_fetcher never
    actually fetches it when ats_provider+ats_identifier are cached (see
    fetch_company_jobs), so this only needs to be a real, clickable link —
    not something the pipeline depends on for correctness."""
    if provider == "greenhouse":
        return f"https://boards.greenhouse.io/{identifier}"
    if provider == "lever":
        return f"https://jobs.lever.co/{identifier}"
    if provider == "ashby":
        return f"https://jobs.ashbyhq.com/{identifier}"
    if provider == "workable":
        return f"https://apply.workable.com/{identifier}"
    if provider == "smartrecruiters":
        return f"https://careers.smartrecruiters.com/{identifier}"
    if provider == "workday":
        return f"https://{identifier}"
    return ""


def verify(provider: str, identifier: str) -> int | None:
    """Returns the job count if the identifier is real and live, else None."""
    url = build_url(provider, identifier)
    if not url:
        return None
    try:
        if provider == "workday":
            resp = requests.post(
                url, json={"appliedFacets": {}, "limit": 20, "offset": 0, "searchText": ""},
                headers={**_HEADERS, "Content-Type": "application/json"}, timeout=10,
            )
        else:
            resp = requests.get(url, headers=_HEADERS, timeout=10)
        if resp.status_code != 200:
            return None
        data = resp.json()
    except Exception:
        return None

    if provider == "lever":
        return len(data) if isinstance(data, list) else None
    if provider == "greenhouse":
        jobs = data.get("jobs") if isinstance(data, dict) else None
        return len(jobs) if isinstance(jobs, list) else None
    if provider == "ashby":
        jobs = data.get("jobs") if isinstance(data, dict) else None
        return len(jobs) if isinstance(jobs, list) else None
    if provider == "workable":
        jobs = data.get("jobs") if isinstance(data, dict) else None
        return len(jobs) if isinstance(jobs, list) else None
    if provider == "smartrecruiters":
        # SmartRecruiters' postings endpoint returns HTTP 200 with an empty
        # `content` list for ANY slug, real or not — unlike every other
        # provider here, a 200 alone proves nothing. Only a nonzero result
        # is evidence of a genuine account; 0 is indistinguishable from a
        # fake company and must not be accepted.
        content = data.get("content") if isinstance(data, dict) else None
        if not isinstance(content, list) or len(content) == 0:
            return None
        return len(content)
    if provider == "workday":
        jobs = data.get("jobPostings") if isinstance(data, dict) else None
        return len(jobs) if isinstance(jobs, list) else None
    return None


def load_old_identifiers() -> dict[str, list[tuple[str, str]]]:
    """name.lower() -> [(provider, identifier), ...] from the previously
    committed companies.csv (recovered from git even though the working tree
    copy was deleted)."""
    import subprocess

    try:
        raw = subprocess.run(
            ["git", "show", "HEAD:data/companies.csv"],
            cwd=REPO_ROOT, capture_output=True, text=True, check=True, encoding="utf-8",
        ).stdout
    except Exception:
        return {}

    import io
    reader = csv.DictReader(io.StringIO(raw))
    result: dict[str, list[tuple[str, str]]] = {}
    for row in reader:
        name = (row.get("Company") or "").strip()
        provider = (row.get("ATS") or "").strip()
        identifier = (row.get("ATS Identifier") or "").strip()
        if name and provider and identifier:
            result.setdefault(name.lower(), []).append((provider, identifier))
    return result


def resolve_one(
    company: str, stated_providers: list[str], old_identifiers: dict[str, list[tuple[str, str]]]
) -> tuple[str, str, str, int] | None:
    """Returns (company, provider, identifier, job_count) on success, else None."""
    candidates: list[tuple[str, str]] = []

    for provider, identifier in old_identifiers.get(company.lower(), []):
        candidates.append((provider, identifier))

    for provider in stated_providers:
        if provider == "workday":
            continue  # unguessable without a real tenant/site; reuse-only above
        for variant in slug_variants(company):
            candidates.append((provider, variant))

    seen: set[tuple[str, str]] = set()
    for provider, identifier in candidates:
        key = (provider, identifier)
        if key in seen:
            continue
        seen.add(key)
        count = verify(provider, identifier)
        if count is not None:
            return company, provider, identifier, count

    return None


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workers", type=int, default=10)
    parser.add_argument(
        "--retry-unresolved", action="store_true",
        help="Only re-attempt companies from the previous run's unresolved_companies.csv, "
        "keeping everything already resolved in data/companies.csv",
    )
    args = parser.parse_args()

    rows = list(csv.DictReader(SAMPLE_CSV.open(encoding="utf-8")))
    old_identifiers = load_old_identifiers()
    print(f"Loaded {len(rows)} companies from sample sheet, "
          f"{len(old_identifiers)} previously-verified names to reuse as seeds.")

    by_company = {(row.get("Company") or "").strip(): row for row in rows}

    already_resolved: list[tuple[str, str, str, int]] = []
    retry_only: set[str] | None = None
    if args.retry_unresolved and UNRESOLVED_CSV.exists() and OUT_CSV.exists():
        retry_only = set()
        for r in csv.DictReader(UNRESOLVED_CSV.open(encoding="utf-8")):
            if "no live-verifiable identifier" in (r.get("Reason") or ""):
                retry_only.add(r["Company"])
        for r in csv.DictReader(OUT_CSV.open(encoding="utf-8")):
            already_resolved.append((r["Company"], r["ATS"], r["ATS Identifier"], 0))
        print(f"Retry mode: keeping {len(already_resolved)} already-resolved, "
              f"retrying {len(retry_only)} unresolved with wider slug variants.")

    tasks: list[tuple[str, list[str]]] = []
    skipped_unsupported: list[tuple[str, str]] = []
    for row in rows:
        company = (row.get("Company") or "").strip()
        ats_raw = (row.get("ATS") or "").strip()
        if not company:
            continue
        if retry_only is not None and company not in retry_only:
            continue
        providers = classify_providers(ats_raw)
        has_old = company.lower() in old_identifiers
        if not providers and not has_old:
            if retry_only is None:
                skipped_unsupported.append((company, ats_raw))
            continue
        tasks.append((company, providers))

    print(f"{len(tasks)} companies to attempt, {len(skipped_unsupported)} skipped "
          f"(no supported ATS adapter for their stated platform).")

    resolved: list[tuple[str, str, str, int]] = []
    unresolved: list[str] = []
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {
            pool.submit(resolve_one, company, providers, old_identifiers): company
            for company, providers in tasks
        }
        done = 0
        for future in as_completed(futures):
            done += 1
            company = futures[future]
            result = future.result()
            if result is None:
                unresolved.append(company)
                print(f"[{done}/{len(tasks)}] UNRESOLVED  {company}")
            else:
                _, provider, identifier, count = result
                resolved.append(result)
                print(f"[{done}/{len(tasks)}] OK  {company}: {provider}/{identifier} ({count} jobs)")

    resolved.extend(already_resolved)

    if retry_only is not None:
        # Preserve the unsupported-ATS rows from the previous unresolved report
        # (those were never part of this retry pass).
        for r in csv.DictReader(UNRESOLVED_CSV.open(encoding="utf-8")):
            reason = r.get("Reason") or ""
            if reason.startswith("unsupported ATS"):
                skipped_unsupported.append((r["Company"], reason.replace("unsupported ATS: ", "")))

    resolved.sort(key=lambda r: r[0])
    unresolved.sort()

    fieldnames = [
        "Company", "Region", "Category", "Careers / Job Board URL",
        "Remote Policy (typical)", "Est. Junior AI/ML Salary Range (1-3 YOE)",
        "Notes", "Tier", "Why Target This Company", "Research Status",
        "ATS", "ATS Identifier",
    ]
    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with OUT_CSV.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for company, provider, identifier, _count in resolved:
            writer.writerow({
                "Company": company,
                "Region": "",
                "Category": "",
                "Careers / Job Board URL": build_career_url(provider, identifier),
                "Remote Policy (typical)": "",
                "Est. Junior AI/ML Salary Range (1-3 YOE)": "",
                "Notes": "",
                "Tier": "",
                "Why Target This Company": "",
                "Research Status": "Verified live via resolve_new_companies.py",
                "ATS": provider,
                "ATS Identifier": identifier,
            })

    UNRESOLVED_CSV.parent.mkdir(parents=True, exist_ok=True)
    with UNRESOLVED_CSV.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Company", "Reason"])
        for company in unresolved:
            writer.writerow([company, "no live-verifiable identifier found"])
        for company, ats_raw in skipped_unsupported:
            writer.writerow([company, f"unsupported ATS: {ats_raw or '(blank)'}"])

    total_jobs = sum(c for *_r, c in resolved)
    print()
    print(f"Resolved {len(resolved)}/{len(tasks)} companies, {total_jobs} live jobs found across them.")
    print(f"Unresolved: {len(unresolved)} (see {UNRESOLVED_CSV})")
    print(f"Skipped (unsupported ATS): {len(skipped_unsupported)}")
    print(f"Wrote {OUT_CSV}")


if __name__ == "__main__":
    main()
