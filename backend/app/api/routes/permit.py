"""Post-award work-permit readiness simulation endpoints."""

from __future__ import annotations

from fastapi import APIRouter

from app.core.config import get_settings
from app.core.logging import get_request_id
from app.models.audit_record import AuditRepository
from app.schemas.audit import AuditActorType, AuditEventType
from app.schemas.common import ApiMeta, ApiResponse, ProcessingState
from app.schemas.permit import AwardSimulationRequest, PermitReadinessResult
from app.services.permit_readiness import PermitReadinessService

router = APIRouter(prefix="/api/v1/permits", tags=["Work-Permit Readiness"])


@router.post("/simulate-award", response_model=ApiResponse[PermitReadinessResult])
async def simulate_contract_award(
    request: AwardSimulationRequest,
) -> ApiResponse[PermitReadinessResult]:
    """Simulate a contract award and generate a work-permit readiness checklist."""
    settings = get_settings()
    permit_service = PermitReadinessService()
    audit_repo = AuditRepository(settings.sqlite_db_path)

    result = permit_service.simulate_award_and_build_checklist(request)

    audit_repo.record_event(
        event_type=AuditEventType.CONTRACT_AWARD_SIMULATED,
        analysis_id=request.analysis_id,
        actor=AuditActorType.USER,
        summary=(
            f"Simulated contract award ({result.contract_reference}) and generated "
            f"{result.summary.total_items} work-permit readiness checklist item(s)."
        ),
        details={
            "permit_pack_id": result.permit_pack_id,
            "contract_reference": result.contract_reference,
            "readiness_percentage": result.summary.readiness_percentage,
            "blocking_conditions_count": result.summary.blocking_conditions_count,
        },
    )

    return ApiResponse[PermitReadinessResult](
        success=True,
        data=result,
        meta=ApiMeta(
            request_id=get_request_id(),
            processing_state=ProcessingState.COMPLETED,
            version=settings.app_version,
        ),
    )
