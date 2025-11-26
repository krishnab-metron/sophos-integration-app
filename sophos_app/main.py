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
from .utils import format_username, build_weekly_attendance_table
from .google_sheets import update_google_sheet


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
        body = """
        <html>
        <body>
        <h2>Weekly Summary: Employees with &lt; 3 Office Days</h2>
        """ + build_weekly_attendance_table(low_attendees) + """
        </body>
        </html>
        """

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
        )
        return

    client = SophosAPIClient(config.client_id, config.client_secret)
    logging.getLogger(__name__).info("Retrieving endpoint information...")
    fields = ["hostname", "ipv4Addresses", "lastSeenAt", "associatedPerson"]
    endpoints = list(client.list_endpoints(fields=fields, view="summary"))
    logging.getLogger(__name__).info("Fetched %d endpoints", len(endpoints))

    report_path = os.path.abspath("report.csv")
    office_count, wfh_count, unknown_count = generate_report(
        endpoints=endpoints,
        office_subnet_strs=config.office_subnets,
        report_path=report_path,
    )

    init_db()
    import ipaddress
    office_networks = [ipaddress.ip_network(subnet, strict=False) for subnet in config.office_subnets]
    classifications = [
        classify_endpoint(ep, office_networks)[:3] for ep in endpoints
    ]
    log_attendance(classifications)

    # Build attendance_dict for Google Sheet
    attendance_dict = {format_username(u): c for h, u, c in classifications}
    update_google_sheet(attendance_dict, "C:/Users/krishna.balsara_metr/Downloads/sophos_app/sophos_app/credentials/sophos-integration-app-4d5e053b6446.json")

    table_rows = "\n".join(
        f"<tr><td>{format_username(u)}</td><td>{h}</td><td>{c}</td></tr>"
        for h, u, c in classifications
    )
    html_table = f"""
    <html>
    <body>
    <h2>Sophos Endpoint Report</h2>
    <p><strong>Office devices:</strong> {office_count} &nbsp;&nbsp;
       <strong>WFH devices:</strong> {wfh_count} &nbsp;&nbsp;
       <strong>Unknown:</strong> {unknown_count}</p>
    <table style='width:100%; border-collapse:collapse; font-family:sans-serif;'>
        <thead>
            <tr style='background-color:#f2f2f2;'>
                <th style='border:1px solid #ddd; padding:8px;'>Name</th>
                <th style='border:1px solid #ddd; padding:8px;'>Hostname</th>
                <th style='border:1px solid #ddd; padding:8px;'>Classification</th>
            </tr>
        </thead>
        <tbody>
            {table_rows}
        </tbody>
    </table>
    </body>
    </html>
    """

    try:
        from email.message import EmailMessage
        import smtplib

        msg = EmailMessage()
        msg["From"] = config.email_sender
        msg["To"] = ", ".join(config.email_recipients)
        msg["Subject"] = "Sophos Report"
        msg.set_content("This is an HTML email.")
        msg.add_alternative(html_table, subtype="html")

        if config.smtp_use_ssl:
            server = smtplib.SMTP_SSL(config.email_smtp_server, config.email_smtp_port)
        else:
            server = smtplib.SMTP(config.email_smtp_server, config.email_smtp_port)
            if config.smtp_use_tls:
                server.starttls()

        server.login(config.email_sender, config.email_password)
        server.send_message(msg)
        server.quit()

    except Exception as exc:
        logging.getLogger(__name__).error("Failed to send email: %s", exc)


if __name__ == "__main__":
    run()