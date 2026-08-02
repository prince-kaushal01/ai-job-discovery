#!/usr/bin/env python
"""Reports every company we can't reliably fetch jobs from right now, split
by why: no ATS detected at all (falls back to generic HTML parsing), an ATS
recognized but with no adapter built for it, or an ATS/adapter that's
currently erroring on fetch (bot-blocked, stale identifier, etc.).

This is a point-in-time snapshot for you to act on (fix a CSV URL, research
the right ATS, or just accept the gap) — not part of the daily pipeline.

Usage:
    python scripts/unsupported_companies_report.py
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from jobscraper.companies import load_companies  # noqa: E402
from jobscraper.company_fetcher import _ADAPTERS  # noqa: E402
from jobscraper.config import load_settings  # noqa: E402
from jobscraper.db import Database  # noqa: E402


def main() -> None:
    settings = load_settings(str(REPO_ROOT / "config" / "config.yaml"))
    companies = load_companies(settings.sources.companies_csv)

    db_status: dict[str, str] = {}
    db_path = Path(settings.storage.db_path)
    if db_path.exists():
        with Database(db_path) as db:
            for row in db.conn.execute("select name, last_status from companies"):
                db_status[row["name"]] = row["last_status"] or ""

    no_ats: list = []
    unadapted_ats: list = []
    failing: list = []

    for c in companies:
        status = db_status.get(c.name, "")
        is_error = status.startswith("error")

        if not c.ats_provider:
            no_ats.append((c, status))
        elif c.ats_provider not in _ADAPTERS:
            unadapted_ats.append((c, status))
        elif is_error:
            failing.append((c, status))

    tier_order = {"Tier 1": 0, "Tier 2": 1, "Tier 3": 2}

    def _sorted(items):
        return sorted(items, key=lambda x: (tier_order.get(x[0].priority, 9), x[0].name))

    lines = []
    lines.append("# Companies we can't reliably get jobs from right now")
    lines.append("")
    lines.append(f"Generated from {len(companies)} companies in data/companies.csv")
    lines.append(f"(DB status cross-referenced from {settings.storage.db_path} where available).")
    lines.append("")

    lines.append(f"## ATS detected but no adapter built for it ({len(unadapted_ats)})")
    lines.append("These were manually identified (e.g. from ATS_TODO.md research) but we")
    lines.append("don't have a working integration — most need a browser/paid API, so they")
    lines.append("stay generic-HTML-only unless a new adapter gets built.")
    lines.append("")
    for c, status in _sorted(unadapted_ats):
        lines.append(f"- [{c.priority}] {c.name} — ats={c.ats_provider} — {c.career_page}")
    lines.append("")

    lines.append(f"## ATS/adapter currently failing to fetch ({len(failing)})")
    lines.append("We have a real adapter for these, but the last run errored — bot-blocked,")
    lines.append("stale identifier, or the site is temporarily down. Worth checking first,")
    lines.append("these are often a quick CSV URL or identifier fix (see README).")
    lines.append("")
    for c, status in _sorted(failing):
        lines.append(f"- [{c.priority}] {c.name} — ats={c.ats_provider}/{c.ats_identifier} — {status}")
    lines.append("")

    lines.append(f"## No ATS detected at all ({len(no_ats)})")
    lines.append("Falls back to generic HTML keyword parsing, which is lower-precision and")
    lines.append("often finds 0 jobs (client-side-rendered pages, hard bot walls, or a")
    lines.append("genuinely custom hiring platform). Run scripts/detect_ats_browser.py, or")
    lines.append("check manually via ATS_TODO.md.")
    lines.append("")
    for c, status in _sorted(no_ats):
        tag = f" ({status})" if status.startswith("error") else ""
        lines.append(f"- [{c.priority}] {c.name} — {c.career_page}{tag}")

    report = "\n".join(lines) + "\n"
    print(report)

    out_path = REPO_ROOT / "UNSUPPORTED_COMPANIES.md"
    out_path.write_text(report, encoding="utf-8")
    print(f"\nAlso written to {out_path}")


if __name__ == "__main__":
    main()
