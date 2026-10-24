"""Report export endpoints."""

from __future__ import annotations

from fastapi import APIRouter

from app.core.config import get_settings
from app.core.logging import get_request_id
from app.models.audit_record import AuditRepository
from app.schemas.audit import AuditActorType, AuditEventType
from app.schemas.common import ApiMeta, ApiResponse, ProcessingState
from app.schemas.report import ExportableReportData, ReportExportRequest
from app.services.report_generator import ReportGeneratorService

router = APIRouter(prefix="/api/v1/reports", tags=["Report Export"])


@router.post("/export", response_model=ApiResponse[ExportableReportData])
async def export_compliance_report(
    request: ReportExportRequest,
) -> ApiResponse[ExportableReportData]:
    """Generate and export a consolidated compliance and work-permit readiness report."""
    settings = get_settings()
    audit_repo = AuditRepository(settings.sqlite_db_path)
    report_service = ReportGeneratorService()

    audit_events = (
        audit_repo.list_events(analysis_id=request.analysis_id, limit=100)
        if request.include_audit_trail
        else []
    )

    report = report_service.generate_report(
        request=request,
        audit_events=audit_events,
    )

    audit_repo.record_event(
        event_type=AuditEventType.REPORT_EXPORTED,
        analysis_id=request.analysis_id,
        actor=AuditActorType.USER,
        summary=f"Exported {request.format.value} report '{report.filename}'.",
        details={
            "report_id": report.report_id,
            "format": request.format.value,
            "filename": report.filename,
        },
    )

    return ApiResponse[ExportableReportData](
        success=True,
        data=report,
        meta=ApiMeta(
            request_id=get_request_id(),
            processing_state=ProcessingState.COMPLETED,
            version=settings.app_version,
        ),
    )
