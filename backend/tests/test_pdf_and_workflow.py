"""Tests for PDF extraction, temp cleanup, compliance workflow, permit readiness, audit, and export."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app.core.config import get_settings
from tests.conftest import build_text_pdf_bytes


def test_rejects_non_pdf_file_with_structured_error(client: TestClient) -> None:
    response = client.post(
        "/api/v1/compliance/extract",
        files={"file": ("malicious.txt", b"not a pdf file", "text/plain")},
    )
    assert response.status_code == 400
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "INVALID_FILE_TYPE"
    assert body["meta"]["processing_state"] == "FAILED"


def test_pdf_extraction_and_temp_file_cleanup(client: TestClient) -> None:
    pdf_bytes = build_text_pdf_bytes(
        [
            "Page 1: Bidder must be registered and have ISO 9001 certification.",
            "Page 2: Safety HSE work permit procedures are mandatory on site.",
        ]
    )

    response = client.post(
        "/api/v1/compliance/extract",
        files={"file": ("sample_tender.pdf", pdf_bytes, "application/pdf")},
        data={"role": "TENDER"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True

    data = body["data"]
    assert data["metadata"]["filename"] == "sample_tender.pdf"
    assert data["metadata"]["page_count"] == 2
    assert len(data["pages"]) == 2
    assert data["pages"][0]["page_number"] == 1
    assert "ISO 9001" in data["pages"][0]["text"]

    # Ensure temporary upload directory has no leftover b2w_*.pdf files
    temp_dir = Path(get_settings().temp_upload_dir)
    leftover = list(temp_dir.glob("b2w_*.pdf"))
    assert leftover == []


def test_end_to_end_foundational_workflow(client: TestClient) -> None:
    tender_pdf = build_text_pdf_bytes(
        [
            "Clause 1.1: Bidder must hold valid ISO 45001 certification. "
            "Clause 1.2: Minimum annual turnover of USD 5M financial capacity required.",
            "Clause 2.1: Mandatory HSE safety plan and confined space work permit compliance.",
        ]
    )
    bidder_pdf_1 = build_text_pdf_bytes(
        [
            "Our company holds ISO 45001 certificate valid until 2028-06-30. "
            "Audited annual turnover is USD 8.5M."
        ]
    )
    bidder_pdf_2 = build_text_pdf_bytes(
        [
            "Corporate HSE safety manual and confined space work permit training valid until 2025-01-15."
        ]
    )

    # 1. Analyze compliance
    analyze_resp = client.post(
        "/api/v1/compliance/analyze",
        files=[
            ("tender_file", ("industrial_tender.pdf", tender_pdf, "application/pdf")),
            ("bidder_files", ("bidder_financials_iso.pdf", bidder_pdf_1, "application/pdf")),
            ("bidder_files", ("bidder_hse_manual.pdf", bidder_pdf_2, "application/pdf")),
        ],
    )
    assert analyze_resp.status_code == 200
    comp_data = analyze_resp.json()["data"]
    analysis_id = comp_data["analysis_id"]
    assert analysis_id.startswith("ANL-")
    assert comp_data["summary"]["total_requirements"] >= 2
    assert len(comp_data["assessments"]) == comp_data["summary"]["total_requirements"]

    # 2. Simulate contract award & work-permit readiness
    permit_resp = client.post(
        "/api/v1/permits/simulate-award",
        json={
            "analysis_id": analysis_id,
            "contract_reference": "CTR-2026-900",
            "planned_start_date": "2026-11-01",
            "site_location": "Refinery Unit 4",
            "tender_requirements": comp_data["requirements"],
            "assessments": comp_data["assessments"],
        },
    )
    assert permit_resp.status_code == 200
    permit_data = permit_resp.json()["data"]
    assert permit_data["permit_pack_id"].startswith("PCK-")
    assert permit_data["summary"]["total_items"] >= 1
    # Bidder 2 had an expiry date of 2025-01-15 which is before 2026-11-01
    assert permit_data["summary"]["expired_count"] >= 1

    # 3. Check audit trail events
    audit_resp = client.get(f"/api/v1/audit/events?analysis_id={analysis_id}")
    assert audit_resp.status_code == 200
    audit_data = audit_resp.json()["data"]
    assert audit_data["total"] >= 3

    # 4. Export Markdown report
    export_resp = client.post(
        "/api/v1/reports/export",
        json={
            "analysis_id": analysis_id,
            "format": "MARKDOWN",
            "include_permit_checklist": True,
            "include_audit_trail": True,
            "compliance_result": comp_data,
            "permit_result": permit_data,
        },
    )
    assert export_resp.status_code == 200
    report_data = export_resp.json()["data"]
    assert report_data["report_id"].startswith("RPT-")
    assert report_data["filename"].endswith(".md")
    assert "Bid2Work AI" in report_data["content"]
