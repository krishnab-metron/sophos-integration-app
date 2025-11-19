"""Configuration utilities for the Sophos App.

This module defines a :class:`Config` dataclass to hold runtime
configuration and a :func:`load_config` helper which reads configuration
settings from environment variables.  It uses the ``python-dotenv``
library to support .env files.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import List, Optional

from dotenv import load_dotenv


@dataclass
class Config:
    """Holds configuration needed by the application."""
    client_id: str
    client_secret: str
    office_subnets: List[str]
    email_sender: str
    email_password: str
    email_smtp_server: str
    email_smtp_port: int
    email_recipients: List[str]
    smtp_use_tls: bool = True
    smtp_use_ssl: bool = False


def load_config() -> Config:
    """Load configuration from the environment."""

    load_dotenv()

    def get(name: str) -> Optional[str]:
        return os.getenv(name)

    missing = []
    client_id = get("SOPHOS_CLIENT_ID")
    client_secret = get("SOPHOS_CLIENT_SECRET")
    subnets = get("OFFICE_SUBNETS")
    email_sender = get("EMAIL_SENDER")
    email_password = get("EMAIL_PASSWORD")
    smtp_server = get("EMAIL_SMTP_SERVER")
    smtp_port = get("EMAIL_SMTP_PORT")
    recipients = get("EMAIL_RECIPIENTS")

    for key, value in {
        "SOPHOS_CLIENT_ID": client_id,
        "SOPHOS_CLIENT_SECRET": client_secret,
        "OFFICE_SUBNETS": subnets,
        "EMAIL_SENDER": email_sender,
        "EMAIL_PASSWORD": email_password,
        "EMAIL_SMTP_SERVER": smtp_server,
        "EMAIL_SMTP_PORT": smtp_port,
        "EMAIL_RECIPIENTS": recipients,
    }.items():
        if not value:
            missing.append(key)
    if missing:
        raise RuntimeError(f"Missing required environment variables: {', '.join(missing)}")

    try:
        port = int(smtp_port)
    except ValueError:
        raise RuntimeError(f"EMAIL_SMTP_PORT must be an integer, got {smtp_port}")

    subnet_list = [s.strip() for s in subnets.split(",") if s.strip()]
    recipient_list = [e.strip() for e in recipients.split(",") if e.strip()]

    return Config(
        client_id=client_id,
        client_secret=client_secret,
        office_subnets=subnet_list,
        email_sender=email_sender,
        email_password=email_password,
        email_smtp_server=smtp_server,
        email_smtp_port=port,
        email_recipients=recipient_list,
    )