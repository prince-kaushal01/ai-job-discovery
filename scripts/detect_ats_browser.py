#!/usr/bin/env python
"""Thorough ATS re-check using a real (headless) browser via Playwright.

The plain detect_ats.py only fetches the raw HTTP response for a company's
career page and sniffs the static HTML. That misses two common real-world
cases:
  1. The ATS is embedded via client-side JS (iframe/widget) that only
     appears in the DOM after the page renders.
  2. The career URL in the CSV is a marketing landing page; the actual job
     board only shows up after clicking "See open positions" or similar,
     landing on a different URL (e.g. hubspot.com/careers -> .../careers/jobs).

This script renders each company's page with a real browser, checks the
rendered DOM, and — if nothing matches — follows the most likely "view
jobs" link one hop and checks again. It's a one-off/occasional research
tool (like detect_ats.py), not part of the daily pipeline: rendering 215
pages with a browser is slow and unnecessary once the ATS is cached.

Usage:
    python scripts/detect_ats_browser.py                 # only re-check companies with no ATS yet
    python scripts/detect_ats_browser.py --all            # re-check every company, even ones already matched
    python scripts/detect_ats_browser.py --limit 20        # only the first N (of whichever set above)
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
from collections import Counter
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

import requests
from playwright.sync_api import Browser, sync_playwright  # noqa: E402

from jobscraper.ats.detect import detect_ats  # noqa: E402
from jobscraper.companies import ATS_COL, ATS_IDENTIFIER_COL, load_companies  # noqa: E402
from jobscraper.config import load_settings  # noqa: E402
from jobscraper.models import Company  # noqa: E402

# Some custom career sites render Greenhouse job data through their own UI,
# server-side-proxying Greenhouse's API and never literally linking
# boards.greenhouse.io/boards-api.greenhouse.io anywhere on the page (e.g.
# Stripe: raw JSON with "greenhouseId" fields, no board URL in sight). When
# that signal is present, guess the board token from the company name and
# verify it against the real public API before accepting — never guess blind.
_HEADLESS_SIGNAL_RE = re.compile(r'"greenhouseId"\s*:')


def _slugify_company_name(name: str) -> str:
    return re.sub(r"[^a-z0-9]", "", name.lower())


def _verify_greenhouse_guess(company_name: str) -> str | None:
    guess = _slugify_company_name(company_name)
    if not guess:
        return None
    try:
        resp = requests.get(
            f"https://boards-api.greenhouse.io/v1/boards/{guess}/jobs", timeout=10
        )
        if resp.status_code == 200 and resp.json().get("jobs"):
            return guess
    except Exception:
        pass
    return None

_JOBS_LINK_RE = re.compile(
    r"/(jobs|careers?/(jobs|search|open)|positions|openings|opportunit|search-?jobs|hiring)",
    re.IGNORECASE,
)
_JOBS_TEXT_RE = re.compile(
    r"open (role|position|job)|view (job|role|position)|see (job|role|position|opening)|"
    r"explore (job|career|role|opportunit)|current opening|browse job|search job|"
    r"we.?re hiring|explore opportunit|all open",
    re.IGNORECASE,
)
_SKIP_LINK_RE = re.compile(
    r"(blog|about|contact|press|investor|privacy|legal|help|support|community|"
    r"academy|docs|facebook|twitter|linkedin|instagram|youtube|mailto:|tel:)",
    re.IGNORECASE,
)


def _rank_candidate_links(links: list[str], current_url: str) -> list[str]:
    seen: set[str] = set()
    ranked: list[str] = []
    for href in links:
        if not href or href == current_url or href in seen:
            continue
        if _SKIP_LINK_RE.search(href):
            continue
        if _JOBS_LINK_RE.search(href):
            seen.add(href)
            ranked.append(href)
    return ranked[:2]


def _try_click_candidates(page, current_url: str) -> str | None:
    """Clicks up to 2 elements whose visible text suggests "view jobs"
    (handles client-side-routed SPA buttons that have no real href)."""
    texts = page.eval_on_selector_all(
        "a, button",
        "els => els.map(e => e.innerText ? e.innerText.trim() : '').filter(t => t.length > 0 && t.length < 60)",
    )
    candidates = [t for t in dict.fromkeys(texts) if _JOBS_TEXT_RE.search(t)][:2]

    for text in candidates:
        try:
            locator = page.locator(f"text={text}").first
            locator.click(timeout=5000)
        except Exception:
            continue
        page.wait_for_timeout(2500)
        if page.url != current_url:
            return page.content()
        html = page.content()
        result = detect_ats(html, page.url)
        if result is not None:
            return html
    return None


def check_one(browser: Browser, company: Company) -> tuple[str, str, str, str]:
    """Returns (company_name, ats_provider, ats_identifier, note)."""
    page = browser.new_page()
    seen_html: list[str] = []
    try:
        try:
            page.goto(company.career_page, wait_until="load", timeout=20000)
        except Exception as exc:
            return company.name, "", "", f"goto failed: {exc.__class__.__name__}"

        page.wait_for_timeout(2000)
        html = page.content()
        seen_html.append(html)
        result = detect_ats(html, page.url)
        if result is not None:
            return company.name, result.provider, result.identifier, "found on landing page"

        landing_url = page.url

        # 1. Follow plain <a href> links that look like a jobs page.
        links = page.eval_on_selector_all("a[href]", "els => els.map(e => e.href)")
        for candidate in _rank_candidate_links(links, landing_url):
            try:
                page.goto(candidate, wait_until="load", timeout=15000)
            except Exception:
                continue
            page.wait_for_timeout(2000)
            html2 = page.content()
            seen_html.append(html2)
            result2 = detect_ats(html2, page.url)
            if result2 is not None:
                return company.name, result2.provider, result2.identifier, f"found after following link {candidate}"

        # 2. Click SPA buttons with no real href ("Open roles", "See all
        #    open positions") that navigate/route client-side instead.
        try:
            page.goto(landing_url, wait_until="load", timeout=15000)
            page.wait_for_timeout(1500)
        except Exception:
            pass
        clicked_html = _try_click_candidates(page, landing_url)
        if clicked_html is not None:
            seen_html.append(clicked_html)
            result3 = detect_ats(clicked_html, page.url)
            if result3 is not None:
                return company.name, result3.provider, result3.identifier, f"found after clicking button -> {page.url}"

        # 3. Last resort: some sites proxy Greenhouse server-side and never
        #    link boards.greenhouse.io anywhere, but leave "greenhouseId"
        #    fields in embedded JSON. Guess the board token from the company
        #    name and verify against the real public API before accepting.
        if any(_HEADLESS_SIGNAL_RE.search(h) for h in seen_html):
            guess = _verify_greenhouse_guess(company.name)
            if guess:
                return company.name, "greenhouse", guess, "found via verified headless-Greenhouse guess"

        return company.name, "", "", "no match after following links/buttons"
    finally:
        page.close()


def _write_single_result(csv_path: Path, company_name: str, provider: str, identifier: str) -> None:
    """Re-reads/updates/writes just one row immediately, so a match found
    early in a long run survives even if the run is later interrupted."""
    with csv_path.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames or [])
        rows = list(reader)

    for col in (ATS_COL, ATS_IDENTIFIER_COL):
        if col not in fieldnames:
            fieldnames.append(col)

    for row in rows:
        if row.get("Company") == company_name:
            row[ATS_COL] = provider
            row[ATS_IDENTIFIER_COL] = identifier
            break

    with csv_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default=str(REPO_ROOT / "config" / "config.yaml"))
    parser.add_argument("--all", action="store_true", help="Re-check every company, not just blank-ATS ones")
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()

    settings = load_settings(args.config)
    csv_path = Path(settings.sources.companies_csv)
    companies = load_companies(csv_path)

    if not args.all:
        companies = [c for c in companies if not c.ats_provider]
    if args.limit is not None:
        companies = companies[: args.limit]

    total = len(companies)
    print(f"Browser-checking {total} companies. Each match is written to the CSV")
    print("immediately, so you can safely Ctrl+C at any point without losing progress.")
    print()

    matched = 0
    matched_counts: Counter = Counter()

    with sync_playwright() as p:
        browser = p.chromium.launch()
        try:
            for i, company in enumerate(companies, start=1):
                name, provider, identifier, note = check_one(browser, company)
                if provider:
                    matched += 1
                    matched_counts[provider] += 1
                    _write_single_result(csv_path, name, provider, identifier)

                done = i
                left = total - i
                print(
                    f"[{done}/{total}, {left} left, {matched} matched so far] "
                    f"{name}: {provider or '(none)'} ({note})"
                )
        finally:
            browser.close()

    print()
    print(f"Done. {matched} new matches out of {total} checked.")
    print("New ATS matches found:", dict(matched_counts))


if __name__ == "__main__":
    main()
