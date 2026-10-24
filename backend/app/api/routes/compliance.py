"""Tender compliance and PDF extraction endpoints."""

from __future__ import annotations

import uuid
from typing import List

from fastapi import APIRouter, File, Form, UploadFile

from app.core.config import get_settings
from app.core.exceptions import UploadLimitExceededError
from app.core.logging import get_logger, get_request_id
from app.models.analysis_record import AnalysisRepository
from app.models.audit_record import AuditRepository
from app.models.document_record import DocumentRepository
from app.schemas.audit import AuditActorType, AuditEventType
from app.schemas.common import ApiMeta, ApiResponse, ProcessingState
from app.schemas.compliance import ComplianceAnalysisResult
from app.schemas.document import DocumentExtractionResult, DocumentRole
from app.services.compliance_rules import ComplianceRulesService
from app.services.evidence_matcher import EvidenceMatcherService
from app.services.pdf_extractor import PDFExtractorService
from app.services.requirement_extractor import RequirementExtractorService

logger = get_logger(__name__)
router = APIRouter(prefix="/api/v1/compliance", tags=["Compliance Analysis"])


@router.post("/extract", response_model=ApiResponse[DocumentExtractionResult])
async def extract_document_pages(
    file: UploadFile = File(..., description="Text-based PDF file to extract."),
    role: DocumentRole = Form(default=DocumentRole.TENDER),
) -> ApiResponse[DocumentExtractionResult]:
    """Extract page-level text and metadata from a single PDF document."""
    settings = get_settings()
    extractor = PDFExtractorService(settings)
    audit_repo = AuditRepository(settings.sqlite_db_path)

    content_bytes = await file.read()
    doc_id = f"DOC-{role.value[:3]}-{uuid.uuid4().hex[:6].upper()}"

    extraction = extractor.extract_from_bytes(
        document_id=doc_id,
        filename=file.filename or "document.pdf",
        content_bytes=content_bytes,
        role=role,
        content_type=file.content_type or "application/pdf",
    )

    audit_repo.record_event(
        event_type=AuditEventType.PDF_EXTRACTED,
        actor=AuditActorType.USER,
        summary=f"Extracted {extraction.metadata.page_count} page(s) from '{extraction.metadata.filename}'.",
        details={
            "document_id": doc_id,
            "filename": extraction.metadata.filename,
            "page_count": extraction.metadata.page_count,
            "total_chars": extraction.total_chars,
        },
    )

    return ApiResponse[DocumentExtractionResult](
        success=True,
        data=extraction,
        meta=ApiMeta(
            request_id=get_request_id(),
            processing_state=ProcessingState.COMPLETED,
            version=settings.app_version,
            warnings=extraction.extraction_warnings,
        ),
    )


@router.post("/analyze", response_model=ApiResponse[ComplianceAnalysisResult])
async def analyze_tender_compliance(
    tender_file: UploadFile = File(
        ..., description="Primary text-based tender PDF document."
    ),
    bidder_files: List[UploadFile] = File(
        ..., description="One or more bidder supporting PDF documents."
    ),
) -> ApiResponse[ComplianceAnalysisResult]:
    """Upload one tender PDF and one or more bidder PDFs to run compliance intelligence."""
    settings = get_settings()

    if len(bidder_files) == 0:
        raise UploadLimitExceededError(
            "At least one bidder supporting PDF file must be provided."
        )

    if len(bidder_files) > settings.max_bidder_files:
        raise UploadLimitExceededError(
            f"Uploaded {len(bidder_files)} bidder files, exceeding the maximum "
            f"limit of {settings.max_bidder_files} files."
        )

    analysis_id = f"ANL-{uuid.uuid4().hex[:8].upper()}"
    pdf_extractor = PDFExtractorService(settings)
    req_extractor = RequirementExtractorService()
    evidence_matcher = EvidenceMatcherService()
    rules_service = ComplianceRulesService()
    doc_repo = DocumentRepository(settings.sqlite_db_path)
    analysis_repo = AnalysisRepository(settings.sqlite_db_path)
    audit_repo = AuditRepository(settings.sqlite_db_path)

    warnings: List[str] = []

    # 1. Extract tender PDF
    tender_bytes = await tender_file.read()
    tender_extraction = pdf_extractor.extract_from_bytes(
        document_id="DOC-TENDER-001",
        filename=tender_file.filename or "tender.pdf",
        content_bytes=tender_bytes,
        role=DocumentRole.TENDER,
        content_type=tender_file.content_type or "application/pdf",
    )
    doc_repo.save_document(tender_extraction)
    warnings.extend(tender_extraction.extraction_warnings)

    # 2. Extract bidder supporting PDFs
    bidder_extractions: List[DocumentExtractionResult] = []
    for idx, b_file in enumerate(bidder_files, start=1):
        b_bytes = await b_file.read()
        b_extraction = pdf_extractor.extract_from_bytes(
            document_id=f"DOC-BIDDER-{idx:03d}",
            filename=b_file.filename or f"bidder_{idx}.pdf",
            content_bytes=b_bytes,
            role=DocumentRole.BIDDER_SUPPORTING,
            content_type=b_file.content_type or "application/pdf",
        )
        doc_repo.save_document(b_extraction)
        warnings.extend(b_extraction.extraction_warnings)
        bidder_extractions.append(b_extraction)

    audit_repo.record_event(
        event_type=AuditEventType.DOCUMENTS_UPLOADED,
        analysis_id=analysis_id,
        actor=AuditActorType.USER,
        summary=(
            f"Uploaded tender '{tender_extraction.metadata.filename}' and "
            f"{len(bidder_extractions)} bidder supporting PDF(s)."
        ),
        details={
            "tender_filename": tender_extraction.metadata.filename,
            "bidder_filenames": [b.metadata.filename for b in bidder_extractions],
        },
    )

    # 3. Identify tender requirements
    requirements = req_extractor.extract_requirements(tender_extraction)

    # 4. Match against bidder evidence
    matched_evidence_map = evidence_matcher.match_evidence(
        requirements=requirements,
        bidder_extractions=bidder_extractions,
    )

    # 5. Evaluate compliance status and compute summary metrics
    assessments = rules_service.evaluate_requirements(
        requirements=requirements,
        matched_evidence_map=matched_evidence_map,
    )
    summary = rules_service.build_summary(
        requirements=requirements,
        assessments=assessments,
    )

    result = ComplianceAnalysisResult(
        analysis_id=analysis_id,
        processing_state=ProcessingState.COMPLETED,
        tender_document=tender_extraction.metadata,
        bidder_documents=[b.metadata for b in bidder_extractions],
        requirements=requirements,
        assessments=assessments,
        summary=summary,
    )

    analysis_repo.save_analysis(result)

    audit_repo.record_event(
        event_type=AuditEventType.COMPLIANCE_EVALUATED,
        analysis_id=analysis_id,
        actor=AuditActorType.SYSTEM,
        summary=(
            f"Evaluated {summary.total_requirements} requirement(s): "
            f"{summary.evidence_found_count} Evidence Found, {summary.missing_count} Missing."
        ),
        details=summary.model_dump(),
    )

    return ApiResponse[ComplianceAnalysisResult](
        success=True,
        data=result,
        meta=ApiMeta(
            request_id=get_request_id(),
            processing_state=ProcessingState.COMPLETED,
            version=settings.app_version,
            warnings=warnings,
        ),
    )
