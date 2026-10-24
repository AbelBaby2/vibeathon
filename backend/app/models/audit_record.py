"""Audit record persistence model and repository functions."""

from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.core.logging import get_logger
from app.db.sqlite import init_sqlite_db, sqlite_connection
from app.schemas.audit import AuditActorType, AuditEvent, AuditEventType

logger = get_logger(__name__)

# In-memory fallback buffer so audit queries still work if SQLite is unreachable
_FALLBACK_AUDIT_BUFFER: List[AuditEvent] = []


class AuditRepository:
    """Lightweight repository for persisting and querying MVP audit events."""

    def __init__(self, db_path: Optional[str] = None) -> None:
        self.db_path = db_path
        init_sqlite_db(self.db_path)

    def record_event(
        self,
        event_type: AuditEventType,
        summary: str,
        analysis_id: Optional[str] = None,
        actor: AuditActorType = AuditActorType.SYSTEM,
        details: Optional[Dict[str, Any]] = None,
        event_id: Optional[str] = None,
    ) -> AuditEvent:
        """Create and persist an AuditEvent without failing the caller if DB is busy."""
        now = datetime.now(timezone.utc)
        resolved_id = event_id or f"AUD-{uuid.uuid4().hex[:10].upper()}"
        event = AuditEvent(
            event_id=resolved_id,
            analysis_id=analysis_id,
            event_type=event_type,
            actor=actor,
            summary=summary,
            details=details or {},
            created_at=now,
        )

        try:
            with sqlite_connection(self.db_path) as conn:
                conn.execute(
                    """
                    INSERT INTO audit_events (
                        event_id, analysis_id, event_type, actor, summary, details_json, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        event.event_id,
                        event.analysis_id,
                        event.event_type.value,
                        event.actor.value,
                        event.summary,
                        json.dumps(event.details, default=str),
                        event.created_at.isoformat(),
                    ),
                )
        except (sqlite3.Error, OSError) as exc:
            logger.warning(f"Audit event stored in fallback memory buffer: {exc}")
            _FALLBACK_AUDIT_BUFFER.insert(0, event)

        return event

    def list_events(
        self,
        analysis_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[AuditEvent]:
        """Retrieve recent audit events ordered newest first."""
        try:
            with sqlite_connection(self.db_path) as conn:
                if analysis_id:
                    rows = conn.execute(
                        """
                        SELECT event_id, analysis_id, event_type, actor, summary, details_json, created_at
                        FROM audit_events
                        WHERE analysis_id = ?
                        ORDER BY created_at DESC
                        LIMIT ?
                        """,
                        (analysis_id, limit),
                    ).fetchall()
                else:
                    rows = conn.execute(
                        """
                        SELECT event_id, analysis_id, event_type, actor, summary, details_json, created_at
                        FROM audit_events
                        ORDER BY created_at DESC
                        LIMIT ?
                        """,
                        (limit,),
                    ).fetchall()

            events: List[AuditEvent] = []
            for row in rows:
                try:
                    parsed_details = json.loads(row["details_json"] or "{}")
                except json.JSONDecodeError:
                    parsed_details = {}
                events.append(
                    AuditEvent(
                        event_id=row["event_id"],
                        analysis_id=row["analysis_id"],
                        event_type=AuditEventType(row["event_type"]),
                        actor=AuditActorType(row["actor"]),
                        summary=row["summary"],
                        details=parsed_details,
                        created_at=datetime.fromisoformat(row["created_at"]),
                    )
                )
            return events
        except (sqlite3.Error, OSError) as exc:
            logger.warning(f"Reading audit events from fallback memory buffer: {exc}")
            if analysis_id:
                return [
                    e for e in _FALLBACK_AUDIT_BUFFER if e.analysis_id == analysis_id
                ][:limit]
            return _FALLBACK_AUDIT_BUFFER[:limit]
