"""Loads config/config.yaml into typed, validated settings objects."""

from __future__ import annotations

import os
from pathlib import Path

import yaml
from pydantic import BaseModel


class ProfileConfig(BaseModel):
    # Jobs requiring at most this many years of experience are ranked
    # favorably; jobs requiring more score lower (see ranking._score_yoe).
    max_years_experience: int = 3
    preferred_countries: list[str] = []
    remote_preference: str = "soft"
    preferred_keywords: list[str] = []


class RolesConfig(BaseModel):
    include: list[str] = []
    exclude_keywords: list[str] = []
    include_internships: bool = False
    internship_keywords: list[str] = []


class RssSource(BaseModel):
    name: str
    url: str


class SourcesConfig(BaseModel):
    companies_csv: str = "data/companies.csv"
    rss: list[RssSource] = []
    apis: dict[str, str] = {}


class HttpConfig(BaseModel):
    timeout_seconds: int = 15
    max_retries: int = 3
    backoff_seconds: int = 2
    concurrency: int = 10
    rate_limit_per_host_seconds: float = 1.0
    user_agent: str = "Mozilla/5.0 (compatible; AIJobDiscoveryBot/1.0)"


class ScheduleConfig(BaseModel):
    cron: str = "30 2 * * *"


class EmailConfig(BaseModel):
    enabled: bool = True
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    sender_env_var: str = "EMAIL_SENDER"
    password_env_var: str = "EMAIL_APP_PASSWORD"
    recipient: str = ""
    top_n_in_email: int = 20
    min_stars_in_email: int = 3

    @property
    def sender(self) -> str | None:
        return os.environ.get(self.sender_env_var)

    @property
    def password(self) -> str | None:
        return os.environ.get(self.password_env_var)


class LimitsConfig(BaseModel):
    max_jobs_per_company: int = 5


class StorageConfig(BaseModel):
    db_path: str = "data/jobscraper.db"


class ReportConfig(BaseModel):
    output_dir: str = "reports"


class LoggingConfig(BaseModel):
    level: str = "INFO"
    file: str = "logs/jobscraper.log"


class Settings(BaseModel):
    profile: ProfileConfig = ProfileConfig()
    roles: RolesConfig = RolesConfig()
    sources: SourcesConfig = SourcesConfig()
    http: HttpConfig = HttpConfig()
    schedule: ScheduleConfig = ScheduleConfig()
    email: EmailConfig = EmailConfig()
    limits: LimitsConfig = LimitsConfig()
    storage: StorageConfig = StorageConfig()
    report: ReportConfig = ReportConfig()
    logging: LoggingConfig = LoggingConfig()


def load_settings(config_path: str | Path = "config/config.yaml") -> Settings:
    path = Path(config_path)
    with path.open(encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    return Settings.model_validate(raw)
