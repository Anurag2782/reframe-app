"""
Lightweight job tracking backed by SQLite. This keeps the MVP dependency-free
(no Redis/Celery needed to get started) while still surviving a server
restart. FastAPI's BackgroundTasks runs the actual work in-process.

For heavier production use, swap this out for Celery/RQ + Redis -- the
public functions here (create_job, update_job, get_job, list_jobs) are the
seam to do that behind.
"""
from __future__ import annotations

import sqlite3
import time
import uuid
from contextlib import contextmanager
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "storage" / "jobs.db"


@contextmanager
def _conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with _conn() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS jobs (
                id TEXT PRIMARY KEY,
                batch_id TEXT,
                filename TEXT,
                media_type TEXT,
                target_w INTEGER,
                target_h INTEGER,
                mode TEXT,
                status TEXT,
                error TEXT,
                input_path TEXT,
                output_path TEXT,
                created_at REAL,
                updated_at REAL
            )
            """
        )


def create_job(batch_id: str, filename: str, media_type: str, target_w: int,
               target_h: int, mode: str, input_path: str) -> str:
    job_id = str(uuid.uuid4())
    now = time.time()
    with _conn() as conn:
        conn.execute(
            """INSERT INTO jobs
               (id, batch_id, filename, media_type, target_w, target_h, mode,
                status, error, input_path, output_path, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, 'queued', NULL, ?, NULL, ?, ?)""",
            (job_id, batch_id, filename, media_type, target_w, target_h, mode,
             input_path, now, now),
        )
    return job_id


def update_job(job_id: str, **fields) -> None:
    if not fields:
        return
    fields["updated_at"] = time.time()
    set_clause = ", ".join(f"{k} = ?" for k in fields)
    values = list(fields.values()) + [job_id]
    with _conn() as conn:
        conn.execute(f"UPDATE jobs SET {set_clause} WHERE id = ?", values)


def get_job(job_id: str) -> dict | None:
    with _conn() as conn:
        row = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
        return dict(row) if row else None


def list_jobs_for_batch(batch_id: str) -> list[dict]:
    with _conn() as conn:
        rows = conn.execute(
            "SELECT * FROM jobs WHERE batch_id = ? ORDER BY created_at", (batch_id,)
        ).fetchall()
        return [dict(r) for r in rows]
