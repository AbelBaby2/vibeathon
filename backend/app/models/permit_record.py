"""Repository for persisting and updating PermitReadinessResult and checklist items."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from typing import Dict, Optional, Tuple

from app.core.logging import get_logger
from app.db.sqlite import init_sqlite_db, sqlite_connection
from app.schemas.permit import (
    HumanReviewStatus,
    PermitChecklistItem,
    PermitItemStatus,
    PermitItemUpdateRequest,
    PermitReadinessResult,
    PermitReadinessSummary,
)

logger = get_logger(__name__)

_FALLBACK_CHECKLISTS: Dict[str, PermitReadinessResult] = {}


class PermitRepository:
    """Manages storage and status updates of post-award permit checklists."""

    def __init__(self, db_path: Optional[str] = None) -> None:
        self.db_path = db_path
        init_sqlite_db(self.db_path)

    def save_checklist(
        self, result: PermitReadinessResult
    ) -> PermitReadinessResult:
        """Persist a complete work-permit readiness package to SQLite."""
        now = datetime.now(timezone.utc).isoformat()
        items_json = json.dumps([i.model_dump(mode="json") for i in result.checklist_items])
        summary_json = result.summary.model_dump_json()
        unresolved_json = json.dumps(result.unresolved_conditions)

        try:
            with sqlite_connection(self.db_path) as conn:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO permit_checklists (
                        permit_pack_id, analysis_id, contract_reference,
                        planned_start_date, site_location, checklist_items_json,
                        summary_json, unresolved_conditions_json, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        result.permit_pack_id,
                        result.analysis_id,
                        result.contract_reference,
                        result.planned_start_date,
                        result.site_location,
                        items_json,
                        summary_json,
                        unresolved_json,
                        result.simulated_award_date.isoformat(),
                        now,
                    ),
                )
        except (sqlite3.Error, OSError) as exc:
            logger.warning(f"Permit checklist stored in fallback buffer: {exc}")

        _FALLBACK_CHECKLISTS[result.analysis_id] = result
        return result

    def get_checklist_by_analysis(
        self, analysis_id: str
    ) -> Optional[PermitReadinessResult]:
        """Fetch permit readiness package for a given analysis_id."""
        if analysis_id in _FALLBACK_CHECKLISTS:
            return _FALLBACK_CHECKLISTS[analysis_id]

        try:
            with sqlite_connection(self.db_path) as conn:
                row = conn.execute(
                    """
                    SELECT permit_pack_id, analysis_id, contract_reference,
                           planned_start_date, site_location, checklist_items_json,
                           summary_json, unresolved_conditions_json, created_at, updated_at
                    FROM permit_checklists
                    WHERE analysis_id = ?
                    """,
                    (analysis_id,),
                ).fetchone()

            if not row:
                return None

            items = [
                PermitChecklistItem(**i)
                for i in json.loads(row["checklist_items_json"] or "[]")
            ]
            summary = PermitReadinessSummary.model_validate_json(row["summary_json"])
            unresolved = json.loads(row["unresolved_conditions_json"] or "[]")

            result = PermitReadinessResult(
                permit_pack_id=row["permit_pack_id"],
                analysis_id=row["analysis_id"],
                contract_reference=row["contract_reference"],
                simulated_award_date=datetime.fromisoformat(row["created_at"]),
                planned_start_date=row["planned_start_date"],
                site_location=row["site_location"],
                checklist_items=items,
                summary=summary,
                unresolved_conditions=unresolved,
            )
            _FALLBACK_CHECKLISTS[analysis_id] = result
            return result
        except (sqlite3.Error, OSError) as exc:
            logger.warning(f"Failed to query SQLite permit checklist: {exc}")
            return _FALLBACK_CHECKLISTS.get(analysis_id)

    def find_item_by_id(
        self, item_id: str
    ) -> Optional[Tuple[PermitReadinessResult, PermitChecklistItem]]:
        """Search across stored permit packages to locate a specific checklist item."""
        # 1. Search in-memory
        for result in _FALLBACK_CHECKLISTS.values():
            for item in result.checklist_items:
                if item.item_id == item_id:
                    return result, item

        # 2. Query all database checklists if not found in memory
        try:
            with sqlite_connection(self.db_path) as conn:
                rows = conn.execute(
                    "SELECT analysis_id FROM permit_checklists"
                ).fetchall()

            for r in rows:
                chk = self.get_checklist_by_analysis(r["analysis_id"])
                if chk:
                    for item in chk.checklist_items:
                        if item.item_id == item_id:
                            return chk, item
        except (sqlite3.Error, OSError) as exc:
            logger.warning(f"Error querying items: {exc}")

        return None

    def update_checklist_item(
        self, item_id: str, update: PermitItemUpdateRequest
    ) -> Optional[Tuple[PermitReadinessResult, PermitChecklistItem]]:
        """Update review status, reviewer info, or attached evidence for an item."""
        found = self.find_item_by_id(item_id)
        if not found:
            return None

        chk, item = found
        now = datetime.now(timezone.utc)

        # Apply updates
        if update.review_status is not None:
            item.review_status = update.review_status
            if update.review_status == HumanReviewStatus.APPROVED_BY_REVIEWER:
                item.status = PermitItemStatus.VERIFIED

        if update.reviewer_name is not None:
            item.reviewer_name = update.reviewer_name

        if update.reviewer_role is not None:
            item.reviewer_role = update.reviewer_role

        if update.reviewer_notes is not None:
            item.reviewer_notes = update.reviewer_notes

        if update.attached_evidence_ids is not None:
            item.attached_evidence_ids = update.attached_evidence_ids

        item.reviewed_at = now

        # Recalculate summary metrics
        total = len(chk.checklist_items)
        verified = sum(1 for i in chk.checklist_items if i.status == PermitItemStatus.VERIFIED)
        pending = sum(1 for i in chk.checklist_items if i.status == PermitItemStatus.PENDING_EVIDENCE)
        expired = sum(1 for i in chk.checklist_items if i.status == PermitItemStatus.EXPIRED)
        conflicting = sum(1 for i in chk.checklist_items if i.status == PermitItemStatus.CONFLICTING)
        needs_review = sum(1 for i in chk.checklist_items if i.status == PermitItemStatus.NEEDS_REVIEW)
        pct = round((verified / total) * 100.0, 1) if total > 0 else 0.0

        chk.summary = PermitReadinessSummary(
            total_items=total,
            verified_count=verified,
            pending_count=pending,
            expired_count=expired,
            conflicting_count=conflicting,
            needs_review_count=needs_review,
            readiness_percentage=pct,
            blocking_conditions_count=len(chk.unresolved_conditions),
        )

        self.save_checklist(chk)
        return chk, item
