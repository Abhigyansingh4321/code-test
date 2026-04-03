from __future__ import annotations

import csv
import sqlite3
from datetime import date, datetime
from pathlib import Path
from typing import Iterable

VALID_STATUSES = ("wishlist", "applied", "interview", "offer", "rejected")


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS applications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company TEXT NOT NULL,
    role TEXT NOT NULL,
    status TEXT NOT NULL,
    applied_on TEXT NOT NULL,
    notes TEXT,
    created_at TEXT NOT NULL
);
"""


def _connect(db_path: str) -> sqlite3.Connection:
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: str) -> None:
    with _connect(db_path) as conn:
        conn.executescript(SCHEMA_SQL)


def validate_status(status: str) -> str:
    if status not in VALID_STATUSES:
        raise ValueError(
            f"Invalid status '{status}'. Expected one of: {', '.join(VALID_STATUSES)}"
        )
    return status


def validate_date_iso(date_value: str) -> str:
    try:
        date.fromisoformat(date_value)
    except ValueError as exc:
        raise ValueError("Date must be in YYYY-MM-DD format.") from exc
    return date_value


def add_application(
    db_path: str,
    *,
    company: str,
    role: str,
    status: str = "applied",
    applied_on: str | None = None,
    notes: str = "",
) -> int:
    init_db(db_path)
    status = validate_status(status)
    if applied_on is None:
        applied_on = date.today().isoformat()
    validate_date_iso(applied_on)

    with _connect(db_path) as conn:
        cur = conn.execute(
            """
            INSERT INTO applications (company, role, status, applied_on, notes, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (company.strip(), role.strip(), status, applied_on, notes.strip(), datetime.utcnow().isoformat()),
        )
        return int(cur.lastrowid)


def list_applications(
    db_path: str,
    *,
    status: str | None = None,
    since: str | None = None,
) -> list[sqlite3.Row]:
    init_db(db_path)
    query = "SELECT id, company, role, status, applied_on, notes FROM applications"
    clauses: list[str] = []
    params: list[str] = []

    if status:
        validate_status(status)
        clauses.append("status = ?")
        params.append(status)
    if since:
        validate_date_iso(since)
        clauses.append("applied_on >= ?")
        params.append(since)

    if clauses:
        query += " WHERE " + " AND ".join(clauses)
    query += " ORDER BY applied_on DESC, id DESC"

    with _connect(db_path) as conn:
        return list(conn.execute(query, params).fetchall())


def stats_by_status(db_path: str) -> tuple[int, list[tuple[str, int]]]:
    init_db(db_path)
    with _connect(db_path) as conn:
        total = int(conn.execute("SELECT COUNT(*) FROM applications").fetchone()[0])
        rows = conn.execute(
            """
            SELECT status, COUNT(*) AS count
            FROM applications
            GROUP BY status
            ORDER BY count DESC, status ASC
            """
        ).fetchall()

    ordered = [(row[0], int(row[1])) for row in rows]
    return total, ordered


def export_csv(db_path: str, output_path: str) -> int:
    rows = list_applications(db_path)
    fieldnames = ["id", "company", "role", "status", "applied_on", "notes"]
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row[key] for key in fieldnames})
    return len(rows)


def render_table(rows: Iterable[sqlite3.Row]) -> str:
    rows = list(rows)
    if not rows:
        return "No applications found."

    headers = ["ID", "Company", "Role", "Status", "Applied On", "Notes"]
    data = [
        [
            str(r["id"]),
            r["company"],
            r["role"],
            r["status"],
            r["applied_on"],
            r["notes"] or "",
        ]
        for r in rows
    ]

    widths = [len(h) for h in headers]
    for row in data:
        for i, value in enumerate(row):
            widths[i] = max(widths[i], len(value))

    sep = "-+-".join("-" * w for w in widths)
    top = " | ".join(h.ljust(widths[i]) for i, h in enumerate(headers))
    body = [" | ".join(col.ljust(widths[i]) for i, col in enumerate(row)) for row in data]
    return "\n".join([top, sep, *body])
