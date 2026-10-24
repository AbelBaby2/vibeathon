"""Tests for PDF extraction, empty pages, scanned detection, encrypted files, and upload limits."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.core.exceptions import InvalidFileTypeError, PDFExtractionError, UploadLimitExceededError
from app.schemas.document import DocumentRole
from app.services.pdf_extractor import PDFExtractorService
from tests.conftest import build_empty_pdf_bytes, build_encrypted_pdf_bytes, build_text_pdf_bytes


def test_rejects_empty_scanned_pdf_with_ocr_explanation(client: TestClient) -> None:
    """Detect likely scanned PDFs (0 extractable text) and explain OCR is not supported yet."""
    empty_pdf = build_empty_pdf_bytes(page_count=2)

    response = client.post(
        "/api/v1/compliance/extract",
        files={"file": ("scanned_blueprint.pdf", empty_pdf, "application/pdf")},
        data={"role": "TENDER"},
    )
    assert response.status_code == 422
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "PDF_EXTRACTION_ERROR"
    assert "OCR is not supported yet" in body["error"]["message"]


def test_rejects_encrypted_pdf() -> None:
    """Detect encrypted and password-protected PDFs with clear error."""
    encrypted_bytes = build_encrypted_pdf_bytes(password="supersecret")
    service = PDFExtractorService()

    try:
        service.extract_from_bytes(
            document_id="DOC-ENC-001",
            filename="protected_bid.pdf",
            content_bytes=encrypted_bytes,
            role=DocumentRole.BIDDER_SUPPORTING,
        )
        assert False, "Expected PDFExtractionError for encrypted PDF"
    except PDFExtractionError as exc:
        assert "encrypted" in exc.message.lower()


def test_rejects_invalid_magic_header_and_extension(client: TestClient) -> None:
    """Validate file type, extension, and PDF file signature."""
    # Invalid extension
    resp1 = client.post(
        "/api/v1/compliance/extract",
        files={"file": ("document.docx", b"%PDF-1.4 fake docx", "application/pdf")},
    )
    assert resp1.status_code == 400
    assert resp1.json()["error"]["code"] == "INVALID_FILE_TYPE"

    # Valid extension but invalid PDF signature
    resp2 = client.post(
        "/api/v1/compliance/extract",
        files={"file": ("fake_header.pdf", b"NOT_A_PDF_STREAM", "application/pdf")},
    )
    assert resp2.status_code == 400
    assert resp2.json()["error"]["code"] == "INVALID_FILE_TYPE"


def test_rejects_oversized_upload(monkeypatch) -> None:
    """Validate maximum upload size limits."""
    monkeypatch.setenv("MAX_UPLOAD_SIZE_MB", "1")
    get_settings.cache_clear()
    settings = get_settings()

    service = PDFExtractorService(settings)
    oversized_bytes = b"%PDF-1.4 " + (b"A" * (2 * 1024 * 1024))

    try:
        service.validate_upload("large.pdf", oversized_bytes)
        assert False, "Expected UploadLimitExceededError"
    except UploadLimitExceededError as exc:
        assert "exceeds maximum upload limit" in exc.message

    get_settings.cache_clear()


def test_handles_unicode_and_cleans_temp_files() -> None:
    """Verify text extraction, page metrics, and temporary file removal."""
    sample_pdf = build_text_pdf_bytes(
        [
            "Clause 1: Bidder ISO 9001:2015 Quality and Safety HSE Protocol. Societe Generale 5,000,000.",
            "Clause 2: Multi-page engineering inspection and work permit compliance procedure.",
        ]
    )

    settings = get_settings()
    service = PDFExtractorService(settings)
    result = service.extract_from_bytes(
        document_id="DOC-UNI-001",
        filename="sample_tender.pdf",
        content_bytes=sample_pdf,
        role=DocumentRole.TENDER,
    )

    assert result.metadata.page_count == 2
    assert result.is_text_based is True
    assert "ISO 9001:2015" in result.pages[0].text
    assert result.pages[0].page_number == 1
    assert result.pages[1].page_number == 2

    # Verify no temp files left behind
    temp_dir = Path(settings.temp_upload_dir)
    leftover = list(temp_dir.glob("b2w_*.pdf"))
    assert leftover == []
