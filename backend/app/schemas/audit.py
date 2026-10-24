"""Audit event contracts for tracking compliance and permit readiness actions."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class AuditEventType(str, Enum):
    """Standardized audit trail event classifications."""

    DOCUMENTS_UPLOADED = "DOCUMENTS_UPLOADED"
    PDF_EXTRACTED = "PDF_EXTRACTED"
    REQUIREMENTS_IDENTIFIED = "REQUIREMENTS_IDENTIFIED"
    COMPLIANCE_EVALUATED = "COMPLIANCE_EVALUATED"
    CONTRACT_AWARD_SIMULATED = "CONTRACT_AWARD_SIMULATED"
    PERMIT_CHECKLIST_GENERATED = "PERMIT_CHECKLIST_GENERATED"
    PERMIT_ITEM_REVIEWED = "PERMIT_ITEM_REVIEWED"
    REPORT_EXPORTED = "REPORT_EXPORTED"
    ANALYSIS_ERROR = "ANALYSIS_ERROR"


class AuditActorType(str, Enum):
    """Originating actor of an audit event."""

    SYSTEM = "SYSTEM"
    USER = "USER"


class AuditEvent(BaseModel):
    """A single immutable audit record stored in SQLite for traceability."""

    event_id: str = Field(
        ...,
        min_length=3,
        description="Stable identifier for the audit event (e.g., AUD-001).",
    )
    analysis_id: Optional[str] = Field(
        default=None,
        description="Associated compliance analysis session ID, if applicable.",
    )
    event_type: AuditEventType = Field(..., description="Category of the audit event.")
    actor: AuditActorType = Field(
        default=AuditActorType.SYSTEM,
        description="Actor that triggered the event.",
    )
    summary: str = Field(..., min_length=1, description="Human-readable event summary.")
    details: Dict[str, Any] = Field(
        default_factory=dict,
        description="Structured context metadata (filenames, counts, status breakdown).",
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp when the event was recorded.",
    )


class AuditLogListResponse(BaseModel):
    """Paginated/listed collection of audit events."""

    events: List[AuditEvent] = Field(
        default_factory=list, description="Ordered list of audit events."
    )
    total: int = Field(..., ge=0, description="Total number of events returned.")
