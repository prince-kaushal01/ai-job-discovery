"""Loads the target-companies CSV (data/companies.csv) into Company objects.

The CSV's own header names are used directly here rather than requiring the
source file to be renamed/remapped:
    Company, Region, Category, Careers / Job Board URL,
    Remote Policy (typical), Est. Junior AI/ML Salary Range (1-3 YOE),
    Notes, Tier, Why Target This Company, Research Status

Two additional columns, ATS and ATS Identifier, are optional: scripts/detect_ats.py
pre-populates them so the daily run can call a company's ATS API directly
instead of fetching (and risking a block on) the company's own career page.
"""

from __future__ import annotations

import csv
import logging
from pathlib import Path

from jobscraper.models import Company

logger = logging.getLogger(__name__)

_CAREER_URL_COL = "Careers / Job Board URL"
ATS_COL = "ATS"
ATS_IDENTIFIER_COL = "ATS Identifier"


def load_companies(csv_path: str | Path) -> list[Company]:
    path = Path(csv_path)
    companies: list[Company] = []

    with path.open(encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = (row.get("Company") or "").strip()
            career_page = (row.get(_CAREER_URL_COL) or "").strip()
            if not name or not career_page:
                logger.warning("Skipping company row with missing name/URL: %r", row)
                continue

            companies.append(
                Company(
                    name=name,
                    career_page=career_page,
                    region=(row.get("Region") or "").strip(),
                    priority=(row.get("Tier") or "").strip(),
                    notes=(row.get("Notes") or "").strip(),
                    ats_provider=(row.get(ATS_COL) or "").strip() or None,
                    ats_identifier=(row.get(ATS_IDENTIFIER_COL) or "").strip() or None,
                )
            )

    logger.info("Loaded %d companies from %s", len(companies), path)
    return companies
