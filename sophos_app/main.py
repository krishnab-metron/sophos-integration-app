"""Entry point for Sophos App.

This script can be executed directly to produce a report
based on Sophos Central endpoint data.  It loads configuration, fetches
endpoints, classifies them according to the configured office subnets,
generates a CSV report and emails the result to the configured recipients.
"""

from __future__ import annotations

import logging
import os
import sys
from typing import List

from .config import load_config
from .client import SophosAPIClient
from .report import generate_report, classify_endpoint
from .attendance import init_db, log_attendance, get_low_office_attendance
from .emailer import send_email


def run() -> None:
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["daily", "weekly"], default="daily")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    )
    try:
        config = load_config()
    except RuntimeError as e:
        logging.getLogger(__name__).error("Configuration error: %s", e)
        sys.exit(1)
    
    if args.mode == "weekly":
        init_db()
        low_attendees = get_low_office_attendance(threshold=3)
        if not low_attendees:
            print("Everyone met the 3-day office policy this week.")
            return
        summary_path = os.path.abspath("weekly_summary.csv")
        with open(summary_path, "w", encoding="utf-8", newline="") as f:
            import csv
            writer = csv.writer(f)
            writer.writerow(["Username", "Office Days"])
            for username, count in low_attendees:
                writer.writerow([username, count])

        subject = "Weekly Attendance Summary"
        body = (
            "Weekly Summary: Employees with < 3 Office Days\n\n" +
            "\n".join(f"- {u} ({c} days)" for u, c in low_attendees)
        )
        send_email(
            smtp_server=config.email_smtp_server,
            smtp_port=config.email_smtp_port,
            username=config.email_sender,
            password=config.email_password,
            use_tls=config.smtp_use_tls,
            use_ssl=config.smtp_use_ssl,
            sender=config.email_sender,
            recipients=config.email_recipients,
            subject=subject,
            body=body,
            attachment_path=summary_path,
        )
        return

    # Initialise client and fetch endpoints
    client = SophosAPIClient(config.client_id, config.client_secret)
    logging.getLogger(__name__).info("Retrieving endpoint information...")
    fields = ["hostname", "ipv4Addresses", "lastSeenAt", "associatedPerson"]
    endpoints = list(client.list_endpoints(fields=fields, view="summary"))
    logging.getLogger(__name__).info("Fetched %d endpoints", len(endpoints))
    # Generate report
    report_path = os.path.abspath("report.csv")
    office_count, wfh_count, unknown_count = generate_report(
        endpoints=endpoints,
        office_subnet_strs=config.office_subnets,
        report_path=report_path,
    )
    
    # Record daily attendance in DB
    init_db()
    import ipaddress
    office_networks = [ipaddress.ip_network(subnet, strict=False) for subnet in config.office_subnets]
    classifications = [
        classify_endpoint(ep, office_networks)[:3]  # hostname, username, classification
        for ep in endpoints
    ]
    log_attendance(classifications)

    # Compose and send email
    subject = "Sophos Report"
    body = (
        f"Sophos Endpoint Report\n\n"
        f"Office devices: {office_count}\n"
        f"Work From Home devices: {wfh_count}\n"
        f"Unknown devices: {unknown_count}\n\n"
        "See attached CSV for details."
    )
    try:
        send_email(
            smtp_server=config.email_smtp_server,
            smtp_port=config.email_smtp_port,
            username=config.email_sender,
            password=config.email_password,
            use_tls=config.smtp_use_tls,
            use_ssl=config.smtp_use_ssl,
            sender=config.email_sender,
            recipients=config.email_recipients,
            subject=subject,
            body=body,
            attachment_path=report_path,
        )
    except Exception as exc:
        logging.getLogger(__name__).error("Failed to send email: %s", exc)


if __name__ == "__main__":
    run()