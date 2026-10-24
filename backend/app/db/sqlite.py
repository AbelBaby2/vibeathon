"""Lightweight SQLite connection and schema management for MVP audit records."""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator, Optional

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)

_CREATE_AUDIT_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS audit_events (
    event_id TEXT PRIMARY KEY,
    analysis_id TEXT,
    event_type TEXT NOT NULL,
    actor TEXT NOT NULL,
    summary TEXT NOT NULL,
    details_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_audit_events_analysis_id
    ON audit_events (analysis_id);

CREATE INDEX IF NOT EXISTS idx_audit_events_created_at
    ON audit_events (created_at DESC);

CREATE TABLE IF NOT EXISTS uploaded_documents (
    document_id TEXT PRIMARY KEY,
    filename TEXT NOT NULL,
    role TEXT NOT NULL,
    file_size_bytes INTEGER NOT NULL,
    page_count INTEGER NOT NULL,
    content_type TEXT NOT NULL,
    sha256_hash TEXT,
    pages_json TEXT NOT NULL,
    total_chars INTEGER NOT NULL,
    is_text_based INTEGER NOT NULL,
    uploaded_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS compliance_analyses (
    analysis_id TEXT PRIMARY KEY,
    tender_document_id TEXT NOT NULL,
    bidder_document_ids_json TEXT NOT NULL,
    result_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS permit_checklists (
    permit_pack_id TEXT PRIMARY KEY,
    analysis_id TEXT UNIQUE NOT NULL,
    contract_reference TEXT,
    planned_start_date TEXT,
    site_location TEXT,
    checklist_items_json TEXT NOT NULL,
    summary_json TEXT NOT NULL,
    unresolved_conditions_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_permit_checklists_analysis_id
    ON permit_checklists (analysis_id);
"""


def get_db_path(custom_path: Optional[str] = None) -> Path:
    """Resolve the configured SQLite database file path and ensure parent dir exists."""
    raw_path = custom_path or get_settings().sqlite_db_path
    db_path = Path(raw_path).resolve()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return db_path


def init_sqlite_db(custom_path: Optional[str] = None) -> bool:
    """Initialize the SQLite audit database schema. Returns True if ready."""
    try:
        db_path = get_db_path(custom_path)
        with sqlite3.connect(str(db_path), timeout=5.0) as conn:
            conn.executescript(_CREATE_AUDIT_TABLE_SQL)
            conn.commit()
        return True
    except sqlite3.Error as exc:
        logger.warning(f"SQLite initialization warning: {exc}")
        return False
    except OSError as exc:
        logger.warning(f"SQLite directory creation warning: {exc}")
        return False


def check_database_health(custom_path: Optional[str] = None) -> bool:
    """Verify SQLite connectivity without blocking document analysis."""
    try:
        db_path = get_db_path(custom_path)
        with sqlite3.connect(str(db_path), timeout=2.0) as conn:
            conn.execute("SELECT 1")
        return True
    except (sqlite3.Error, OSError):
        return False


@contextmanager
def sqlite_connection(custom_path: Optional[str] = None) -> Iterator[sqlite3.Connection]:
    """Context manager yielding a SQLite connection with Row factory."""
    db_path = get_db_path(custom_path)
    conn = sqlite3.connect(str(db_path), timeout=5.0)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()
