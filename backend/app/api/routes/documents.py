"""Document upload and role classification endpoints."""

from __future__ import annotations

import uuid
from typing import List, Optional

from fastapi import APIRouter, Request, UploadFile

from app.core.config import get_settings
from app.core.exceptions import InvalidFileTypeError, UploadLimitExceededError
from app.core.logging import get_logger, get_request_id
from app.models.audit_record import AuditRepository
from app.models.document_record import DocumentRepository
from app.schemas.audit import AuditActorType, AuditEventType
from app.schemas.common import ApiMeta, ApiResponse, ProcessingState
from app.schemas.document import (
    DocumentExtractionResult,
    DocumentMetadata,
    DocumentRole,
    DocumentUploadBatchResponse,
)
from app.services.pdf_extractor import PDFExtractorService

logger = get_logger(__name__)
router = APIRouter(prefix="/api/v1/documents", tags=["Document Management"])


@router.post("/upload", response_model=ApiResponse[DocumentUploadBatchResponse])
async def upload_documents(
    request: Request,
) -> ApiResponse[DocumentUploadBatchResponse]:
    """Upload tender and bidder PDFs with explicit document roles and persist extracted content."""
    settings = get_settings()
    form = await request.form()

    # Collect files from form
    files: List[UploadFile] = []
    for key, value in form.multi_items():
        if isinstance(value, UploadFile) or (hasattr(value, "file") and hasattr(value, "filename")):
            files.append(value)

    if not files:
        raise InvalidFileTypeError("No files provided in upload request.")

    if len(files) > (settings.max_bidder_files + 1):
        raise UploadLimitExceededError(
            f"Uploaded {len(files)} files, exceeding maximum allowed batch size of {settings.max_bidder_files + 1}."
        )

    roles_list = form.getlist("roles")
    if len(roles_list) == 1 and "," in roles_list[0]:
        roles_list = [r.strip() for r in roles_list[0].split(",") if r.strip()]

    default_role = form.get("role")

    pdf_extractor = PDFExtractorService(settings)
    doc_repo = DocumentRepository(settings.sqlite_db_path)
    audit_repo = AuditRepository(settings.sqlite_db_path)

    uploaded_metadata: List[DocumentMetadata] = []
    tender_meta: Optional[DocumentMetadata] = None
    bidder_metas: List[DocumentMetadata] = []
    all_warnings: List[str] = []

    for idx, upload_file in enumerate(files):
        # Determine explicit role for this file
        assigned_role: DocumentRole
        if roles_list and idx < len(roles_list) and roles_list[idx]:
            try:
                assigned_role = DocumentRole(roles_list[idx])
            except ValueError:
                assigned_role = DocumentRole.BIDDER_SUPPORTING
        elif default_role:
            try:
                assigned_role = DocumentRole(default_role)
            except ValueError:
                assigned_role = DocumentRole.BIDDER_SUPPORTING
        else:
            # Infer role if not explicitly provided
            fname_lower = (upload_file.filename or "").lower()
            if "tender" in fname_lower or "rfp" in fname_lower:
                assigned_role = DocumentRole.TENDER
            elif "safety" in fname_lower or "permit" in fname_lower:
                assigned_role = DocumentRole.SAFETY_PERMIT
            else:
                assigned_role = DocumentRole.BIDDER_SUPPORTING

        doc_prefix = "TENDER" if assigned_role == DocumentRole.TENDER else "BIDDER"
        doc_id = f"DOC-{doc_prefix}-{uuid.uuid4().hex[:6].upper()}"

        content_bytes = await upload_file.read()
        extraction: DocumentExtractionResult = pdf_extractor.extract_from_bytes(
            document_id=doc_id,
            filename=upload_file.filename or f"upload_{idx + 1}.pdf",
            content_bytes=content_bytes,
            role=assigned_role,
            content_type=upload_file.content_type or "application/pdf",
        )

        # Persist extracted document
        doc_repo.save_document(extraction)

        meta = extraction.metadata
        uploaded_metadata.append(meta)
        all_warnings.extend(extraction.extraction_warnings)

        if assigned_role == DocumentRole.TENDER:
            tender_meta = meta
        else:
            bidder_metas.append(meta)

    # Record audit event
    audit_repo.record_event(
        event_type=AuditEventType.DOCUMENTS_UPLOADED,
        actor=AuditActorType.USER,
        summary=f"Uploaded and extracted {len(files)} document(s) with explicit roles.",
        details={
            "total_files": len(files),
            "tender": tender_meta.filename if tender_meta else None,
            "bidder_files": [b.filename for b in bidder_metas],
        },
    )

    batch_resp = DocumentUploadBatchResponse(
        uploaded_documents=uploaded_metadata,
        tender_document=tender_meta,
        bidder_documents=bidder_metas,
        total_files=len(files),
        warnings=all_warnings,
    )

    return ApiResponse[DocumentUploadBatchResponse](
        success=True,
        data=batch_resp,
        meta=ApiMeta(
            request_id=get_request_id(),
            processing_state=ProcessingState.COMPLETED,
            version=settings.app_version,
            warnings=all_warnings,
        ),
    )
