# AI Job Discovery Automation

A daily, fully-free pipeline that finds high-quality AI Engineering job
postings from ~215 target companies plus trusted public job boards, dedupes
against jobs already seen, ranks them for relevance, and emails you a report.

## What it does, every day

1. Checks every company in `data/companies.csv` (a target list, not a
   scrape-everything list) — auto-detecting Greenhouse, Lever, Ashby,
   Workday, SmartRecruiters, Teamtailor, and BambooHR job boards and calling
   each one's public API directly; falls back to a heuristic HTML parser for
   everything else.
2. Pulls jobs from RemoteOK's public API and We Work Remotely's RSS feed.
3. Filters to AI/ML engineering roles only (see `config/config.yaml`).
4. Dedupes against everything seen before, and against jobs you've marked as
   applied — nothing is ever recommended twice.
5. Ranks every job 1-5 stars based on title match, tech-stack overlap,
   remote/country fit, and years-of-experience fit.
6. Writes an HTML + Markdown report to `reports/`, and emails the top
   recommendations to you.

## Project layout

```
config/config.yaml          All tunable behavior — roles, keywords, countries, schedule, email
data/companies.csv           Your target companies (Company, Region, Careers URL, Tier, Notes, ...)
data/jobscraper.db           SQLite state: companies, jobs, applied_jobs, daily_reports
src/jobscraper/
  ats/                       One parser per ATS provider + detect.py (sniffs career pages) + generic_html.py fallback
  sources/                   RemoteOK + We Work Remotely
  filtering.py               Include/exclude role & keyword rules
  dedupe.py                  Hashing + previously-seen/applied checks
  ranking.py                 1-5 star relevance scoring
  report/                    Markdown + HTML (Jinja2) report rendering
  email_sender.py            Gmail SMTP sending
  pipeline.py                Orchestrates one full daily run
scripts/
  run_daily.py               Main entrypoint (local + GitHub Actions)
  mark_applied.py            CLI to mark a job as applied
tests/                       pytest suite with fixtures for every parser
.github/workflows/daily.yml  Runs the pipeline every day at 08:00 IST
```

## Setup

1. **Install dependencies** (Python 3.12):
   ```
   python -m venv .venv
   .venv\Scripts\activate          # Windows
   pip install -r requirements.txt
   ```

2. **Gmail App Password** (for sending the report):
   - Enable 2-Step Verification on the sending Gmail account.
   - Google Account → Security → App passwords → generate one for "Mail".
   - Copy `.env.example` to `.env` and fill in `EMAIL_SENDER` /
     `EMAIL_APP_PASSWORD`. `.env` is gitignored — never commit it.

3. **Review `config/config.yaml`**: preferred countries, remote preference,
   tech-stack keywords, role include/exclude lists, and the email recipient
   all live here.

4. **Run it**:
   ```
   python scripts/run_daily.py --limit 10 --no-email   # smoke test, no email
   python scripts/run_daily.py                          # full run, sends email
   ```

5. **Mark a job as applied** so it's never recommended again:
   ```
   python scripts/mark_applied.py --company "Acme Inc" --title "AI Engineer" --location "Remote, India"
   ```

6. **Run tests**:
   ```
   pytest -q
   ```

## Deploying the daily GitHub Actions run

1. Push this repo to GitHub.
2. In the repo's Settings → Secrets and variables → Actions, add:
   - `EMAIL_SENDER`
   - `EMAIL_APP_PASSWORD`
3. The workflow (`.github/workflows/daily.yml`) runs every day at 08:00 IST
   (`30 2 * * *` UTC) and can also be triggered manually from the Actions tab
   (`workflow_dispatch`).
4. After each run, the workflow commits `data/jobscraper.db` and `reports/`
   back to the repo — this is how state persists across GitHub Actions' own
   ephemeral runners without needing a cloud database.

## Design decisions

- **ATS detection sniffs the fetched page, not the CSV URL.** Almost none of
  the 215 target companies link directly to a `greenhouse.io`/`lever.co`
  URL — they link to their own domain (e.g. `careers.adobe.com`), which
  embeds or redirects to the actual ATS. `ats/detect.py` regex-scans the
  fetched HTML and the final resolved URL for ATS signatures, then hands off
  to that provider's dedicated adapter, which calls the ATS's public JSON
  API directly (fast, structured, no HTML scraping needed for those ~7
  providers).
- **Static HTML fetching, no headless browser.** Some career sites render
  their job list entirely client-side via JavaScript, so neither ATS
  detection nor the generic fallback will see anything on those pages. This
  is a deliberate simplicity/reliability tradeoff — running a browser for
  215 companies daily, for free, isn't practical. Companies like this will
  simply contribute 0 jobs; check `companies.last_status` in the DB to see
  which ones.
- **RemoteOK + We Work Remotely only for Source B, for now.** Wellfound and
  YC Jobs require login or defeat non-browser scraping with anti-bot
  measures; rather than build something brittle, `sources/` is a small
  plugin interface (`fetch_jobs(client) -> list[Job]`) so a new source is a
  single new file plus one line in `pipeline.py`.
- **SQLite file committed back to the repo** is the persistence layer.
  There's no cloud database per the requirements, and GitHub Actions
  runners are ephemeral, so the workflow's last step commits the updated
  `.db` file and the day's reports back to `main`.
- **One bad company never aborts the run.** Every fetch — company career
  page, ATS API call, RSS/API source — is wrapped so exceptions are logged
  and turned into an empty result; `pipeline.py` tracks
  `companies_failed` for visibility without stopping the other 214.
- **Ranking is a transparent weighted score**, not a black box: title match
  (0-40), tech-stack overlap (0-25), remote fit (0-15), country fit (0-10),
  YOE fit (0-10) → mapped to 1-5 stars. The `rank_reason` string surfaces
  which factors fired, and the "why it matches" field in the email is built
  directly from it.

## Future extensibility (not implemented yet, designed for)

The codebase is intentionally structured so these can be added without
touching the rest of the pipeline:

- **Resume matching**: a `resume.py` module could embed/keyword-match a
  resume file against `job.description` and feed an extra score into
  `ranking.score_job`.
- **AI-based ranking**: swap the scoring function in `ranking.py` for an
  LLM-based scorer behind the same `score_job(job, profile, roles)` signature.
- **Cover letter / interview question generation**: new modules under a
  `generation/` package, using the full `job.description` already stored in
  SQLite.
- **Slack / Discord / Telegram notifications**: new modules parallel to
  `email_sender.py`, each implementing a `send(report_data) -> bool` style
  interface, wired into `pipeline.py` next to the existing email step.

## Known limitations

- Generic HTML fallback parsing is heuristic (keyword-matches anchor text)
  and has lower precision than the dedicated ATS adapters — expected, given
  it covers arbitrary custom career pages.
- Workday detection/parsing targets the public CXS search endpoint most
  Workday career sites use; some tenants customize this enough that the
  adapter returns nothing for them (logged, not fatal).
- YC Jobs and Wellfound are not yet implemented as sources (see above).
