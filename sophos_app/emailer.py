"""Email sending utilities.

This module defines a function to send an email with an optional attachment
using the ``smtplib`` and ``email.message`` libraries.  TLS or SSL
connections are supported based on the provided configuration.
"""

from __future__ import annotations

import os
import logging
from typing import List, Optional

from email.message import EmailMessage
import smtplib


LOGGER = logging.getLogger(__name__)


def send_email(
    smtp_server: str,
    smtp_port: int,
    username: str,
    password: str,
    use_tls: bool,
    use_ssl: bool,
    sender: str,
    recipients: List[str],
    subject: str,
    body: str,
    attachment_path: Optional[str] = None,
) -> None:
    """Send an email with an optional file attachment. """

    msg = EmailMessage()
    msg["From"] = sender
    msg["To"] = ", ".join(recipients)
    msg["Subject"] = subject
    msg.set_content("This email requires an HTML-compatible client.")
    msg.add_alternative(body, subtype="html")
    # Attach file if provided
    if attachment_path:
        with open(attachment_path, "rb") as f:
            payload = f.read()
        filename = os.path.basename(attachment_path)

        msg.add_attachment(
            payload,
            maintype="text",
            subtype="csv",
            filename=filename,
        )
    # Connect and send
    if use_ssl:
        server = smtplib.SMTP_SSL(smtp_server, smtp_port)
    else:
        server = smtplib.SMTP(smtp_server, smtp_port)
        if use_tls:
            server.starttls()
    try:
        server.login(username, password)
        server.send_message(msg)
        LOGGER.info("Mail sent to %s", ", ".join(recipients))
    finally:
        server.quit()