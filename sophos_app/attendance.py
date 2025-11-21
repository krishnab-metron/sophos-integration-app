"""Attendance tracking utilities using SQLite.

This module provides functions to log daily classifications and
generate a weekly summary report from stored data.
"""

import sqlite3
from datetime import datetime, date, timedelta
from typing import List, Tuple


DB_PATH = "attendance.db"


def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            '''CREATE TABLE IF NOT EXISTS attendance (
                date TEXT,
                username TEXT,
                hostname TEXT,
                classification TEXT
            )'''
        )


def log_attendance(classifications: List[Tuple[str, str, str]]):
    """Insert today's classifications into the attendance database.

    Args:
        classifications: List of (hostname, username, classification) tuples
    """
    today = date.today().isoformat()
    with sqlite3.connect(DB_PATH) as conn:
        conn.executemany(
            "INSERT INTO attendance (date, username, hostname, classification) VALUES (?, ?, ?, ?)",
            [(today, user, host, status) for host, user, status in classifications]
        )

def get_low_office_attendance(threshold: int = 3) -> List[Tuple[str, int]]:
    """Return list of usernames with < threshold office days this week, including 0."""
    today = date.today()
    iso_year, iso_week, _ = today.isocalendar()
    monday = datetime.strptime(f"{iso_year}-W{iso_week - 1}-1", "%G-W%V-%u").date()

    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()

        # Get all users who appeared this week
        cursor.execute(
            '''SELECT DISTINCT username
               FROM attendance
               WHERE date BETWEEN ? AND ?''',
            (monday.isoformat(), today.isoformat())
        )
        all_users = [row[0] for row in cursor.fetchall()]

        # Get number of Office days per user
        cursor.execute(
            '''SELECT username, COUNT(DISTINCT date)
               FROM attendance
               WHERE classification = 'Office'
               AND date BETWEEN ? AND ?
               GROUP BY username''',
            (monday.isoformat(), today.isoformat())
        )
        office_counts = dict(cursor.fetchall())

        # Return users who have < threshold Office days, including 0
        return [(user, office_counts.get(user, 0)) for user in all_users if office_counts.get(user, 0) < threshold]