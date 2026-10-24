"""PDF extraction service using pypdf with page-level retention and temp-file cleanup."""

from __future__ import annotations

import hashlib
import os
import re
import tempfile
from pathlib import Path
from typing import Optional

from pypdf import PdfReader
from pypdf.errors import PdfReadError

from app.core.config import Settings, get_settings
from app.core.exceptions import (
    InvalidFileTypeError,
    PDFExtractionError,
    UploadLimitExceededError,
)
from app.core.logging import get_logger
from app.schemas.document import (
    DocumentExtractionResult,
    DocumentMetadata,
    DocumentRole,
    ExtractedPage,
)

logger = get_logger(__name__)


def sanitize_filename(filename: str) -> str:
    """Sanitize an uploaded filename to prevent path traversal or control characters."""
    base = os.path.basename(filename or "document.pdf").strip()
    cleaned = re.sub(r"[^A-Za-z0-9._\- ()]", "_", base)
    return cleaned or "document.pdf"


class PDFExtractorService:
    """Service responsible for validating PDFs, managing temporary files, and extracting page text."""

    def __init__(self, settings: Optional[Settings] = None) -> None:
        self.settings = settings or get_settings()
        self._ensure_temp_dir()

    def _ensure_temp_dir(self) -> Path:
        temp_dir = Path(self.settings.temp_upload_dir)
        temp_dir.mkdir(parents=True, exist_ok=True)
        return temp_dir

    def validate_upload(
        self,
        filename: str,
        content_bytes: bytes,
        content_type: Optional[str] = None,
    ) -> str:
        """Validate filename, file size, and PDF magic header."""
        safe_name = sanitize_filename(filename)

        if not safe_name.lower().endswith(".pdf"):
            raise InvalidFileTypeError(
                f"File '{safe_name}' rejected: only .pdf files are supported."
            )

        if len(content_bytes) == 0:
            raise InvalidFileTypeError(f"File '{safe_name}' is empty (0 bytes).")

        if len(content_bytes) > self.settings.max_upload_size_bytes:
            raise UploadLimitExceededError(
                f"File '{safe_name}' ({len(content_bytes) / (1024 * 1024):.2f} MB) "
                f"exceeds maximum upload limit of {self.settings.max_upload_size_mb} MB."
            )

        if not content_bytes.lstrip().startswith(b"%PDF-"):
            raise InvalidFileTypeError(
                f"File '{safe_name}' does not have a valid PDF header."
            )

        return safe_name

    def extract_from_bytes(
        self,
        document_id: str,
        filename: str,
        content_bytes: bytes,
        role: DocumentRole,
        content_type: str = "application/pdf",
    ) -> DocumentExtractionResult:
        """Write PDF bytes to a scoped temporary file, extract page text, and always clean up."""
        safe_name = self.validate_upload(filename, content_bytes, content_type)
        sha256_hash = hashlib.sha256(content_bytes).hexdigest()
        temp_dir = self._ensure_temp_dir()
        temp_path: Optional[Path] = None

        try:
            with tempfile.NamedTemporaryFile(
                mode="wb",
                suffix=".pdf",
                prefix="b2w_",
                dir=str(temp_dir),
                delete=False,
            ) as tmp_file:
                tmp_file.write(content_bytes)
                temp_path = Path(tmp_file.name)

            return self._extract_from_path(
                temp_path=temp_path,
                document_id=document_id,
                safe_filename=safe_name,
                file_size_bytes=len(content_bytes),
                role=role,
                content_type=content_type,
                sha256_hash=sha256_hash,
            )
        finally:
            if temp_path and temp_path.exists():
                try:
                    temp_path.unlink()
                except OSError as exc:
                    logger.warning(f"Failed to remove temporary file {temp_path}: {exc}")

    def _extract_from_path(
        self,
        temp_path: Path,
        document_id: str,
        safe_filename: str,
        file_size_bytes: int,
        role: DocumentRole,
        content_type: str,
        sha256_hash: str,
    ) -> DocumentExtractionResult:
        try:
            reader = PdfReader(str(temp_path))
        except (PdfReadError, Exception) as exc:
            raise PDFExtractionError(
                f"Unable to read PDF '{safe_filename}': {exc}"
            ) from exc

        page_count = len(reader.pages)
        if page_count == 0:
            raise PDFExtractionError(f"PDF '{safe_filename}' contains 0 pages.")

        if page_count > self.settings.max_pages_per_pdf:
            raise UploadLimitExceededError(
                f"PDF '{safe_filename}' has {page_count} pages, exceeding the "
                f"maximum limit of {self.settings.max_pages_per_pdf} pages."
            )

        extracted_pages: list[ExtractedPage] = []
        warnings: list[str] = []
        total_chars = 0

        for idx, page in enumerate(reader.pages, start=1):
            try:
                raw_text = page.extract_text() or ""
            except Exception as exc:
                raw_text = ""
                warnings.append(
                    f"Page {idx} of '{safe_filename}' raised an extraction warning: {exc}"
                )

            normalized_text = raw_text.strip()
            char_count = len(normalized_text)
            word_count = len(normalized_text.split()) if normalized_text else 0
            total_chars += char_count

            if char_count == 0:
                warnings.append(
                    f"Page {idx} of '{safe_filename}' contains no extractable text (may be scanned or blank)."
                )

            extracted_pages.append(
                ExtractedPage(
                    page_number=idx,
                    text=normalized_text,
                    char_count=char_count,
                    word_count=word_count,
                )
            )

        is_text_based = total_chars >= 20
        if not is_text_based:
            warnings.append(
                f"Document '{safe_filename}' yielded minimal text ({total_chars} chars). "
                "Bid2Work AI MVP requires text-based PDFs."
            )

        metadata = DocumentMetadata(
            document_id=document_id,
            filename=safe_filename,
            role=role,
            file_size_bytes=file_size_bytes,
            page_count=page_count,
            content_type=content_type or "application/pdf",
            sha256_hash=sha256_hash,
        )

        return DocumentExtractionResult(
            metadata=metadata,
            pages=extracted_pages,
            total_chars=total_chars,
            is_text_based=is_text_based,
            extraction_warnings=warnings,
        )
