#!/usr/bin/env python
"""Smoke-tests every ATS adapter against real companies from data/companies.csv
and reports whether each one is actually returning jobs right now.

For every ATS provider that has at least one company with a cached
(ATS, ATS Identifier) pair in the CSV, this calls that adapter directly
(bypassing career-page fetch + detection, same as the "ok:cached" path in
company_fetcher.py) for up to --per-provider companies, and records job
count / latency / error per company.

Writes a row-per-company CSV report plus a per-ATS summary to stdout.

Usage:
    python scripts/test_ats_pipeline.py                    # 5 companies per ATS
    python scripts/test_ats_pipeline.py --per-provider 3
    python scripts/test_ats_pipeline.py --out reports/ats_test.csv
"""

from __future__ import annotations

import argparse
import csv
import sys
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from jobscraper.ats import (  # noqa: E402
    ashby,
    bamboohr,
    greenhouse,
    lever,
    oracle_recruiting,
    recruitee,
    smartrecruiters,
    teamtailor,
    workable,
    workday,
)
from jobscraper.companies import load_companies  # noqa: E402
from jobscraper.config import load_settings  # noqa: E402
from jobscraper.http_client import HttpClient  # noqa: E402
from jobscraper.logging_setup import setup_logging  # noqa: E402
from jobscraper.models import Company  # noqa: E402

_ADAPTERS = {
    "greenhouse": greenhouse.fetch_jobs,
    "lever": lever.fetch_jobs,
    "ashby": ashby.fetch_jobs,
    "workday": workday.fetch_jobs,
    "smartrecruiters": smartrecruiters.fetch_jobs,
    "teamtailor": teamtailor.fetch_jobs,
    "bamboohr": bamboohr.fetch_jobs,
    "workable": workable.fetch_jobs,
    "recruitee": recruitee.fetch_jobs,
    "oracle_recruiting": oracle_recruiting.fetch_jobs,
}


@dataclass
class AtsCheckResult:
    ats_provider: str
    company_name: str
    ats_identifier: str
    status: str  # "ok" | "error"
    job_count: int
    elapsed_seconds: float
    sample_title: str
    error: str


def run_one(client: HttpClient, provider: str, company: Company) -> AtsCheckResult:
    adapter = _ADAPTERS[provider]
    start = time.monotonic()
    try:
        jobs = adapter(client, company.ats_identifier, company.name)
        elapsed = time.monotonic() - start
        sample = jobs[0].title if jobs else ""
        return AtsCheckResult(
            provider, company.name, company.ats_identifier or "", "ok", len(jobs), elapsed, sample, ""
        )
    except Exception as exc:
        elapsed = time.monotonic() - start
        return AtsCheckResult(
            provider,
            company.name,
            company.ats_identifier or "",
            "error",
            0,
            elapsed,
            "",
            f"{exc.__class__.__name__}: {exc}",
        )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default=str(REPO_ROOT / "config" / "config.yaml"))
    parser.add_argument(
        "--per-provider", type=int, default=5, help="Max companies to test per ATS provider"
    )
    parser.add_argument(
        "--out", default=str(REPO_ROOT / "reports" / "ats_test_results.csv"),
        help="Where to write the per-company CSV report",
    )
    args = parser.parse_args()

    settings = load_settings(args.config)
    setup_logging(settings.logging.level, settings.logging.file)

    companies = load_companies(settings.sources.companies_csv)

    by_provider: dict[str, list[Company]] = defaultdict(list)
    for c in companies:
        if c.ats_provider and c.ats_identifier and c.ats_provider in _ADAPTERS:
            by_provider[c.ats_provider].append(c)

    if not by_provider:
        print("No companies in the CSV have a cached ATS provider + identifier. Run scripts/detect_ats.py first.")
        return

    to_test: list[tuple[str, Company]] = []
    for provider, cs in sorted(by_provider.items()):
        for c in cs[: args.per_provider]:
            to_test.append((provider, c))

    print(f"Testing {len(to_test)} companies across {len(by_provider)} ATS providers "
          f"(up to {args.per_provider} each)...")
    untested = _ADAPTERS.keys() - by_provider.keys()
    if untested:
        print(f"(No cached companies for: {', '.join(sorted(untested))} — skipped, not tested)")

    client = HttpClient(
        timeout_seconds=settings.http.timeout_seconds,
        max_retries=settings.http.max_retries,
        backoff_seconds=settings.http.backoff_seconds,
        rate_limit_per_host_seconds=settings.http.rate_limit_per_host_seconds,
        user_agent=settings.http.user_agent,
    )

    results: list[AtsCheckResult] = []
    with ThreadPoolExecutor(max_workers=settings.http.concurrency) as pool:
        futures = {pool.submit(run_one, client, provider, c): (provider, c) for provider, c in to_test}
        for i, future in enumerate(as_completed(futures), start=1):
            result = future.result()
            results.append(result)
            marker = "OK" if result.status == "ok" else "FAIL"
            detail = f"{result.job_count} jobs" if result.status == "ok" else result.error
            print(f"[{i}/{len(to_test)}] {marker:4} {result.ats_provider:17} {result.company_name}: {detail}")

    results.sort(key=lambda r: (r.ats_provider, r.company_name))

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(
            ["ats_provider", "company_name", "ats_identifier", "status", "job_count",
             "elapsed_seconds", "sample_title", "error"]
        )
        for r in results:
            writer.writerow(
                [r.ats_provider, r.company_name, r.ats_identifier, r.status, r.job_count,
                 f"{r.elapsed_seconds:.2f}", r.sample_title, r.error]
            )

    print()
    print(f"Wrote {len(results)} rows to {out_path}")
    print()
    print(f"{'ATS':17} {'tested':>6} {'ok':>4} {'failed':>6} {'total jobs':>10} {'avg jobs/co':>11}")
    for provider in sorted(by_provider):
        rows = [r for r in results if r.ats_provider == provider]
        ok_rows = [r for r in rows if r.status == "ok"]
        total_jobs = sum(r.job_count for r in ok_rows)
        avg_jobs = total_jobs / len(ok_rows) if ok_rows else 0.0
        failed = len(rows) - len(ok_rows)
        print(f"{provider:17} {len(rows):>6} {len(ok_rows):>4} {failed:>6} {total_jobs:>10} {avg_jobs:>11.1f}")

    failures = [r for r in results if r.status == "error"]
    if failures:
        print()
        print("Failures:")
        for r in failures:
            print(f"  {r.ats_provider} / {r.company_name}: {r.error}")

    zero_job_ok = [r for r in results if r.status == "ok" and r.job_count == 0]
    if zero_job_ok:
        print()
        print("Returned 0 jobs (no error, but worth checking — identifier may be stale):")
        for r in zero_job_ok:
            print(f"  {r.ats_provider} / {r.company_name} ({r.ats_identifier})")


if __name__ == "__main__":
    main()
