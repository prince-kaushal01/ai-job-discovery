"""Sends the daily report by email via Gmail SMTP (or any SMTP server).

Credentials come only from environment variables (see config.EmailConfig),
never hardcoded. Failure to send is logged and swallowed by the caller's
pipeline — a failed email must not fail the whole run (the report is still
saved to disk).
"""

from __future__ import annotations

import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

logger = logging.getLogger(__name__)


def send_email(
    smtp_host: str,
    smtp_port: int,
    sender: str,
    password: str,
    recipient: str,
    subject: str,
    html_body: str,
    text_body: str,
) -> bool:
    message = MIMEMultipart("alternative")
    message["Subject"] = subject
    message["From"] = sender
    message["To"] = recipient
    message.attach(MIMEText(text_body, "plain", "utf-8"))
    message.attach(MIMEText(html_body, "html", "utf-8"))

    try:
        with smtplib.SMTP(smtp_host, smtp_port, timeout=30) as server:
            server.starttls()
            server.login(sender, password)
            server.sendmail(sender, [recipient], message.as_string())
        logger.info("Email sent to %s", recipient)
        return True
    except Exception:
        logger.error("Failed to send email to %s", recipient, exc_info=True)
        return False
