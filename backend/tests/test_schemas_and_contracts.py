"""Tests for shared Pydantic data contracts, stable IDs, and source references."""

from __future__ import annotations

from app.schemas import (
    BidderEvidence,
    ComplianceStatus,
    DocumentMetadata,
    DocumentRole,
    PermitCategory,
    PermitChecklistItem,
    PermitItemStatus,
    ProcessingState,
    RequirementAssessment,
    RequirementCategory,
    RequirementPriority,
    SourceReference,
    TenderRequirement,
)


def test_tender_requirement_and_evidence_contract() -> None:
    req = TenderRequirement(
        requirement_id="REQ-001",
        category=RequirementCategory.SAFETY,
        title="Confined Space & HSE Plan",
        description="Bidder must submit an approved HSE plan and confined space procedure.",
        priority=RequirementPriority.MANDATORY,
        source=SourceReference(
            filename="tender_rfp.pdf",
            page_number=4,
            excerpt="Section 4.2: Bidder must submit an approved HSE plan.",
        ),
        requires_permit_carryover=True,
    )

    ev = BidderEvidence(
        evidence_id="EVD-001",
        requirement_id=req.requirement_id,
        source_document_id="DOC-BIDDER-001",
        filename="bidder_hse_manual.pdf",
        page_number=2,
        excerpt="Approved HSE manual and confined space entry procedure valid until 2027-12-31.",
        valid_until="2027-12-31",
        confidence=0.92,
    )

    assessment = RequirementAssessment(
        requirement_id=req.requirement_id,
        requirement=req,
        status=ComplianceStatus.EVIDENCE_FOUND,
        matched_evidence=[ev],
        rationale="Verified against bidder HSE manual on page 2.",
    )

    assert assessment.status.value == "Evidence Found"
    assert assessment.matched_evidence[0].evidence_id == "EVD-001"
    assert assessment.matched_evidence[0].filename == "bidder_hse_manual.pdf"
    assert assessment.matched_evidence[0].page_number == 2


def test_permit_checklist_item_contract() -> None:
    item = PermitChecklistItem(
        item_id="PRM-001",
        source_requirement_id="REQ-001",
        category=PermitCategory.HSE_POLICY,
        title="HSE Plan Verification",
        description="Verify active HSE plan prior to mobilization.",
        status=PermitItemStatus.VERIFIED,
        required_document_type="HSE Plan",
        expiry_date="2027-12-31",
        is_expired=False,
    )
    assert item.item_id == "PRM-001"
    assert item.status == PermitItemStatus.VERIFIED


def test_document_metadata_and_processing_states() -> None:
    doc = DocumentMetadata(
        document_id="DOC-TENDER-001",
        filename="master_tender.pdf",
        role=DocumentRole.TENDER,
        file_size_bytes=24500,
        page_count=12,
    )
    assert doc.role == DocumentRole.TENDER
    assert ProcessingState.ANALYZING.value == "ANALYZING"
