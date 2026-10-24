"""Tender requirements, bidder evidence, and compliance assessment schemas."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, Field

from app.schemas.common import DECISION_SUPPORT_DISCLAIMER, ProcessingState
from app.schemas.document import DocumentMetadata


class RequirementCategory(str, Enum):
    """Core tender requirement categories supported by Bid2Work AI."""

    ELIGIBILITY = "ELIGIBILITY"
    EXPERIENCE = "EXPERIENCE"
    FINANCIAL = "FINANCIAL"
    CERTIFICATION = "CERTIFICATION"
    DEADLINE = "DEADLINE"
    SAFETY = "SAFETY"
    OTHER = "OTHER"

    @classmethod
    def _missing_(cls, value: object):
        if isinstance(value, str):
            val_upper = value.strip().upper()
            for member in cls:
                if member.value == val_upper or member.name == val_upper:
                    return member
        return super()._missing_(value)


class RequirementPriority(str, Enum):
    """Criticality level of an extracted tender requirement."""

    MANDATORY = "MANDATORY"
    RECOMMENDED = "RECOMMENDED"
    INFORMATIONAL = "INFORMATIONAL"


class ComplianceStatus(str, Enum):
    """Standardized compliance assessment flags for each requirement."""

    EVIDENCE_FOUND = "Evidence Found"
    MISSING = "Missing"
    CONFLICTING = "Conflicting"
    NEEDS_REVIEW = "Needs Review"

    @classmethod
    def _missing_(cls, value: object):
        if isinstance(value, str):
            v_norm = value.strip().lower().replace("_", " ").replace("-", " ")
            for member in cls:
                if (
                    member.value.lower() == v_norm
                    or member.name.lower() == value.strip().lower()
                    or member.name.lower() == v_norm.replace(" ", "_")
                ):
                    return member
        return super()._missing_(value)

    @property
    def code(self) -> str:
        return self.name.lower()


class SourceReference(BaseModel):
    """Traceable reference pointing to a specific document page and excerpt."""

    filename: str = Field(..., min_length=1, description="Source PDF filename.")
    page_number: int = Field(..., ge=1, description="1-based page number where referenced.")
    excerpt: str = Field(
        default="",
        description="Short verbatim or near-verbatim excerpt from the source page.",
    )
    section_hint: Optional[str] = Field(
        default=None, description="Optional clause or section number if detected."
    )


class TenderRequirement(BaseModel):
    """A single structured requirement extracted from the tender PDF."""

    requirement_id: str = Field(
        ...,
        min_length=3,
        description="Stable identifier for this requirement (e.g., REQ-001).",
    )
    category: RequirementCategory = Field(
        ..., description="Domain category of the requirement."
    )
    title: str = Field(..., min_length=1, description="Concise requirement title.")
    description: str = Field(
        ..., min_length=1, description="Detailed requirement statement and criteria."
    )
    priority: RequirementPriority = Field(
        default=RequirementPriority.MANDATORY,
        description="Whether the requirement is mandatory or advisory.",
    )
    source: SourceReference = Field(
        ..., description="Source filename, page number, and excerpt in the tender PDF."
    )
    threshold_or_criteria: Optional[str] = Field(
        default=None,
        description="Specific numeric threshold, standard code, or deadline date if applicable.",
    )
    expected_evidence: Optional[str] = Field(
        default=None, description="Expected type of supporting documentation."
    )
    unit_or_currency: Optional[str] = Field(
        default=None, description="Extracted currency, unit, or measurement standard."
    )
    validity_period: Optional[str] = Field(
        default=None, description="Extracted validity period, timeline, or deadline."
    )
    confidence: float = Field(
        default=0.9, ge=0.0, le=1.0, description="Extraction confidence score."
    )
    needs_review: bool = Field(
        default=False, description="Whether requirement criteria is flagged for human review."
    )
    requires_permit_carryover: bool = Field(
        default=False,
        description="True if this requirement should carry over into post-award work-permit readiness.",
    )


class BidderEvidence(BaseModel):
    """A piece of supporting evidence located in a bidder document."""

    evidence_id: str = Field(
        ...,
        min_length=3,
        description="Stable identifier for this evidence item (e.g., EVD-001).",
    )
    requirement_id: Optional[str] = Field(
        default=None,
        description="ID of the TenderRequirement this evidence addresses.",
    )
    source_document_id: str = Field(
        ..., description="Document ID of the bidder supporting PDF."
    )
    filename: str = Field(
        ..., min_length=1, description="Source bidder PDF filename."
    )
    page_number: int = Field(
        ..., ge=1, description="1-based page number in the bidder PDF."
    )
    excerpt: str = Field(
        ...,
        description="Short excerpt from the bidder document demonstrating or relating to compliance.",
    )
    extracted_value: Optional[str] = Field(
        default=None,
        description="Normalized value extracted from evidence (e.g., turnover figure, ISO number).",
    )
    valid_until: Optional[str] = Field(
        default=None,
        description="ISO date string (YYYY-MM-DD) if an expiry or validity date is present.",
    )
    confidence: float = Field(
        default=0.8,
        ge=0.0,
        le=1.0,
        description="Confidence score (0.0 to 1.0) of the evidence match.",
    )


class RequirementAssessment(BaseModel):
    """Evaluation pairing a tender requirement with matched bidder evidence and compliance flag."""

    requirement_id: str = Field(
        ..., description="Stable ID matching TenderRequirement.requirement_id."
    )
    requirement: TenderRequirement = Field(
        ..., description="The evaluated tender requirement."
    )
    status: ComplianceStatus = Field(
        ...,
        description="Assessment flag: Evidence Found, Missing, Conflicting, or Needs Review.",
    )
    matched_evidence: List[BidderEvidence] = Field(
        default_factory=list,
        description="All bidder evidence items linked to this requirement.",
    )
    rationale: str = Field(
        ..., description="Explanation for the assigned compliance status."
    )
    discrepancies: List[str] = Field(
        default_factory=list,
        description="Specific conflicts, threshold shortfalls, or ambiguities noted.",
    )
    recommended_action: Optional[str] = Field(
        default=None,
        description="Suggested next step for the bid or compliance team.",
    )
    reviewed_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp when this assessment was produced.",
    )


class ComplianceSummaryMetrics(BaseModel):
    """Aggregated compliance counts and readiness metrics for a tender analysis run."""

    total_requirements: int = Field(..., ge=0)
    evidence_found_count: int = Field(..., ge=0)
    missing_count: int = Field(..., ge=0)
    conflicting_count: int = Field(..., ge=0)
    needs_review_count: int = Field(..., ge=0)
    mandatory_gap_count: int = Field(
        default=0,
        ge=0,
        description="Count of mandatory requirements flagged as Missing or Conflicting.",
    )
    safety_requirements_count: int = Field(
        default=0,
        ge=0,
        description="Count of requirements in SAFETY or marked for permit carryover.",
    )
    overall_readiness_score: float = Field(
        default=0.0,
        ge=0.0,
        le=100.0,
        description="Percentage (0-100) of requirements with Evidence Found.",
    )
    by_category: Dict[str, int] = Field(
        default_factory=dict,
        description="Requirement counts grouped by RequirementCategory.",
    )


class ComplianceAnalysisResult(BaseModel):
    """Complete output of analyzing a tender PDF against bidder supporting PDFs."""

    analysis_id: str = Field(
        ..., description="Stable identifier for this compliance analysis session."
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp of analysis creation.",
    )
    processing_state: ProcessingState = Field(
        default=ProcessingState.COMPLETED,
        description="Current processing state.",
    )
    tender_document: DocumentMetadata = Field(
        ..., description="Metadata for the uploaded tender PDF."
    )
    bidder_documents: List[DocumentMetadata] = Field(
        default_factory=list,
        description="Metadata for all uploaded bidder supporting PDFs.",
    )
    requirements: List[TenderRequirement] = Field(
        default_factory=list,
        description="All extracted tender requirements.",
    )
    assessments: List[RequirementAssessment] = Field(
        default_factory=list,
        description="Compliance assessments matching requirements against bidder evidence.",
    )
    summary: ComplianceSummaryMetrics = Field(
        ..., description="High-level compliance summary statistics."
    )
    disclaimer: str = Field(
        default=DECISION_SUPPORT_DISCLAIMER,
        description="Decision-support legal and operational disclaimer.",
    )
