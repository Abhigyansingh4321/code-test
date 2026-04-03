from __future__ import annotations

import argparse
import os
import sys

from jobtrackr.db import (
    VALID_STATUSES,
    add_application,
    export_csv,
    init_db,
    list_applications,
    render_table,
    stats_by_status,
)


DEFAULT_DB = os.environ.get("JOBTRACKR_DB", "jobtrackr.db")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="jobtrackr",
        description="Track your job applications from the command line.",
    )
    parser.add_argument("--db", default=DEFAULT_DB, help="Path to SQLite database file.")

    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("init", help="Initialize the database.")

    add_p = sub.add_parser("add", help="Add a new application.")
    add_p.add_argument("--company", required=True)
    add_p.add_argument("--role", required=True)
    add_p.add_argument("--status", default="applied", choices=VALID_STATUSES)
    add_p.add_argument("--date", default=None, help="Application date in YYYY-MM-DD format.")
    add_p.add_argument("--notes", default="")

    list_p = sub.add_parser("list", help="List applications.")
    list_p.add_argument("--status", choices=VALID_STATUSES)
    list_p.add_argument("--since", default=None, help="Show applications on/after YYYY-MM-DD.")

    sub.add_parser("stats", help="Show status counts.")

    export_p = sub.add_parser("export", help="Export applications to CSV.")
    export_p.add_argument("--output", default="applications_export.csv")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        if args.command == "init":
            init_db(args.db)
            print(f"Initialized database at: {args.db}")
            return 0

        if args.command == "add":
            app_id = add_application(
                args.db,
                company=args.company,
                role=args.role,
                status=args.status,
                applied_on=args.date,
                notes=args.notes,
            )
            print(f"Added application #{app_id}.")
            return 0

        if args.command == "list":
            rows = list_applications(args.db, status=args.status, since=args.since)
            print(render_table(rows))
            return 0

        if args.command == "stats":
            total, grouped = stats_by_status(args.db)
            print(f"Total applications: {total}")
            if not grouped:
                print("No status data yet.")
                return 0
            for status, count in grouped:
                print(f"- {status}: {count}")
            return 0

        if args.command == "export":
            count = export_csv(args.db, args.output)
            print(f"Exported {count} application(s) to {args.output}")
            return 0

        parser.error("Unknown command")
        return 2

    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
