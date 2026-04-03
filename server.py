from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from email.utils import formatdate
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse


HOST = "127.0.0.1"
PORT = 8000
BASE_DIR = Path(__file__).parent
STATIC_DIR = BASE_DIR / "static"
DB_PATH = BASE_DIR / "app.db"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def get_connection() -> sqlite3.Connection:
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def init_db() -> None:
    with get_connection() as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                detail TEXT NOT NULL DEFAULT '',
                due_date TEXT NOT NULL DEFAULT '',
                priority TEXT NOT NULL DEFAULT 'medium',
                status TEXT NOT NULL DEFAULT 'todo',
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS leads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                company TEXT NOT NULL DEFAULT '',
                email TEXT NOT NULL DEFAULT '',
                stage TEXT NOT NULL DEFAULT 'new',
                note TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS activity_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                item_type TEXT NOT NULL,
                item_id INTEGER NOT NULL,
                action TEXT NOT NULL,
                message TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            """
        )
        seed_data(connection)


def seed_data(connection: sqlite3.Connection) -> None:
    task_count = connection.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]
    lead_count = connection.execute("SELECT COUNT(*) FROM leads").fetchone()[0]

    if task_count == 0:
        now = utc_now()
        connection.executemany(
            """
            INSERT INTO tasks (title, detail, due_date, priority, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    "Review onboarding flow",
                    "Tighten first-run copy and remove dead-end steps before release.",
                    "2026-04-05",
                    "high",
                    "in_progress",
                    now,
                ),
                (
                    "Ship weekly operations report",
                    "Summarize conversion, response time, and delivery risk for this week.",
                    "2026-04-06",
                    "medium",
                    "todo",
                    now,
                ),
                (
                    "Archive completed sprint tickets",
                    "Move closed items out of the active board and update labels.",
                    "2026-04-02",
                    "low",
                    "done",
                    now,
                ),
            ],
        )

    if lead_count == 0:
        now = utc_now()
        connection.executemany(
            """
            INSERT INTO leads (name, company, email, stage, note, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    "Aarav Kapoor",
                    "Northstar Labs",
                    "aarav@northstar.example",
                    "qualified",
                    "Interested in a pilot deployment this quarter.",
                    now,
                ),
                (
                    "Meera Shah",
                    "Bloomline Studio",
                    "meera@bloomline.example",
                    "proposal",
                    "Requested a pricing breakdown and onboarding timeline.",
                    now,
                ),
            ],
        )

    activity_count = connection.execute("SELECT COUNT(*) FROM activity_log").fetchone()[0]
    if activity_count == 0:
        rows = connection.execute("SELECT id, title FROM tasks ORDER BY id").fetchall()
        for row in rows:
            log_activity(
                connection,
                item_type="task",
                item_id=row["id"],
                action="seeded",
                message=f"Seeded task: {row['title']}",
            )
        rows = connection.execute("SELECT id, name FROM leads ORDER BY id").fetchall()
        for row in rows:
            log_activity(
                connection,
                item_type="lead",
                item_id=row["id"],
                action="seeded",
                message=f"Seeded lead: {row['name']}",
            )


def log_activity(
    connection: sqlite3.Connection,
    *,
    item_type: str,
    item_id: int,
    action: str,
    message: str,
) -> None:
    connection.execute(
        """
        INSERT INTO activity_log (item_type, item_id, action, message, created_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (item_type, item_id, action, message, utc_now()),
    )


def serialize_task(row: sqlite3.Row) -> dict[str, str | int]:
    return {
        "id": row["id"],
        "title": row["title"],
        "detail": row["detail"],
        "dueDate": row["due_date"],
        "priority": row["priority"],
        "status": row["status"],
        "createdAt": row["created_at"],
    }


def serialize_lead(row: sqlite3.Row) -> dict[str, str | int]:
    return {
        "id": row["id"],
        "name": row["name"],
        "company": row["company"],
        "email": row["email"],
        "stage": row["stage"],
        "note": row["note"],
        "createdAt": row["created_at"],
    }


def serialize_activity(row: sqlite3.Row) -> dict[str, str | int]:
    return {
        "id": row["id"],
        "itemType": row["item_type"],
        "itemId": row["item_id"],
        "action": row["action"],
        "message": row["message"],
        "createdAt": row["created_at"],
    }


def build_snapshot(connection: sqlite3.Connection) -> dict[str, object]:
    tasks = [
        serialize_task(row)
        for row in connection.execute("SELECT * FROM tasks ORDER BY created_at DESC, id DESC")
    ]
    leads = [
        serialize_lead(row)
        for row in connection.execute("SELECT * FROM leads ORDER BY created_at DESC, id DESC")
    ]
    activity = [
        serialize_activity(row)
        for row in connection.execute(
            "SELECT * FROM activity_log ORDER BY created_at DESC, id DESC LIMIT 12"
        )
    ]

    summary = {
        "taskCount": len(tasks),
        "openTaskCount": sum(1 for task in tasks if task["status"] != "done"),
        "highPriorityCount": sum(1 for task in tasks if task["priority"] == "high"),
        "leadCount": len(leads),
        "activePipelineCount": sum(1 for lead in leads if lead["stage"] != "won"),
    }

    return {
        "status": "ok",
        "serverTime": utc_now(),
        "summary": summary,
        "tasks": tasks,
        "leads": leads,
        "activity": activity,
    }


class AppHandler(BaseHTTPRequestHandler):
    server_version = "CodeTestServer/2.0"

    def do_GET(self) -> None:
        parsed = urlparse(self.path)

        if parsed.path == "/api/status":
            with get_connection() as connection:
                self._send_json(build_snapshot(connection))
            return

        if parsed.path == "/api/export":
            with get_connection() as connection:
                self._send_json(build_snapshot(connection))
            return

        self._serve_static(parsed.path)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        payload = self._read_json_body()
        if payload is None:
            return

        if parsed.path == "/api/tasks":
            self._create_task(payload)
            return

        if parsed.path == "/api/leads":
            self._create_lead(payload)
            return

        self.send_error(HTTPStatus.NOT_FOUND, "Not Found")

    def do_PATCH(self) -> None:
        parsed = urlparse(self.path)
        payload = self._read_json_body()
        if payload is None:
            return

        if parsed.path.startswith("/api/tasks/"):
            task_id = self._extract_item_id(parsed.path, "/api/tasks/")
            if task_id is None:
                return
            self._update_task(task_id, payload)
            return

        if parsed.path.startswith("/api/leads/"):
            lead_id = self._extract_item_id(parsed.path, "/api/leads/")
            if lead_id is None:
                return
            self._update_lead(lead_id, payload)
            return

        self.send_error(HTTPStatus.NOT_FOUND, "Not Found")

    def do_DELETE(self) -> None:
        parsed = urlparse(self.path)

        if parsed.path.startswith("/api/tasks/"):
            task_id = self._extract_item_id(parsed.path, "/api/tasks/")
            if task_id is None:
                return
            self._delete_task(task_id)
            return

        if parsed.path.startswith("/api/leads/"):
            lead_id = self._extract_item_id(parsed.path, "/api/leads/")
            if lead_id is None:
                return
            self._delete_lead(lead_id)
            return

        self.send_error(HTTPStatus.NOT_FOUND, "Not Found")

    def _create_task(self, payload: dict[str, object]) -> None:
        title = str(payload.get("title", "")).strip()
        if not title:
            self._send_json({"error": "Task title is required."}, status=HTTPStatus.BAD_REQUEST)
            return

        detail = str(payload.get("detail", "")).strip()
        due_date = str(payload.get("dueDate", "")).strip()
        priority = normalize_choice(str(payload.get("priority", "medium")), {"low", "medium", "high"}, "medium")
        status = normalize_choice(str(payload.get("status", "todo")), {"todo", "in_progress", "done"}, "todo")

        with get_connection() as connection:
            cursor = connection.execute(
                """
                INSERT INTO tasks (title, detail, due_date, priority, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (title, detail, due_date, priority, status, utc_now()),
            )
            task_id = cursor.lastrowid
            log_activity(
                connection,
                item_type="task",
                item_id=task_id,
                action="created",
                message=f"Created task: {title}",
            )
            connection.commit()
            row = connection.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
        self._send_json({"task": serialize_task(row)})

    def _update_task(self, task_id: int, payload: dict[str, object]) -> None:
        with get_connection() as connection:
            existing = connection.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
            if existing is None:
                self._send_json({"error": "Task not found."}, status=HTTPStatus.NOT_FOUND)
                return

            title = str(payload.get("title", existing["title"])).strip() or existing["title"]
            detail = str(payload.get("detail", existing["detail"])).strip()
            due_date = str(payload.get("dueDate", existing["due_date"])).strip()
            priority = normalize_choice(
                str(payload.get("priority", existing["priority"])),
                {"low", "medium", "high"},
                existing["priority"],
            )
            status = normalize_choice(
                str(payload.get("status", existing["status"])),
                {"todo", "in_progress", "done"},
                existing["status"],
            )

            connection.execute(
                """
                UPDATE tasks
                SET title = ?, detail = ?, due_date = ?, priority = ?, status = ?
                WHERE id = ?
                """,
                (title, detail, due_date, priority, status, task_id),
            )
            log_activity(
                connection,
                item_type="task",
                item_id=task_id,
                action="updated",
                message=f"Updated task: {title}",
            )
            connection.commit()
            row = connection.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
        self._send_json({"task": serialize_task(row)})

    def _delete_task(self, task_id: int) -> None:
        with get_connection() as connection:
            existing = connection.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
            if existing is None:
                self._send_json({"error": "Task not found."}, status=HTTPStatus.NOT_FOUND)
                return
            connection.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
            log_activity(
                connection,
                item_type="task",
                item_id=task_id,
                action="deleted",
                message=f"Deleted task: {existing['title']}",
            )
            connection.commit()
        self._send_json({"deleted": True, "id": task_id})

    def _create_lead(self, payload: dict[str, object]) -> None:
        name = str(payload.get("name", "")).strip()
        if not name:
            self._send_json({"error": "Lead name is required."}, status=HTTPStatus.BAD_REQUEST)
            return

        company = str(payload.get("company", "")).strip()
        email = str(payload.get("email", "")).strip()
        note = str(payload.get("note", "")).strip()
        stage = normalize_choice(
            str(payload.get("stage", "new")),
            {"new", "qualified", "proposal", "won"},
            "new",
        )

        with get_connection() as connection:
            cursor = connection.execute(
                """
                INSERT INTO leads (name, company, email, stage, note, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (name, company, email, stage, note, utc_now()),
            )
            lead_id = cursor.lastrowid
            log_activity(
                connection,
                item_type="lead",
                item_id=lead_id,
                action="created",
                message=f"Added lead: {name}",
            )
            connection.commit()
            row = connection.execute("SELECT * FROM leads WHERE id = ?", (lead_id,)).fetchone()
        self._send_json({"lead": serialize_lead(row)})

    def _update_lead(self, lead_id: int, payload: dict[str, object]) -> None:
        with get_connection() as connection:
            existing = connection.execute("SELECT * FROM leads WHERE id = ?", (lead_id,)).fetchone()
            if existing is None:
                self._send_json({"error": "Lead not found."}, status=HTTPStatus.NOT_FOUND)
                return

            name = str(payload.get("name", existing["name"])).strip() or existing["name"]
            company = str(payload.get("company", existing["company"])).strip()
            email = str(payload.get("email", existing["email"])).strip()
            note = str(payload.get("note", existing["note"])).strip()
            stage = normalize_choice(
                str(payload.get("stage", existing["stage"])),
                {"new", "qualified", "proposal", "won"},
                existing["stage"],
            )

            connection.execute(
                """
                UPDATE leads
                SET name = ?, company = ?, email = ?, stage = ?, note = ?
                WHERE id = ?
                """,
                (name, company, email, stage, note, lead_id),
            )
            log_activity(
                connection,
                item_type="lead",
                item_id=lead_id,
                action="updated",
                message=f"Updated lead: {name}",
            )
            connection.commit()
            row = connection.execute("SELECT * FROM leads WHERE id = ?", (lead_id,)).fetchone()
        self._send_json({"lead": serialize_lead(row)})

    def _delete_lead(self, lead_id: int) -> None:
        with get_connection() as connection:
            existing = connection.execute("SELECT * FROM leads WHERE id = ?", (lead_id,)).fetchone()
            if existing is None:
                self._send_json({"error": "Lead not found."}, status=HTTPStatus.NOT_FOUND)
                return
            connection.execute("DELETE FROM leads WHERE id = ?", (lead_id,))
            log_activity(
                connection,
                item_type="lead",
                item_id=lead_id,
                action="deleted",
                message=f"Deleted lead: {existing['name']}",
            )
            connection.commit()
        self._send_json({"deleted": True, "id": lead_id})

    def _serve_static(self, route_path: str) -> None:
        requested = "index.html" if route_path in {"/", ""} else route_path.lstrip("/")
        candidate = (STATIC_DIR / requested).resolve()

        if STATIC_DIR.resolve() not in candidate.parents and candidate != STATIC_DIR.resolve():
            self.send_error(HTTPStatus.FORBIDDEN, "Forbidden")
            return

        if not candidate.exists() or not candidate.is_file():
            self.send_error(HTTPStatus.NOT_FOUND, "Not Found")
            return

        content_type = self._get_content_type(candidate.suffix)
        data = candidate.read_bytes()

        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("Last-Modified", formatdate(candidate.stat().st_mtime, usegmt=True))
        self.end_headers()
        self.wfile.write(data)

    def _read_json_body(self) -> dict[str, object] | None:
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length) if length > 0 else b"{}"

        try:
            payload = json.loads(body.decode("utf-8"))
        except json.JSONDecodeError:
            self._send_json({"error": "Invalid JSON body."}, status=HTTPStatus.BAD_REQUEST)
            return None

        if not isinstance(payload, dict):
            self._send_json({"error": "JSON body must be an object."}, status=HTTPStatus.BAD_REQUEST)
            return None

        return payload

    def _extract_item_id(self, path: str, prefix: str) -> int | None:
        raw_id = path.removeprefix(prefix).strip("/")
        try:
            return int(raw_id)
        except ValueError:
            self._send_json({"error": "Invalid item id."}, status=HTTPStatus.BAD_REQUEST)
            return None

    def _send_json(
        self,
        payload: dict[str, object],
        *,
        status: HTTPStatus = HTTPStatus.OK,
    ) -> None:
        data = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    @staticmethod
    def _get_content_type(suffix: str) -> str:
        return {
            ".html": "text/html; charset=utf-8",
            ".css": "text/css; charset=utf-8",
            ".js": "application/javascript; charset=utf-8",
            ".json": "application/json; charset=utf-8",
        }.get(suffix, "application/octet-stream")


def normalize_choice(value: str, allowed: set[str], fallback: str) -> str:
    normalized = value.strip().lower()
    return normalized if normalized in allowed else fallback


def run() -> None:
    init_db()
    server = ThreadingHTTPServer((HOST, PORT), AppHandler)
    print(f"Serving on http://{HOST}:{PORT}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server.")
    finally:
        server.server_close()


if __name__ == "__main__":
    run()
