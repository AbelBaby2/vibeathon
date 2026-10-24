"""Post-award work-permit readiness simulation and checklist evaluation service."""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from typing import List

from app.schemas.compliance import (
    ComplianceStatus,
    RequirementAssessment,
    RequirementCategory,
)
from app.schemas.permit import (
    AwardSimulationRequest,
    HumanReviewStatus,
    PermitCategory,
    PermitChecklistItem,
    PermitItemStatus,
    PermitReadinessResult,
    PermitReadinessSummary,
)


class PermitReadinessService:
    """Simulates contract award and carries safety/operational items into a permit checklist."""

    def simulate_award_and_build_checklist(
        self, request: AwardSimulationRequest
    ) -> PermitReadinessResult:
        """Generate a PermitReadinessResult from compliance assessments."""
        reference_date_str = request.planned_start_date or datetime.now(
            timezone.utc
        ).strftime("%Y-%m-%d")

        assessment_by_id = {a.requirement_id: a for a in request.assessments}
        checklist_items: List[PermitChecklistItem] = []
        top_unresolved: List[str] = []
        item_counter = 1

        # Carry forward SAFETY, CERTIFICATION, or requirements flagged requires_permit_carryover
        relevant_requirements = [
            r
            for r in request.tender_requirements
            if r.requires_permit_carryover
            or r.category in (RequirementCategory.SAFETY, RequirementCategory.CERTIFICATION)
        ]

        # If none explicitly matched, include a baseline HSE mobilization item
        if not relevant_requirements and request.tender_requirements:
            relevant_requirements = [request.tender_requirements[0]]

        for req in relevant_requirements:
            assessment = assessment_by_id.get(req.requirement_id)
            evidence_list = assessment.matched_evidence if assessment else []

            expiry_date = next(
                (ev.valid_until for ev in evidence_list if ev.valid_until), None
            )
            is_expired = self._check_is_expired(expiry_date, reference_date_str)

            # Determine permit category
            desc_lower = req.description.lower()
            if "worker" in desc_lower or "training" in desc_lower or "qualification" in desc_lower:
                permit_cat = PermitCategory.WORKER_QUALIFICATION
            elif "equipment" in desc_lower or "lifting" in desc_lower or req.category == RequirementCategory.CERTIFICATION:
                permit_cat = PermitCategory.EQUIPMENT_CERTIFICATION
            elif "hazard" in desc_lower or "confined space" in desc_lower:
                permit_cat = PermitCategory.HAZARD_CONTROL
            elif "site" in desc_lower or "approval" in desc_lower:
                permit_cat = PermitCategory.SITE_APPROVAL
            elif "insurance" in desc_lower or "liability" in desc_lower:
                permit_cat = PermitCategory.INSURANCE_LIABILITY
            else:
                permit_cat = PermitCategory.HSE_POLICY

            unresolved: List[str] = []
            remediation: List[str] = []

            if is_expired:
                status = PermitItemStatus.EXPIRED
                review_state = HumanReviewStatus.REQUIRES_VERIFICATION
                msg = (
                    f"Supporting qualification for '{req.title}' expired on {expiry_date} "
                    f"(before mobilization date {reference_date_str})."
                )
                unresolved.append(msg)
                top_unresolved.append(msg)
                remediation.append("Submit renewed certificate or valid active endorsement prior to site mobilization.")
            elif not assessment or assessment.status == ComplianceStatus.MISSING:
                status = PermitItemStatus.PENDING_EVIDENCE
                review_state = HumanReviewStatus.INCOMPLETE
                msg = f"Missing mandatory safety/permit evidence for '{req.title}'."
                unresolved.append(msg)
                top_unresolved.append(msg)
                remediation.append(
                    "Provide signed safety documentation and obtain Site HSE Officer approval."
                )
            elif assessment.status == ComplianceStatus.CONFLICTING:
                status = PermitItemStatus.CONFLICTING
                review_state = HumanReviewStatus.REQUIRES_VERIFICATION
                msg = f"Conflicting safety documentation noted for '{req.title}'."
                unresolved.append(msg)
                top_unresolved.append(msg)
                remediation.append("Resolve discrepancy in safety records before site entry.")
            elif assessment.status == ComplianceStatus.NEEDS_REVIEW:
                status = PermitItemStatus.NEEDS_REVIEW
                review_state = HumanReviewStatus.REQUIRES_VERIFICATION
                msg = f"Manual HSE officer verification required for '{req.title}'."
                unresolved.append(msg)
                remediation.append("Conduct pre-mobilization safety audit and verify original records.")
            else:
                status = PermitItemStatus.VERIFIED
                review_state = HumanReviewStatus.READY_FOR_REVIEW
                remediation.append("Maintain valid documentation and certified personnel on site during execution.")

            evidence_ids = [ev.evidence_id for ev in evidence_list]

            checklist_items.append(
                PermitChecklistItem(
                    item_id=f"PRM-{item_counter:03d}",
                    source_requirement_id=req.requirement_id,
                    category=permit_cat,
                    title=req.title,
                    description=req.description,
                    status=status,
                    required_document_type=(
                        "Accredited Certification"
                        if req.category == RequirementCategory.CERTIFICATION
                        else "HSE Plan / Work-Permit Endorsement"
                    ),
                    supporting_evidence=evidence_list,
                    approval_authority="Site HSE & Permit Authority",
                    qualification_reference=req.threshold_or_criteria,
                    expiry_date=expiry_date,
                    is_expired=is_expired,
                    unresolved_conditions=unresolved,
                    remediation_steps=remediation,
                    review_status=review_state,
                    attached_evidence_ids=evidence_ids,
                )
            )
            item_counter += 1

        summary = self._build_summary(checklist_items, len(top_unresolved))
        permit_pack_id = f"PCK-{uuid.uuid4().hex[:8].upper()}"

        return PermitReadinessResult(
            permit_pack_id=permit_pack_id,
            analysis_id=request.analysis_id,
            contract_reference=request.contract_reference,
            planned_start_date=reference_date_str,
            site_location=request.site_location,
            checklist_items=checklist_items,
            summary=summary,
            unresolved_conditions=top_unresolved,
        )

    @staticmethod
    def _check_is_expired(expiry_str: str | None, reference_str: str) -> bool:
        if not expiry_str:
            return False
        try:
            exp_date = date.fromisoformat(expiry_str)
            ref_date = date.fromisoformat(reference_str)
            return exp_date < ref_date
        except ValueError:
            return False

    @staticmethod
    def _build_summary(
        items: List[PermitChecklistItem], blocking_count: int
    ) -> PermitReadinessSummary:
        total = len(items)
        verified = sum(1 for i in items if i.status == PermitItemStatus.VERIFIED)
        pending = sum(1 for i in items if i.status == PermitItemStatus.PENDING_EVIDENCE)
        expired = sum(1 for i in items if i.status == PermitItemStatus.EXPIRED)
        conflicting = sum(1 for i in items if i.status == PermitItemStatus.CONFLICTING)
        needs_review = sum(1 for i in items if i.status == PermitItemStatus.NEEDS_REVIEW)
        pct = round((verified / total) * 100.0, 1) if total > 0 else 0.0

        return PermitReadinessSummary(
            total_items=total,
            verified_count=verified,
            pending_count=pending,
            expired_count=expired,
            conflicting_count=conflicting,
            needs_review_count=needs_review,
            readiness_percentage=pct,
            blocking_conditions_count=blocking_count,
        )
