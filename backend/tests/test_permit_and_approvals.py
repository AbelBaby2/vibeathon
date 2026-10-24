"""Tests for work-permit checklist generation, human review states, and approval restrictions."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.schemas.compliance import (
    BidderEvidence,
    ComplianceStatus,
    RequirementAssessment,
    RequirementCategory,
    RequirementPriority,
    SourceReference,
    TenderRequirement,
)
from app.schemas.permit import (
    AwardSimulationRequest,
    HumanReviewStatus,
    PermitCategory,
    PermitItemStatus,
)
from app.services.permit_readiness import PermitReadinessService


def test_work_permit_checklist_carries_forward_safety_and_certifications() -> None:
    """Work-permit checklist links to original requirement IDs and sets proper review states."""
    service = PermitReadinessService()

    req_safety = TenderRequirement(
        requirement_id="REQ-SAF-001",
        category=RequirementCategory.SAFETY,
        title="Site HSE & Confined Space",
        description="Mandatory site safety and worker PPE protocol.",
        priority=RequirementPriority.MANDATORY,
        source=SourceReference(filename="tender.pdf", page_number=2, excerpt="HSE protocol"),
        requires_permit_carryover=True,
    )
    req_cert = TenderRequirement(
        requirement_id="REQ-CRT-002",
        category=RequirementCategory.CERTIFICATION,
        title="Crane Lifting Certification",
        description="Accredited equipment certification.",
        priority=RequirementPriority.MANDATORY,
        source=SourceReference(filename="tender.pdf", page_number=3, excerpt="Crane cert"),
        requires_permit_carryover=True,
    )

    ev_safety = BidderEvidence(
        evidence_id="EVD-010",
        requirement_id="REQ-SAF-001",
        source_document_id="DOC-B-1",
        filename="hse_manual.pdf",
        page_number=1,
        excerpt="Approved HSE protocol.",
        confidence=0.9,
    )

    assessments = [
        RequirementAssessment(
            requirement_id="REQ-SAF-001",
            requirement=req_safety,
            status=ComplianceStatus.EVIDENCE_FOUND,
            matched_evidence=[ev_safety],
            rationale="Verified.",
        ),
        RequirementAssessment(
            requirement_id="REQ-CRT-002",
            requirement=req_cert,
            status=ComplianceStatus.MISSING,
            matched_evidence=[],
            rationale="No certificate attached.",
        ),
    ]

    request = AwardSimulationRequest(
        analysis_id="ANL-TEST-001",
        contract_reference="CTR-2026-999",
        planned_start_date="2026-12-01",
        site_location="Terminal 3",
        tender_requirements=[req_safety, req_cert],
        assessments=assessments,
    )

    result = service.simulate_award_and_build_checklist(request)
    assert len(result.checklist_items) == 2

    # Check REQ-SAF-001 mapping
    item1 = next(i for i in result.checklist_items if i.source_requirement_id == "REQ-SAF-001")
    assert item1.status == PermitItemStatus.VERIFIED
    assert item1.review_status == HumanReviewStatus.READY_FOR_REVIEW
    assert "EVD-010" in item1.attached_evidence_ids

    # Check REQ-CRT-002 mapping (Missing evidence)
    item2 = next(i for i in result.checklist_items if i.source_requirement_id == "REQ-CRT-002")
    assert item2.status == PermitItemStatus.PENDING_EVIDENCE
    assert item2.review_status == HumanReviewStatus.INCOMPLETE


def test_human_approval_restriction_rejects_unauthorized_user(client: TestClient) -> None:
    """Only an authorized human reviewer can mark an item as approved (403 Forbidden)."""
    # 1. Simulate award to produce a checklist item
    sim_resp = client.post(
        "/api/v1/permits/simulate-award",
        json={
            "analysis_id": "ANL-AUTH-TEST",
            "contract_reference": "CTR-TEST",
            "planned_start_date": "2026-11-01",
            "tender_requirements": [
                {
                    "requirement_id": "REQ-01",
                    "category": "SAFETY",
                    "title": "Safety Plan",
                    "description": "Safety requirement",
                    "source": {"filename": "tender.pdf", "page_number": 1, "excerpt": "Safety"},
                    "requires_permit_carryover": True,
                }
            ],
            "assessments": [
                {
                    "requirement_id": "REQ-01",
                    "requirement": {
                        "requirement_id": "REQ-01",
                        "category": "SAFETY",
                        "title": "Safety Plan",
                        "description": "Safety requirement",
                        "source": {"filename": "tender.pdf", "page_number": 1, "excerpt": "Safety"},
                        "requires_permit_carryover": True,
                    },
                    "status": "Evidence Found",
                    "matched_evidence": [],
                    "rationale": "Verified",
                }
            ],
        },
    )
    assert sim_resp.status_code == 200
    item_id = sim_resp.json()["data"]["checklist_items"][0]["item_id"]

    # 2. Unauthorized user attempts to approve -> 403 Forbidden
    unauth_resp = client.patch(
        f"/api/v1/permit-items/{item_id}",
        json={
            "review_status": "approved_by_reviewer",
            "reviewer_name": "Junior Clerk",
            "reviewer_role": "guest",
            "is_authorized_reviewer": False,
        },
    )
    assert unauth_resp.status_code == 403
    body = unauth_resp.json()
    assert body["success"] is False
    assert body["error"]["code"] == "FORBIDDEN"
    assert "Only an authorised human reviewer" in body["error"]["message"]

    # 3. Authorized reviewer approves -> 200 OK
    auth_resp = client.patch(
        f"/api/v1/permit-items/{item_id}",
        json={
            "review_status": "approved_by_reviewer",
            "reviewer_name": "Chief Safety Inspector",
            "reviewer_role": "hse_officer",
            "is_authorized_reviewer": True,
            "reviewer_notes": "Site inspection completed; documentation verified.",
        },
    )
    assert auth_resp.status_code == 200
    updated_item = auth_resp.json()["data"]
    assert updated_item["review_status"] == "approved_by_reviewer"
    assert updated_item["reviewer_name"] == "Chief Safety Inspector"
    assert updated_item["reviewer_role"] == "hse_officer"
    assert updated_item["status"] == "Verified"
