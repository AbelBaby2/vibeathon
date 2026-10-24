"""Work-permit readiness checklist and post-award simulation schemas."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field

from app.schemas.common import DECISION_SUPPORT_DISCLAIMER, ProcessingState
from app.schemas.compliance import (
    BidderEvidence,
    RequirementAssessment,
    TenderRequirement,
)


class PermitItemStatus(str, Enum):
    """Readiness status for an individual work-permit checklist item."""

    VERIFIED = "Verified"
    PENDING_EVIDENCE = "Pending Evidence"
    EXPIRED = "Expired"
    CONFLICTING = "Conflicting"
    NEEDS_REVIEW = "Needs Review"


class PermitCategory(str, Enum):
    """Safety and operational permit checklist domains."""

    HSE_POLICY = "HSE_POLICY"
    WORKER_QUALIFICATION = "WORKER_QUALIFICATION"
    EQUIPMENT_CERTIFICATION = "EQUIPMENT_CERTIFICATION"
    SITE_APPROVAL = "SITE_APPROVAL"
    INSURANCE_LIABILITY = "INSURANCE_LIABILITY"
    EMERGENCY_RESPONSE = "EMERGENCY_RESPONSE"
    HAZARD_CONTROL = "HAZARD_CONTROL"


class PermitChecklistItem(BaseModel):
    """A single post-award work-permit readiness checklist entry."""

    item_id: str = Field(
        ...,
        min_length=3,
        description="Stable identifier for this checklist item (e.g., PRM-001).",
    )
    source_requirement_id: Optional[str] = Field(
        default=None,
        description="Originating TenderRequirement ID carried over from compliance analysis.",
    )
    category: PermitCategory = Field(
        ..., description="Permit safety or operational category."
    )
    title: str = Field(..., min_length=1, description="Checklist requirement title.")
    description: str = Field(
        ..., description="Operational requirement and verification criteria."
    )
    status: PermitItemStatus = Field(
        ..., description="Current readiness evaluation status."
    )
    required_document_type: str = Field(
        ...,
        description="Type of safety document, qualification, or approval certificate required.",
    )
    supporting_evidence: List[BidderEvidence] = Field(
        default_factory=list,
        description="Evidence items from bidder documents supporting this checklist item.",
    )
    approval_authority: Optional[str] = Field(
        default=None,
        description="Issuing or approving body (e.g., Site HSE Officer, ISO Registrar).",
    )
    qualification_reference: Optional[str] = Field(
        default=None,
        description="Detected certificate number, standard code, or license reference.",
    )
    expiry_date: Optional[str] = Field(
        default=None,
        description="Detected document or certification expiry date (YYYY-MM-DD) when available.",
    )
    is_expired: bool = Field(
        default=False,
        description="True if expiry_date is earlier than the planned work date or current date.",
    )
    unresolved_conditions: List[str] = Field(
        default_factory=list,
        description="Unresolved conditions or missing approvals blocking work-permit mobilization.",
    )
    remediation_steps: List[str] = Field(
        default_factory=list,
        description="Actionable steps required to resolve pending or expired items.",
    )


class AwardSimulationRequest(BaseModel):
    """Payload to simulate a contract award and generate a work-permit readiness checklist."""

    analysis_id: str = Field(
        ..., min_length=1, description="Compliance analysis session ID."
    )
    contract_reference: Optional[str] = Field(
        default="CTR-SIM-001",
        description="Simulated contract reference identifier.",
    )
    planned_start_date: Optional[str] = Field(
        default=None,
        description="Planned mobilization date (YYYY-MM-DD) used for expiry verification.",
    )
    site_location: Optional[str] = Field(
        default=None,
        description="Operational site or facility name.",
    )
    tender_requirements: List[TenderRequirement] = Field(
        default_factory=list,
        description="Tender requirements from the compliance run.",
    )
    assessments: List[RequirementAssessment] = Field(
        default_factory=list,
        description="Compliance assessments with matched bidder evidence.",
    )


class PermitReadinessSummary(BaseModel):
    """Aggregated readiness statistics for the post-award work-permit checklist."""

    total_items: int = Field(..., ge=0)
    verified_count: int = Field(..., ge=0)
    pending_count: int = Field(..., ge=0)
    expired_count: int = Field(..., ge=0)
    conflicting_count: int = Field(..., ge=0)
    needs_review_count: int = Field(..., ge=0)
    readiness_percentage: float = Field(
        default=0.0,
        ge=0.0,
        le=100.0,
        description="Percentage (0-100) of checklist items in Verified status.",
    )
    blocking_conditions_count: int = Field(
        default=0,
        ge=0,
        description="Count of unresolved conditions that must be cleared before mobilization.",
    )


class PermitReadinessResult(BaseModel):
    """Complete result of simulating contract award and evaluating work-permit readiness."""

    permit_pack_id: str = Field(
        ..., description="Stable identifier for this work-permit readiness package."
    )
    analysis_id: str = Field(
        ..., description="Originating compliance analysis session ID."
    )
    contract_reference: Optional[str] = Field(
        default=None, description="Simulated contract identifier."
    )
    simulated_award_date: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp of contract award simulation.",
    )
    planned_start_date: Optional[str] = Field(
        default=None, description="Target mobilization start date (YYYY-MM-DD)."
    )
    site_location: Optional[str] = Field(
        default=None, description="Target operational site."
    )
    processing_state: ProcessingState = Field(
        default=ProcessingState.COMPLETED,
        description="Current processing state.",
    )
    checklist_items: List[PermitChecklistItem] = Field(
        default_factory=list,
        description="Generated work-permit readiness checklist items.",
    )
    summary: PermitReadinessSummary = Field(
        ..., description="Aggregated work-permit readiness metrics."
    )
    unresolved_conditions: List[str] = Field(
        default_factory=list,
        description="Top-level rollup of unresolved safety or permit conditions.",
    )
    disclaimer: str = Field(
        default=DECISION_SUPPORT_DISCLAIMER,
        description="Decision-support legal and operational disclaimer.",
    )
