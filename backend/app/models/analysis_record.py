"""Repository for persisting and retrieving ComplianceAnalysisResult records."""

from __future__ import annotations

import json
import sqlite3
from typing import Dict, List, Optional

from app.core.logging import get_logger
from app.db.sqlite import init_sqlite_db, sqlite_connection
from app.schemas.compliance import ComplianceAnalysisResult

logger = get_logger(__name__)

_FALLBACK_ANALYSES: Dict[str, ComplianceAnalysisResult] = {}


class AnalysisRepository:
    """Manages storage and query of compliance analysis intelligence runs."""

    def __init__(self, db_path: Optional[str] = None) -> None:
        self.db_path = db_path
        init_sqlite_db(self.db_path)

    def save_analysis(
        self, result: ComplianceAnalysisResult
    ) -> ComplianceAnalysisResult:
        """Persist compliance analysis result into SQLite with in-memory fallback."""
        tender_doc_id = result.tender_document.document_id
        bidder_doc_ids = [b.document_id for b in result.bidder_documents]
        result_json = result.model_dump_json()

        try:
            with sqlite_connection(self.db_path) as conn:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO compliance_analyses (
                        analysis_id, tender_document_id, bidder_document_ids_json,
                        result_json, created_at
                    ) VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        result.analysis_id,
                        tender_doc_id,
                        json.dumps(bidder_doc_ids),
                        result_json,
                        result.created_at.isoformat(),
                    ),
                )
        except (sqlite3.Error, OSError) as exc:
            logger.warning(f"Analysis saved to fallback memory buffer: {exc}")

        _FALLBACK_ANALYSES[result.analysis_id] = result
        return result

    def get_analysis(self, analysis_id: str) -> Optional[ComplianceAnalysisResult]:
        """Fetch a compliance analysis by stable analysis_id."""
        if analysis_id in _FALLBACK_ANALYSES:
            return _FALLBACK_ANALYSES[analysis_id]

        try:
            with sqlite_connection(self.db_path) as conn:
                row = conn.execute(
                    """
                    SELECT result_json
                    FROM compliance_analyses
                    WHERE analysis_id = ?
                    """,
                    (analysis_id,),
                ).fetchone()

            if not row:
                return None

            result = ComplianceAnalysisResult.model_validate_json(row["result_json"])
            _FALLBACK_ANALYSES[analysis_id] = result
            return result
        except (sqlite3.Error, OSError) as exc:
            logger.warning(f"Query analysis failed; falling back to memory: {exc}")
            return _FALLBACK_ANALYSES.get(analysis_id)

    def list_analyses(self, limit: int = 50) -> List[ComplianceAnalysisResult]:
        """List recent analyses ordered newest first."""
        try:
            with sqlite_connection(self.db_path) as conn:
                rows = conn.execute(
                    """
                    SELECT result_json
                    FROM compliance_analyses
                    ORDER BY created_at DESC
                    LIMIT ?
                    """,
                    (limit,),
                ).fetchall()

            return [
                ComplianceAnalysisResult.model_validate_json(r["result_json"])
                for r in rows
            ]
        except (sqlite3.Error, OSError) as exc:
            logger.warning(f"Listing analyses from memory buffer: {exc}")
            return list(_FALLBACK_ANALYSES.values())[:limit]
