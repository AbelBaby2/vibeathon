"""Tender compliance analysis, contract award simulation, and CSV reporting endpoints."""

from __future__ import annotations

import uuid
from typing import List, Optional

from fastapi import APIRouter, Body, Depends, File, Form, Request, Response, UploadFile
from pydantic import BaseModel, Field

from app.core.config import get_settings
from app.core.exceptions import (
    InvalidFileTypeError,
    NotFoundError,
    UploadLimitExceededError,
)
from app.core.logging import get_logger, get_request_id
from app.models.analysis_record import AnalysisRepository
from app.models.audit_record import AuditRepository
from app.models.document_record import DocumentRepository
from app.models.permit_record import PermitRepository
from app.schemas.audit import AuditActorType, AuditEventType
from app.schemas.common import ApiMeta, ApiResponse, ProcessingState
from app.schemas.compliance import ComplianceAnalysisResult
from app.schemas.document import DocumentExtractionResult, DocumentRole
from app.schemas.permit import AwardSimulationRequest, PermitReadinessResult
from app.services.compliance_rules import ComplianceRulesService
from app.services.evidence_matcher import EvidenceMatcherService
from app.services.pdf_extractor import PDFExtractorService
from app.services.permit_readiness import PermitReadinessService
from app.services.report_generator import ReportGeneratorService
from app.services.requirement_extractor import RequirementExtractorService

logger = get_logger(__name__)
router = APIRouter(prefix="/api/v1/analysis", tags=["Compliance Analysis"])


class AnalysisCreateRequest(BaseModel):
    """Payload to trigger compliance intelligence using pre-uploaded documents."""

    tender_document_id: Optional[str] = Field(
        default=None, description="Document ID of the uploaded tender PDF."
    )
    bidder_document_ids: Optional[List[str]] = Field(
        default=None, description="List of Document IDs for bidder supporting PDFs."
    )
    document_ids: Optional[List[str]] = Field(
        default=None, description="Optional combined list of document IDs."
    )


class AwardRequestPayload(BaseModel):
    """Optional payload when simulating contract award for an existing analysis."""

    contract_reference: Optional[str] = Field(
        default="CTR-SIM-001", description="Simulated contract reference code."
    )
    planned_start_date: Optional[str] = Field(
        default=None, description="Planned site mobilization date (YYYY-MM-DD)."
    )
    site_location: Optional[str] = Field(
        default="Primary Operational Site", description="Operational site or facility."
    )


