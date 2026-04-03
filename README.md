# JobTrackr CLI

A lightweight, portfolio-ready Python CLI app for tracking job applications using SQLite.

## Why this project looks good on a resume

- **Real-world problem**: manage applications, statuses, and timelines.
- **Production-style structure**: modular package, tests, and clear CLI interface.
- **No heavy dependencies**: built with Python standard library (`argparse`, `sqlite3`, `csv`).
- **Data portability**: export your tracker data to CSV.

## Features

- Initialize a local SQLite database
- Add job applications with metadata (company, role, status, date, notes)
- List applications with optional filters
- View status statistics
- Export all records to CSV

## Quickstart

```bash
python -m jobtrackr.cli init
python -m jobtrackr.cli add --company "OpenAI" --role "Software Engineer" --status applied --date 2026-04-03 --notes "Applied via careers page"
python -m jobtrackr.cli list
python -m jobtrackr.cli stats
python -m jobtrackr.cli export --output applications.csv
```

You can optionally choose a custom DB location:

```bash
python -m jobtrackr.cli --db ./data/my_jobs.db init
```

## Commands

### `init`
Creates the applications table if it doesn't exist.

### `add`
Required:
- `--company`
- `--role`

Optional:
- `--status` (`wishlist`, `applied`, `interview`, `offer`, `rejected`) default: `applied`
- `--date` (YYYY-MM-DD) default: today
- `--notes`

### `list`
Optional filters:
- `--status` one of valid statuses
- `--since` date in YYYY-MM-DD (show applications on or after this date)

### `stats`
Shows total applications and count by status.

### `export`
- `--output` path to CSV file (default: `applications_export.csv`)

## Run tests

```bash
python -m unittest discover -s tests -v
```

## Repository name suggestion

A strong name for GitHub and resume use:

- **`jobtrackr-cli`** (recommended)
- `job-application-tracker`
- `career-pipeline-cli`

If you want, I can also prepare a one-line resume bullet for this project.
