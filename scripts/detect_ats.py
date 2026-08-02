#!/usr/bin/env python
"""Detects each company's ATS provider once and caches it in data/companies.csv.

Fetches every company's career page, sniffs it for a known ATS signature
(ats/detect.py), and writes the result into two CSV columns: ATS and
ATS Identifier. The daily pipeline (company_fetcher.fetch_company_jobs)
checks these columns first and, if set, calls that ATS's API directly
instead of fetching the company's own career page — skipping the exact
request where most bot-blocking happens.

Re-run this occasionally (e.g. monthly) to catch companies that migrate to
a different ATS; the daily run trusts whatever is cached here until then.

Usage:
    python scripts/detect_ats.py                  # detect all companies, update the CSV
    python scripts/detect_ats.py --limit 10        # only the first 10, for a quick check
"""

from __future__ import annotations

import argparse
import csv
import sys
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from jobscraper.ats.detect import detect_ats  # noqa: E402
from jobscraper.companies import ATS_COL, ATS_IDENTIFIER_COL, load_companies  # noqa: E402
from jobscraper.config import load_settings  # noqa: E402
from jobscraper.http_client import HttpClient  # noqa: E402
from jobscraper.logging_setup import setup_logging  # noqa: E402
from jobscraper.models import Company  # noqa: E402


def detect_one(client: HttpClient, company: Company) -> tuple[str, str, str]:
    """Returns (company_name, ats_provider, ats_identifier) — blanks on no match/error."""
    try:
        resp = client.get(company.career_page)
        if not resp.ok:
            return company.name, "", ""
        result = detect_ats(resp.text, resp.url)
    except Exception:
        return company.name, "", ""

    if result is None:
        return company.name, "", ""
    return company.name, result.provider, result.identifier


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default=str(REPO_ROOT / "config" / "config.yaml"))
    parser.add_argument("--limit", type=int, default=None, help="Only check the first N companies")
    args = parser.parse_args()

    settings = load_settings(args.config)
    setup_logging(settings.logging.level, settings.logging.file)

    csv_path = Path(settings.sources.companies_csv)
    companies = load_companies(csv_path)
    if args.limit is not None:
        companies = companies[: args.limit]

    client = HttpClient(
        timeout_seconds=settings.http.timeout_seconds,
        max_retries=settings.http.max_retries,
        backoff_seconds=settings.http.backoff_seconds,
        rate_limit_per_host_seconds=settings.http.rate_limit_per_host_seconds,
        user_agent=settings.http.user_agent,
    )

    total = len(companies)
    print(f"Detecting ATS for {total} companies (concurrency={settings.http.concurrency})...")
    results: dict[str, tuple[str, str]] = {}
    matched = 0
    with ThreadPoolExecutor(max_workers=settings.http.concurrency) as pool:
        futures = {pool.submit(detect_one, client, c): c for c in companies}
        for i, future in enumerate(as_completed(futures), start=1):
            name, provider, identifier = future.result()
            results[name] = (provider, identifier)
            if provider:
                matched += 1
            print(f"[{i}/{total}, {total - i} left, {matched} matched so far] {name}: {provider or '(none)'}")

    # Rewrite the CSV, updating only the ATS columns and only for rows we checked.
    with csv_path.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames or [])
        rows = list(reader)

    for col in (ATS_COL, ATS_IDENTIFIER_COL):
        if col not in fieldnames:
            fieldnames.append(col)

    updated = 0
    for row in rows:
        name = row.get("Company", "")
        if name in results:
            provider, identifier = results[name]
            row[ATS_COL] = provider
            row[ATS_IDENTIFIER_COL] = identifier
            updated += 1

    with csv_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    counts = Counter(provider for provider, _ in results.values() if provider)
    no_match = sum(1 for provider, _ in results.values() if not provider)

    print()
    print(f"Updated {updated} rows in {csv_path}")
    print("ATS breakdown:", dict(counts))
    print(f"No ATS detected (falls back to generic HTML parsing): {no_match}")


if __name__ == "__main__":
    main()
