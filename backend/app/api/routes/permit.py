"""Post-award work-permit readiness and human review status endpoints."""

from __future__ import annotations

from fastapi import APIRouter

from app.core.config import get_settings
from app.core.exceptions import NotFoundError, UnauthorizedReviewerError
from app.core.logging import get_request_id
from app.models.audit_record import AuditRepository
from app.models.permit_record import PermitRepository
from app.schemas.audit import AuditActorType, AuditEventType
from app.schemas.common import ApiMeta, ApiResponse, ProcessingState
from app.schemas.permit import (
    AwardSimulationRequest,
    HumanReviewStatus,
    PermitChecklistItem,
    PermitItemUpdateRequest,
    PermitReadinessResult,
)
from app.services.permit_readiness import PermitReadinessService

router = APIRouter(tags=["Work-Permit Readiness"])

_AUTHORISED_ROLES = {
    "authorised_reviewer",
    "authorized_reviewer",
    "hse_officer",
    "site_safety_officer",
    "safety_auditor",
    "lead_auditor",
    "compliance_officer",
    "procurement_lead",
}


@router.post("/api/v1/permits/simulate-award", response_model=ApiResponse[PermitReadinessResult])
async def simulate_contract_award(
    request: AwardSimulationRequest,
) -> ApiResponse[PermitReadinessResult]:
    """Simulate a contract award and generate a work-permit readiness checklist."""
    settings = get_settings()
    permit_service = PermitReadinessService()
    permit_repo = PermitRepository(settings.sqlite_db_path)
    audit_repo = AuditRepository(settings.sqlite_db_path)

    result = permit_service.simulate_award_and_build_checklist(request)
    permit_repo.save_checklist(result)

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


@router.patch("/api/v1/permit-items/{item_id}", response_model=ApiResponse[PermitChecklistItem])
async def update_permit_checklist_item(
    item_id: str,
    update: PermitItemUpdateRequest,
) -> ApiResponse[PermitChecklistItem]:
    """Update a checklist item's human review status with an audit event."""
    settings = get_settings()
    permit_repo = PermitRepository(settings.sqlite_db_path)
    audit_repo = AuditRepository(settings.sqlite_db_path)

    # Human review authorization guard
    if update.review_status == HumanReviewStatus.APPROVED_BY_REVIEWER:
        is_authorized = (
            update.is_authorized_reviewer is True
            or (update.reviewer_role and update.reviewer_role.strip().lower() in _AUTHORISED_ROLES)
        )
        if not is_authorized:
            raise UnauthorizedReviewerError(
                "Only an authorised human reviewer can mark a work-permit checklist item as approved. "
                "Checklists do not constitute formal work permits and require qualified verification."
            )

    updated = permit_repo.update_checklist_item(item_id, update)
    if not updated:
        raise NotFoundError(f"Permit checklist item '{item_id}' was not found.")

    chk, item = updated

    audit_repo.record_event(
        event_type=AuditEventType.PERMIT_ITEM_REVIEWED,
        analysis_id=chk.analysis_id,
        actor=AuditActorType.USER,
        summary=(
            f"Updated review status of permit item '{item_id}' to '{item.review_status.value}' "
            f"by {item.reviewer_name or 'reviewer'}."
        ),
        details={
            "item_id": item_id,
            "review_status": item.review_status.value,
            "readiness_status": item.status.value,
            "reviewer_name": item.reviewer_name,
            "reviewer_role": item.reviewer_role,
            "reviewer_notes": item.reviewer_notes,
        },
    )

    return ApiResponse[PermitChecklistItem](
        success=True,
        data=item,
        meta=ApiMeta(
            request_id=get_request_id(),
            processing_state=ProcessingState.COMPLETED,
            version=settings.app_version,
        ),
    )
