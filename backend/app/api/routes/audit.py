"""Audit trail query endpoints."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Query

from app.core.config import get_settings
from app.core.logging import get_request_id
from app.models.audit_record import AuditRepository
from app.schemas.audit import AuditLogListResponse
from app.schemas.common import ApiMeta, ApiResponse, ProcessingState

router = APIRouter(prefix="/api/v1/audit", tags=["Audit Trail"])


@router.get("/events", response_model=ApiResponse[AuditLogListResponse])
async def list_audit_events(
    analysis_id: Optional[str] = Query(
        default=None, description="Filter events by compliance analysis session ID."
    ),
    limit: int = Query(
        default=50, ge=1, le=200, description="Maximum number of events to return."
    ),
) -> ApiResponse[AuditLogListResponse]:
    """Retrieve recorded compliance and permit readiness audit events from SQLite."""
    settings = get_settings()
    audit_repo = AuditRepository(settings.sqlite_db_path)
    events = audit_repo.list_events(analysis_id=analysis_id, limit=limit)

    payload = AuditLogListResponse(events=events, total=len(events))
    return ApiResponse[AuditLogListResponse](
        success=True,
        data=payload,
        meta=ApiMeta(
            request_id=get_request_id(),
            processing_state=ProcessingState.COMPLETED,
            version=settings.app_version,
        ),
    )
