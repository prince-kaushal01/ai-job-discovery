#!/usr/bin/env python
"""Mark a job as applied so it is never recommended again.

Usage:
    python scripts/mark_applied.py --company "Acme Inc" --title "AI Engineer" --location "Remote, India"
    python scripts/mark_applied.py --job-hash <sha256>
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from jobscraper.config import load_settings  # noqa: E402
from jobscraper.db import Database  # noqa: E402
from jobscraper.dedupe import compute_job_hash  # noqa: E402
from jobscraper.models import Job  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default=str(REPO_ROOT / "config" / "config.yaml"))
    parser.add_argument("--job-hash", help="job_hash as stored in the jobs table")
    parser.add_argument("--company", help="Company name (used with --title/--location)")
    parser.add_argument("--title", help="Job title (used with --company/--location)")
    parser.add_argument("--location", default="", help="Job location (used with --company/--title)")
    parser.add_argument("--notes", default="", help="Optional free-text notes")
    args = parser.parse_args()

    if args.job_hash:
        job_hash = args.job_hash
    elif args.company and args.title:
        job_hash = compute_job_hash(
            Job(company_name=args.company, title=args.title, apply_url="", source="manual", location=args.location)
        )
    else:
        parser.error("Provide either --job-hash, or --company and --title")
        return

    settings = load_settings(args.config)
    with Database(settings.storage.db_path) as db:
        db.mark_applied(job_hash, notes=args.notes)

    print(f"Marked as applied: {job_hash}")


if __name__ == "__main__":
    main()
