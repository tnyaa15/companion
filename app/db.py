import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

SCHEMA = """
CREATE TABLE IF NOT EXISTS messages (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    role      TEXT    NOT NULL CHECK (role IN ('user', 'assistant')),
    content   TEXT    NOT NULL,
    ts        TEXT    NOT NULL,
    proactive INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS memories (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    content TEXT    NOT NULL,
    ts      TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS preferences (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS reminders (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    content TEXT    NOT NULL,
    due_at  TEXT    NOT NULL,
    sent    INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS tasks (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    content TEXT    NOT NULL,
    created TEXT    NOT NULL,
    done    INTEGER NOT NULL DEFAULT 0
);
"""


class Database:
    def __init__(self, path: str):
        self.path = path
        with self._conn() as conn:
            conn.executescript(SCHEMA)

    @contextmanager
    def _conn(self):
        conn = sqlite3.connect(self.path)
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def add(self, role: str, content: str, proactive: bool = False) -> None:
        ts = datetime.now(timezone.utc).isoformat()
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO messages (role, content, ts, proactive) VALUES (?, ?, ?, ?)",
                (role, content, ts, int(proactive)),
            )

    def recent(self, limit: int) -> list[dict]:
        """Last `limit` messages, oldest first, in the shape the LLM API expects."""
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT role, content FROM messages ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()
        return [{"role": role, "content": content} for role, content in reversed(rows)]

    def proactive_today(self, tz_name: str) -> int:
        """How many proactive messages were sent since local midnight."""
        local_midnight = datetime.now(ZoneInfo(tz_name)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        start_utc = local_midnight.astimezone(timezone.utc).isoformat()
        with self._conn() as conn:
            (count,) = conn.execute(
                "SELECT COUNT(*) FROM messages WHERE proactive = 1 AND ts >= ?",
                (start_utc,),
            ).fetchone()
        return count

    def unanswered_proactive(self) -> int:
        """Proactive messages sent since the user last wrote (the back-off signal)."""
        with self._conn() as conn:
            (count,) = conn.execute(
                """
                SELECT COUNT(*) FROM messages
                WHERE proactive = 1
                  AND id > COALESCE((SELECT MAX(id) FROM messages WHERE role = 'user'), 0)
                """
            ).fetchone()
        return count

    def clear(self) -> None:
        with self._conn() as conn:
            conn.execute("DELETE FROM messages")

    def add_memory(self, content: str) -> int:
        ts = datetime.now(timezone.utc).isoformat()
        with self._conn() as conn:
            cursor = conn.execute(
                "INSERT INTO memories (content, ts) VALUES (?, ?)", (content, ts)
            )
            return cursor.lastrowid

    def memories(self) -> list[dict]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT id, content FROM memories ORDER BY id"
            ).fetchall()
        return [{"id": memory_id, "content": content} for memory_id, content in rows]

    def delete_memory(self, memory_id: int) -> bool:
        with self._conn() as conn:
            cursor = conn.execute("DELETE FROM memories WHERE id = ?", (memory_id,))
            return cursor.rowcount > 0

    def get_preference(self, key: str, default: str) -> str:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT value FROM preferences WHERE key = ?", (key,)
            ).fetchone()
        return row[0] if row else default

    def set_preference(self, key: str, value: str) -> None:
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO preferences (key, value) VALUES (?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                (key, value),
            )

    def add_reminder(self, content: str, due_at: str) -> int:
        with self._conn() as conn:
            cursor = conn.execute(
                "INSERT INTO reminders (content, due_at) VALUES (?, ?)",
                (content, due_at),
            )
            return cursor.lastrowid

    def due_reminders(self, now: str) -> list[dict]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT id, content, due_at FROM reminders "
                "WHERE sent = 0 AND due_at <= ? ORDER BY due_at, id",
                (now,),
            ).fetchall()
        return [
            {"id": reminder_id, "content": content, "due_at": due_at}
            for reminder_id, content, due_at in rows
        ]

    def pending_reminders(self) -> list[dict]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT id, content, due_at FROM reminders "
                "WHERE sent = 0 ORDER BY due_at, id"
            ).fetchall()
        return [
            {"id": reminder_id, "content": content, "due_at": due_at}
            for reminder_id, content, due_at in rows
        ]

    def mark_reminder_sent(self, reminder_id: int) -> None:
        with self._conn() as conn:
            conn.execute("UPDATE reminders SET sent = 1 WHERE id = ?", (reminder_id,))

    def cancel_reminder(self, reminder_id: int) -> bool:
        with self._conn() as conn:
            cursor = conn.execute(
                "DELETE FROM reminders WHERE id = ? AND sent = 0", (reminder_id,)
            )
            return cursor.rowcount > 0

    def add_task(self, content: str) -> int:
        created = datetime.now(timezone.utc).isoformat()
        with self._conn() as conn:
            cursor = conn.execute(
                "INSERT INTO tasks (content, created) VALUES (?, ?)", (content, created)
            )
            return cursor.lastrowid

    def open_tasks(self) -> list[dict]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT id, content FROM tasks WHERE done = 0 ORDER BY id"
            ).fetchall()
        return [{"id": task_id, "content": content} for task_id, content in rows]

    def complete_task(self, task_id: int) -> bool:
        with self._conn() as conn:
            cursor = conn.execute(
                "UPDATE tasks SET done = 1 WHERE id = ? AND done = 0", (task_id,)
            )
            return cursor.rowcount > 0

    def delete_task(self, task_id: int) -> bool:
        with self._conn() as conn:
            cursor = conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
            return cursor.rowcount > 0
