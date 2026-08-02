#!/usr/bin/env python
"""Main entrypoint: runs one full daily job-discovery pass.

Usage:
    python scripts/run_daily.py                  # full run, sends email
    python scripts/run_daily.py --limit 5         # only check the first 5 companies
    python scripts/run_daily.py --no-email        # generate reports but skip sending
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from dotenv import load_dotenv  # noqa: E402

from jobscraper.config import load_settings  # noqa: E402
from jobscraper.db import Database  # noqa: E402
from jobscraper.logging_setup import setup_logging  # noqa: E402
from jobscraper.pipeline import run_pipeline  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default=str(REPO_ROOT / "config" / "config.yaml"))
    parser.add_argument("--limit", type=int, default=None, help="Only check the first N companies")
    parser.add_argument("--no-email", action="store_true", help="Skip sending the email report")
    args = parser.parse_args()

    load_dotenv(REPO_ROOT / ".env")

    settings = load_settings(args.config)
    setup_logging(settings.logging.level, settings.logging.file)

    with Database(settings.storage.db_path) as db:
        report = run_pipeline(
            settings, db, company_limit=args.limit, send_email_flag=not args.no_email
        )

    print(
        f"Run complete: {report.total_jobs_found} total jobs, "
        f"{report.new_jobs_found} new, {len(report.recommendations)} recommended."
    )


if __name__ == "__main__":
    main()
