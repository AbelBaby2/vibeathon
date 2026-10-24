"""Document metadata and page-level PDF extraction schemas."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class DocumentRole(str, Enum):
    """Classification of an uploaded PDF in the Bid2Work workflow."""

    TENDER = "TENDER"
    BIDDER_SUPPORTING = "BIDDER_SUPPORTING"
    SAFETY_PERMIT = "SAFETY_PERMIT"

    @classmethod
    def _missing_(cls, value: object):
        if isinstance(value, str):
            v_upper = value.strip().upper().replace(" ", "_").replace("-", "_")
            for member in cls:
                if member.value == v_upper or member.name == v_upper:
                    return member
        return super()._missing_(value)


class ExtractedPage(BaseModel):
    """Page-level extracted text and metrics retained for source traceability."""

    page_number: int = Field(..., ge=1, description="1-based page number in the source PDF.")
    text: str = Field(..., description="Extracted plain text content from the page.")
    char_count: int = Field(..., ge=0, description="Character count of extracted text.")
    word_count: int = Field(..., ge=0, description="Approximate word count on the page.")


DocumentPage = ExtractedPage


class DocumentMetadata(BaseModel):
    """Metadata describing an uploaded PDF document."""

    document_id: str = Field(
        ...,
        min_length=3,
        description="Stable unique identifier for the document (e.g., DOC-TENDER-001).",
    )
    filename: str = Field(..., min_length=1, description="Original sanitized filename.")
    role: DocumentRole = Field(..., description="Functional role of the document.")
    file_size_bytes: int = Field(..., ge=0, description="File size in bytes.")
    page_count: int = Field(..., ge=0, description="Total number of pages in the PDF.")
    content_type: str = Field(
        default="application/pdf", description="MIME type of the uploaded file."
    )
    uploaded_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp when the document was processed.",
    )
    sha256_hash: Optional[str] = Field(
        default=None, description="SHA-256 digest of the file content for audit integrity."
    )


class DocumentExtractionResult(BaseModel):
    """Complete result of extracting page-level text from a PDF document."""

    metadata: DocumentMetadata = Field(..., description="Document metadata.")
    pages: List[ExtractedPage] = Field(
        default_factory=list,
        description="Ordered list of extracted pages with 1-based page numbers.",
    )
    total_chars: int = Field(..., ge=0, description="Total characters extracted across all pages.")
    is_text_based: bool = Field(
        ...,
        description="True if sufficient machine-readable text was extracted; False if likely scanned/empty.",
    )
    extraction_warnings: List[str] = Field(
        default_factory=list,
        description="Warnings encountered during extraction (e.g., empty pages).",
    )


class DocumentUploadBatchResponse(BaseModel):
    """Result of uploading one or more documents with explicit roles."""

    uploaded_documents: List[DocumentMetadata] = Field(
        default_factory=list, description="Metadata for all successfully processed documents."
    )
    tender_document: Optional[DocumentMetadata] = Field(
        default=None, description="Metadata for uploaded tender document, if present."
    )
    bidder_documents: List[DocumentMetadata] = Field(
        default_factory=list, description="Metadata for uploaded bidder documents."
    )
    total_files: int = Field(..., ge=0, description="Total count of uploaded files.")
    warnings: List[str] = Field(
        default_factory=list, description="Extraction or processing warnings."
    )

