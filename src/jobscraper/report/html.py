"""Renders a ReportData into the HTML report using the Jinja2 template."""

from __future__ import annotations

from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from jobscraper.report import ReportData

_TEMPLATE_DIR = Path(__file__).parent / "templates"


def render_html(data: ReportData) -> str:
    env = Environment(
        loader=FileSystemLoader(str(_TEMPLATE_DIR)),
        autoescape=select_autoescape(["html", "j2"]),
    )
    template = env.get_template("report.html.j2")
    return template.render(data=data)
