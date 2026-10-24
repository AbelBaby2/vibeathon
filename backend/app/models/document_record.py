"""Repository for persisting and retrieving uploaded PDF extraction records."""

from __future__ import annotations

import json
import sqlite3
from typing import Dict, List, Optional

from app.core.logging import get_logger
from app.db.sqlite import init_sqlite_db, sqlite_connection
from app.schemas.document import (
    DocumentExtractionResult,
    DocumentMetadata,
    DocumentRole,
    ExtractedPage,
)

logger = get_logger(__name__)

_FALLBACK_DOCS: Dict[str, DocumentExtractionResult] = {}


class DocumentRepository:
    """Manages storage of extracted document metadata and page text."""

    def __init__(self, db_path: Optional[str] = None) -> None:
        self.db_path = db_path
        init_sqlite_db(self.db_path)

    def save_document(self, result: DocumentExtractionResult) -> DocumentExtractionResult:
        """Persist a document extraction result to SQLite with in-memory fallback."""
        doc = result.metadata
        pages_payload = [p.model_dump(mode="json") for p in result.pages]

        try:
            with sqlite_connection(self.db_path) as conn:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO uploaded_documents (
                        document_id, filename, role, file_size_bytes, page_count,
                        content_type, sha256_hash, pages_json, total_chars,
                        is_text_based, uploaded_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        doc.document_id,
                        doc.filename,
                        doc.role.value,
                        doc.file_size_bytes,
                        doc.page_count,
                        doc.content_type,
                        doc.sha256_hash,
                        json.dumps(pages_payload),
                        result.total_chars,
                        1 if result.is_text_based else 0,
                        doc.uploaded_at.isoformat(),
                    ),
                )
        except (sqlite3.Error, OSError) as exc:
            logger.warning(f"Document stored in fallback memory buffer: {exc}")

        _FALLBACK_DOCS[doc.document_id] = result
        return result

    def get_document(self, document_id: str) -> Optional[DocumentExtractionResult]:
        """Retrieve a document extraction result by document_id."""
        if document_id in _FALLBACK_DOCS:
            return _FALLBACK_DOCS[document_id]

        try:
            with sqlite_connection(self.db_path) as conn:
                row = conn.execute(
                    """
                    SELECT document_id, filename, role, file_size_bytes, page_count,
                           content_type, sha256_hash, pages_json, total_chars,
                           is_text_based, uploaded_at
                    FROM uploaded_documents
                    WHERE document_id = ?
                    """,
                    (document_id,),
                ).fetchone()

            if not row:
                return None

            pages_raw = json.loads(row["pages_json"] or "[]")
            pages = [ExtractedPage(**p) for p in pages_raw]
            metadata = DocumentMetadata(
                document_id=row["document_id"],
                filename=row["filename"],
                role=DocumentRole(row["role"]),
                file_size_bytes=row["file_size_bytes"],
                page_count=row["page_count"],
                content_type=row["content_type"],
                sha256_hash=row["sha256_hash"],
                uploaded_at=row["uploaded_at"],
            )
            result = DocumentExtractionResult(
                metadata=metadata,
                pages=pages,
                total_chars=row["total_chars"],
                is_text_based=bool(row["is_text_based"]),
                extraction_warnings=[],
            )
            _FALLBACK_DOCS[document_id] = result
            return result
        except (sqlite3.Error, OSError) as exc:
            logger.warning(f"Failed to query SQLite document record: {exc}")
            return _FALLBACK_DOCS.get(document_id)

    def list_documents(
        self, role: Optional[DocumentRole] = None
    ) -> List[DocumentMetadata]:
        """List uploaded document metadata filtered by optional role."""
        try:
            with sqlite_connection(self.db_path) as conn:
                if role:
                    rows = conn.execute(
                        """
                        SELECT document_id, filename, role, file_size_bytes, page_count,
                               content_type, sha256_hash, uploaded_at
                        FROM uploaded_documents
                        WHERE role = ?
                        ORDER BY uploaded_at DESC
                        """,
                        (role.value,),
                    ).fetchall()
                else:
                    rows = conn.execute(
                        """
                        SELECT document_id, filename, role, file_size_bytes, page_count,
                               content_type, sha256_hash, uploaded_at
                        FROM uploaded_documents
                        ORDER BY uploaded_at DESC
                        """
                    ).fetchall()

            return [
                DocumentMetadata(
                    document_id=r["document_id"],
                    filename=r["filename"],
                    role=DocumentRole(r["role"]),
                    file_size_bytes=r["file_size_bytes"],
                    page_count=r["page_count"],
                    content_type=r["content_type"],
                    sha256_hash=r["sha256_hash"],
                    uploaded_at=r["uploaded_at"],
                )
                for r in rows
            ]
        except (sqlite3.Error, OSError) as exc:
            logger.warning(f"Reading document metadata from memory buffer: {exc}")
            docs = [res.metadata for res in _FALLBACK_DOCS.values()]
            if role:
                docs = [d for d in docs if d.role == role]
            return sorted(docs, key=lambda d: d.uploaded_at, reverse=True)
