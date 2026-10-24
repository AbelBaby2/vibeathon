"""Compliance evaluation rules and summary metrics calculation service."""

from __future__ import annotations

from typing import Dict, List

from app.schemas.compliance import (
    BidderEvidence,
    ComplianceStatus,
    ComplianceSummaryMetrics,
    RequirementAssessment,
    RequirementPriority,
    TenderRequirement,
)


class ComplianceRulesService:
    """Evaluates matched bidder evidence against tender requirements and computes summary metrics."""

    def evaluate_requirements(
        self,
        requirements: List[TenderRequirement],
        matched_evidence_map: Dict[str, List[BidderEvidence]],
    ) -> List[RequirementAssessment]:
        """Classify each requirement as Evidence Found, Missing, Conflicting, or Needs Review."""
        assessments: List[RequirementAssessment] = []

        for req in requirements:
            evidence_list = matched_evidence_map.get(req.requirement_id, [])

            if not evidence_list:
                status = ComplianceStatus.MISSING
                rationale = (
                    f"No supporting evidence for '{req.title}' was found across uploaded bidder PDFs."
                )
                discrepancies = ["Required supporting documentation is missing."]
                recommended_action = (
                    f"Upload or attach verifiable evidence addressing {req.category.value} criteria."
                )
            else:
                has_conflict = any(
                    "expired" in ev.excerpt.lower() or "non-compliant" in ev.excerpt.lower()
                    for ev in evidence_list
                )
                avg_confidence = sum(ev.confidence for ev in evidence_list) / len(evidence_list)

                if has_conflict:
                    status = ComplianceStatus.CONFLICTING
                    rationale = (
                        "Evidence was located in bidder documents but contains conflicting or expired indicators."
                    )
                    discrepancies = [
                        "Potential conflict or expired qualification detected in bidder excerpt."
                    ]
                    recommended_action = (
                        "Verify validity dates and resolve conflicting statements prior to submission."
                    )
                elif avg_confidence < 0.65:
                    status = ComplianceStatus.NEEDS_REVIEW
                    rationale = (
                        "Partial or low-confidence reference found; manual procurement review is required."
                    )
                    discrepancies = ["Ambiguous match confidence requires human verification."]
                    recommended_action = "Confirm exact threshold compliance with bid manager."
                else:
                    status = ComplianceStatus.EVIDENCE_FOUND
                    rationale = (
                        f"Matched {len(evidence_list)} supporting evidence excerpt(s) in bidder documents."
                    )
                    discrepancies = []
                    recommended_action = "Retain cited source reference for final bid submission pack."

            assessments.append(
                RequirementAssessment(
                    requirement_id=req.requirement_id,
                    requirement=req,
                    status=status,
                    matched_evidence=evidence_list,
                    rationale=rationale,
                    discrepancies=discrepancies,
                    recommended_action=recommended_action,
                )
            )

        return assessments

    def build_summary(
        self,
        requirements: List[TenderRequirement],
        assessments: List[RequirementAssessment],
    ) -> ComplianceSummaryMetrics:
        """Compute aggregated compliance counts and readiness score."""
        total = len(requirements)
        evidence_found = sum(
            1 for a in assessments if a.status == ComplianceStatus.EVIDENCE_FOUND
        )
        missing = sum(1 for a in assessments if a.status == ComplianceStatus.MISSING)
        conflicting = sum(
            1 for a in assessments if a.status == ComplianceStatus.CONFLICTING
        )
        needs_review = sum(
            1 for a in assessments if a.status == ComplianceStatus.NEEDS_REVIEW
        )
        mandatory_gaps = sum(
            1
            for a in assessments
            if a.requirement.priority == RequirementPriority.MANDATORY
            and a.status in (ComplianceStatus.MISSING, ComplianceStatus.CONFLICTING)
        )
        safety_count = sum(
            1
            for r in requirements
            if r.requires_permit_carryover or r.category.value == "SAFETY"
        )

        by_category: Dict[str, int] = {}
        for r in requirements:
            cat_key = r.category.value
            by_category[cat_key] = by_category.get(cat_key, 0) + 1

        readiness_score = round((evidence_found / total) * 100.0, 1) if total > 0 else 0.0

        return ComplianceSummaryMetrics(
            total_requirements=total,
            evidence_found_count=evidence_found,
            missing_count=missing,
            conflicting_count=conflicting,
            needs_review_count=needs_review,
            mandatory_gap_count=mandatory_gaps,
            safety_requirements_count=safety_count,
            overall_readiness_score=readiness_score,
            by_category=by_category,
        )