@router.post("", response_model=ApiResponse[ComplianceAnalysisResult])
async def create_analysis(
    request: Request,
) -> ApiResponse[ComplianceAnalysisResult]:
    """Analyse uploaded documents to produce compliance intelligence."""
    settings = get_settings()
    content_type = request.headers.get("content-type", "")

    doc_repo = DocumentRepository(settings.sqlite_db_path)
    analysis_repo = AnalysisRepository(settings.sqlite_db_path)
    audit_repo = AuditRepository(settings.sqlite_db_path)
    pdf_extractor = PDFExtractorService(settings)
    req_extractor = RequirementExtractorService(settings=settings)
    evidence_matcher = EvidenceMatcherService(settings=settings)
    rules_service = ComplianceRulesService()

    warnings: List[str] = []
    tender_extraction: Optional[DocumentExtractionResult] = None
    bidder_extractions: List[DocumentExtractionResult] = []

    # Case A: Multipart form upload direct to /analysis
    if "multipart/form-data" in content_type:
        form = await request.form()
        tender_file = form.get("tender_file")
        raw_bidder_files = form.getlist("bidder_files")

        if not tender_file or not hasattr(tender_file, "read"):
            # Check if files were sent with 'files' and 'roles'
            all_files = form.getlist("files")
            if all_files:
                for idx, f in enumerate(all_files):
                    f_bytes = await f.read()
                    role_str = form.get(f"role_{idx}") or ("TENDER" if idx == 0 else "BIDDER_SUPPORTING")
                    role = DocumentRole(role_str)
                    doc_id = f"DOC-{role.value[:3]}-{uuid.uuid4().hex[:6].upper()}"
                    ext = pdf_extractor.extract_from_bytes(
                        document_id=doc_id,
                        filename=f.filename or f"doc_{idx}.pdf",
                        content_bytes=f_bytes,
                        role=role,
                    )
                    doc_repo.save_document(ext)
                    if role == DocumentRole.TENDER and not tender_extraction:
                        tender_extraction = ext
                    else:
                        bidder_extractions.append(ext)
            else:
                raise InvalidFileTypeError("Primary tender_file is required for analysis.")
        else:
            t_bytes = await tender_file.read()
            tender_extraction = pdf_extractor.extract_from_bytes(
                document_id="DOC-TENDER-001",
                filename=getattr(tender_file, "filename", "tender.pdf"),
                content_bytes=t_bytes,
                role=DocumentRole.TENDER,
            )
            doc_repo.save_document(tender_extraction)

            for idx, b_file in enumerate(raw_bidder_files, start=1):
                b_bytes = await b_file.read()
                b_ext = pdf_extractor.extract_from_bytes(
                    document_id=f"DOC-BIDDER-{idx:03d}",
                    filename=getattr(b_file, "filename", f"bidder_{idx}.pdf"),
                    content_bytes=b_bytes,
                    role=DocumentRole.BIDDER_SUPPORTING,
                )
                doc_repo.save_document(b_ext)
                bidder_extractions.append(b_ext)
    else:
        # Case B: JSON body with document_ids
        try:
            body_dict = await request.json()
        except Exception:
            body_dict = {}

        tender_id = body_dict.get("tender_document_id")
        bidder_ids = body_dict.get("bidder_document_ids") or []
        doc_ids = body_dict.get("document_ids") or []

        if not tender_id and doc_ids:
            # Look up first document with role TENDER
            for d_id in doc_ids:
                doc = doc_repo.get_document(d_id)
                if doc and doc.metadata.role == DocumentRole.TENDER:
                    tender_id = d_id
                    break
            if not tender_id and doc_ids:
                tender_id = doc_ids[0]

        if not tender_id:
            # Fallback to the most recently uploaded tender document
            tenders = doc_repo.list_documents(role=DocumentRole.TENDER)
            if tenders:
                tender_id = tenders[0].document_id

        if not tender_id:
            raise NotFoundError("No tender document specified or found in repository. Please upload a tender PDF first.")

        tender_extraction = doc_repo.get_document(tender_id)
        if not tender_extraction:
            raise NotFoundError(f"Tender document '{tender_id}' not found.")

        # Identify bidder documents
        if not bidder_ids:
            if doc_ids:
                bidder_ids = [d for d in doc_ids if d != tender_id]
            else:
                bidders = doc_repo.list_documents(role=DocumentRole.BIDDER_SUPPORTING)
                bidder_ids = [b.document_id for b in bidders]

        for b_id in bidder_ids:
            b_ext = doc_repo.get_document(b_id)
            if b_ext:
                bidder_extractions.append(b_ext)

    if not tender_extraction:
        raise NotFoundError("Tender document could not be resolved.")

    if not bidder_extractions:
        raise UploadLimitExceededError("At least one bidder supporting document is required for compliance analysis.")

    warnings.extend(tender_extraction.extraction_warnings)
    for b in bidder_extractions:
        warnings.extend(b.extraction_warnings)

    analysis_id = f"ANL-{uuid.uuid4().hex[:8].upper()}"

    # 1. Extract tender requirements
    if settings.llm_enabled:
        requirements = await req_extractor.extract_requirements_async(tender_extraction)
    else:
        requirements = req_extractor.extract_requirements(tender_extraction)

    # 2. Match against bidder evidence
    if settings.llm_enabled:
        evidence_map = await evidence_matcher.match_evidence_async(
            requirements=requirements,
            bidder_extractions=bidder_extractions,
        )
    else:
        evidence_map = evidence_matcher.match_evidence(
            requirements=requirements,
            bidder_extractions=bidder_extractions,
        )

    # 3. Evaluate compliance
    assessments = rules_service.evaluate_requirements(
        requirements=requirements,
        matched_evidence_map=evidence_map,
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

    # Persist analysis
    analysis_repo.save_analysis(result)

    # Record audit event
    audit_repo.record_event(
        event_type=AuditEventType.COMPLIANCE_EVALUATED,
        analysis_id=analysis_id,
        actor=AuditActorType.SYSTEM,
        summary=(
            f"Executed compliance analysis '{analysis_id}': {summary.total_requirements} requirement(s), "
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


@router.get("/{analysis_id}", response_model=ApiResponse[ComplianceAnalysisResult])
async def get_analysis(analysis_id: str) -> ApiResponse[ComplianceAnalysisResult]:
    """Retrieve compliance analysis results by analysis_id."""
    settings = get_settings()
    analysis_repo = AnalysisRepository(settings.sqlite_db_path)
    result = analysis_repo.get_analysis(analysis_id)

    if not result:
        raise NotFoundError(f"Compliance analysis '{analysis_id}' was not found.")

    return ApiResponse[ComplianceAnalysisResult](
        success=True,
        data=result,
        meta=ApiMeta(
            request_id=get_request_id(),
            processing_state=ProcessingState.COMPLETED,
            version=settings.app_version,
        ),
    )


@router.post("/{analysis_id}/award", response_model=ApiResponse[PermitReadinessResult])
async def simulate_contract_award_for_analysis(
    analysis_id: str,
    payload: AwardRequestPayload = Body(default_factory=AwardRequestPayload),
) -> ApiResponse[PermitReadinessResult]:
    """Simulate contract award and generate the work-permit readiness checklist."""
    settings = get_settings()
    analysis_repo = AnalysisRepository(settings.sqlite_db_path)
    permit_repo = PermitRepository(settings.sqlite_db_path)
    audit_repo = AuditRepository(settings.sqlite_db_path)
    permit_service = PermitReadinessService()

    analysis = analysis_repo.get_analysis(analysis_id)
    if not analysis:
        raise NotFoundError(f"Compliance analysis '{analysis_id}' was not found.")

    sim_request = AwardSimulationRequest(
        analysis_id=analysis_id,
        contract_reference=payload.contract_reference or "CTR-SIM-001",
        planned_start_date=payload.planned_start_date,
        site_location=payload.site_location,
        tender_requirements=analysis.requirements,
        assessments=analysis.assessments,
    )

    result = permit_service.simulate_award_and_build_checklist(sim_request)
    permit_repo.save_checklist(result)

    audit_repo.record_event(
        event_type=AuditEventType.CONTRACT_AWARD_SIMULATED,
        analysis_id=analysis_id,
        actor=AuditActorType.USER,
        summary=(
            f"Simulated contract award for '{analysis_id}' ({result.contract_reference}): "
            f"generated {result.summary.total_items} work-permit checklist item(s)."
        ),
        details={
            "permit_pack_id": result.permit_pack_id,
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


@router.get("/{analysis_id}/permit-readiness", response_model=ApiResponse[PermitReadinessResult])
async def get_permit_readiness(analysis_id: str) -> ApiResponse[PermitReadinessResult]:
    """Retrieve post-award work-permit checklist and readiness status."""
    settings = get_settings()
    analysis_repo = AnalysisRepository(settings.sqlite_db_path)
    permit_repo = PermitRepository(settings.sqlite_db_path)

    # First check if the analysis exists
    analysis = analysis_repo.get_analysis(analysis_id)
    if not analysis:
        raise NotFoundError(f"Compliance analysis '{analysis_id}' was not found.")

    permit_res = permit_repo.get_checklist_by_analysis(analysis_id)
    if not permit_res:
        # Auto-simulate award with defaults if not already simulated
        permit_service = PermitReadinessService()
        audit_repo = AuditRepository(settings.sqlite_db_path)
        sim_request = AwardSimulationRequest(
            analysis_id=analysis_id,
            contract_reference="CTR-AUTO-001",
            tender_requirements=analysis.requirements,
            assessments=analysis.assessments,
        )
        permit_res = permit_service.simulate_award_and_build_checklist(sim_request)
        permit_repo.save_checklist(permit_res)
        audit_repo.record_event(
            event_type=AuditEventType.PERMIT_CHECKLIST_GENERATED,
            analysis_id=analysis_id,
            actor=AuditActorType.SYSTEM,
            summary=f"Auto-generated permit readiness checklist for analysis '{analysis_id}'.",
            details={"permit_pack_id": permit_res.permit_pack_id},
        )

    return ApiResponse[PermitReadinessResult](
        success=True,
        data=permit_res,
        meta=ApiMeta(
            request_id=get_request_id(),
            processing_state=ProcessingState.COMPLETED,
            version=settings.app_version,
        ),
    )


@router.get("/{analysis_id}/report")
async def download_compliance_csv_report(analysis_id: str) -> Response:
    """Download a consolidated compliance report as a CSV file."""
    settings = get_settings()
    analysis_repo = AnalysisRepository(settings.sqlite_db_path)
    permit_repo = PermitRepository(settings.sqlite_db_path)
    audit_repo = AuditRepository(settings.sqlite_db_path)
    report_service = ReportGeneratorService()

    analysis = analysis_repo.get_analysis(analysis_id)
    if not analysis:
        raise NotFoundError(f"Compliance analysis '{analysis_id}' was not found.")

    permit = permit_repo.get_checklist_by_analysis(analysis_id)
    csv_content = report_service.generate_compliance_csv(analysis, permit)

    audit_repo.record_event(
        event_type=AuditEventType.REPORT_EXPORTED,
        analysis_id=analysis_id,
        actor=AuditActorType.USER,
        summary=f"Downloaded CSV compliance report for analysis '{analysis_id}'.",
        details={"analysis_id": analysis_id, "format": "CSV"},
    )

    filename = f"compliance_report_{analysis_id.lower()}.csv"
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "X-Request-ID": get_request_id(),
        },
    )
