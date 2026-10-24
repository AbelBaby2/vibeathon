"""Comprehensive end-to-end tests for FastAPI application workflow and CSV report export."""

from __future__ import annotations

import csv
import io

from fastapi.testclient import TestClient

from tests.conftest import build_text_pdf_bytes


def test_health_and_readiness_endpoints(client: TestClient) -> None:
    """Validate GET /health and GET /api/v1/health/ready."""
    resp1 = client.get("/health")
    assert resp1.status_code == 200
    assert resp1.json()["data"]["status"] == "healthy"

    resp2 = client.get("/api/v1/health/ready")
    assert resp2.status_code == 200
    data = resp2.json()["data"]
    assert data["ready"] is True
    assert data["database_ready"] is True
    assert data["storage_ready"] is True


def test_complete_backend_workflow_from_upload_to_csv_export(client: TestClient) -> None:
    """Test full workflow: upload -> analysis -> retrieve -> award -> permit-readiness -> review -> CSV."""
    tender_pdf = build_text_pdf_bytes(
        [
            "Clause 1.1: Bidder must hold valid ISO 45001 certification. "
            "Clause 1.2: Minimum annual audited turnover of USD 5M required.",
            "Clause 2.1: Mandatory site safety HSE work permit procedure compliance.",
        ]
    )
    bidder_pdf_1 = build_text_pdf_bytes(
        [
            "Our company holds ISO 45001 valid until 2028-06-30. "
            "Audited annual turnover is USD 8.5M."
        ]
    )
    bidder_pdf_2 = build_text_pdf_bytes(
        [
            "Corporate HSE manual and safety procedure manual valid until 2025-01-15."
        ]
    )

    # 1. POST /api/v1/documents/upload with explicit roles
    upload_resp = client.post(
        "/api/v1/documents/upload",
        files=[
            ("files", ("industrial_tender.pdf", tender_pdf, "application/pdf")),
            ("files", ("financial_iso_bidder.pdf", bidder_pdf_1, "application/pdf")),
            ("files", ("safety_bidder.pdf", bidder_pdf_2, "application/pdf")),
        ],
        data={"roles": ["TENDER", "BIDDER_SUPPORTING", "BIDDER_SUPPORTING"]},
    )
    assert upload_resp.status_code == 200
    upload_data = upload_resp.json()["data"]
    assert upload_data["total_files"] == 3
    tender_doc_id = upload_data["tender_document"]["document_id"]
    bidder_doc_ids = [b["document_id"] for b in upload_data["bidder_documents"]]

    # 2. POST /api/v1/analysis using document IDs
    analysis_resp = client.post(
        "/api/v1/analysis",
        json={
            "tender_document_id": tender_doc_id,
            "bidder_document_ids": bidder_doc_ids,
        },
    )
    assert analysis_resp.status_code == 200
    comp_data = analysis_resp.json()["data"]
    analysis_id = comp_data["analysis_id"]
    assert analysis_id.startswith("ANL-")
    assert comp_data["summary"]["total_requirements"] >= 2

    # 3. GET /api/v1/analysis/{analysis_id}
    get_resp = client.get(f"/api/v1/analysis/{analysis_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["data"]["analysis_id"] == analysis_id

    # 4. POST /api/v1/analysis/{analysis_id}/award
    award_resp = client.post(
        f"/api/v1/analysis/{analysis_id}/award",
        json={
            "contract_reference": "CTR-2026-WINNER",
            "planned_start_date": "2026-12-01",
            "site_location": "Offshore Platform Beta",
        },
    )
    assert award_resp.status_code == 200
    permit_data = award_resp.json()["data"]
    assert permit_data["contract_reference"] == "CTR-2026-WINNER"
    assert len(permit_data["checklist_items"]) >= 1

    # 5. GET /api/v1/analysis/{analysis_id}/permit-readiness
    readiness_resp = client.get(f"/api/v1/analysis/{analysis_id}/permit-readiness")
    assert readiness_resp.status_code == 200
    assert readiness_resp.json()["data"]["permit_pack_id"] == permit_data["permit_pack_id"]

    # 6. PATCH /api/v1/permit-items/{item_id}
    first_item = permit_data["checklist_items"][0]
    patch_resp = client.patch(
        f"/api/v1/permit-items/{first_item['item_id']}",
        json={
            "review_status": "approved_by_reviewer",
            "reviewer_name": "Senior HSE Inspector",
            "reviewer_role": "hse_officer",
            "is_authorized_reviewer": True,
            "reviewer_notes": "All credentials verified and valid.",
        },
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["data"]["review_status"] == "approved_by_reviewer"

    # 7. GET /api/v1/analysis/{analysis_id}/report (CSV download)
    csv_resp = client.get(f"/api/v1/analysis/{analysis_id}/report")
    assert csv_resp.status_code == 200
    assert "text/csv" in csv_resp.headers["content-type"]
    assert "attachment;" in csv_resp.headers.get("content-disposition", "")

    csv_reader = csv.reader(io.StringIO(csv_resp.text))
    rows = list(csv_reader)
    assert len(rows) >= 2  # header + data rows
    header = rows[0]
    expected_cols = [
        "requirement_id",
        "category",
        "description",
        "status",
        "evidence_filename",
        "page",
        "excerpt",
        "explanation",
        "review_state",
    ]
    assert header == expected_cols

    # 8. Check SQLite audit log trail
    audit_resp = client.get(f"/api/v1/audit/events?analysis_id={analysis_id}")
    assert audit_resp.status_code == 200
    events = audit_resp.json()["data"]["events"]
    event_types = {e["event_type"] for e in events}
    assert "COMPLIANCE_EVALUATED" in event_types
    assert "CONTRACT_AWARD_SIMULATED" in event_types
    assert "PERMIT_ITEM_REVIEWED" in event_types
    assert "REPORT_EXPORTED" in event_types

    # 9. Verify listing endpoints
    list_analysis_resp = client.get("/api/v1/analysis")
    assert list_analysis_resp.status_code == 200
    assert len(list_analysis_resp.json()["data"]) >= 1

    list_docs_resp = client.get("/api/v1/documents")
    assert list_docs_resp.status_code == 200
    assert len(list_docs_resp.json()["data"]) >= 3
