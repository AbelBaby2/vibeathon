"""Compliance evaluation rules and summary metrics calculation service."""

from __future__ import annotations

import re
from datetime import date, datetime, timezone
from typing import Dict, List, Optional, Tuple

from app.schemas.compliance import (
    BidderEvidence,
    ComplianceStatus,
    ComplianceSummaryMetrics,
    RequirementAssessment,
    RequirementCategory,
    RequirementPriority,
    TenderRequirement,
)

_DATE_REGEX = re.compile(r"\b(20\d{2}-\d{2}-\d{2})\b")
_CURRENCY_MAP = {
    "$": "USD",
    "USD": "USD",
    "€": "EUR",
    "EUR": "EUR",
    "£": "GBP",
    "GBP": "GBP",
    "INR": "INR",
    "AUD": "AUD",
    "CAD": "CAD",
}


def _parse_money_val(raw_text: str) -> Tuple[Optional[float], Optional[str]]:
    """Parse monetary amount and currency code from text snippet."""
    if not raw_text:
        return None, None

    currency: Optional[str] = None
    for sym, code in _CURRENCY_MAP.items():
        if sym.lower() in raw_text.lower():
            currency = code
            break

    # Look for number with M/million/k/billion
    match = re.search(
        r"([\d,.]+)\s*(M|million|k|thousand|B|billion)?", raw_text, re.IGNORECASE
    )
    if not match:
        return None, currency

    num_str = match.group(1).replace(",", "")
    unit = (match.group(2) or "").lower()

    try:
        val = float(num_str)
        if unit in ("m", "million"):
            val *= 1_000_000
        elif unit in ("k", "thousand"):
            val *= 1_000
        elif unit in ("b", "billion"):
            val *= 1_000_000_000
        return val, currency
    except ValueError:
        return None, currency


class ComplianceRulesService:
    """Evaluates matched bidder evidence against tender requirements with deterministic checks."""

    def evaluate_requirements(
        self,
        requirements: List[TenderRequirement],
        matched_evidence_map: Dict[str, List[BidderEvidence]],
        reference_date_str: Optional[str] = None,
    ) -> List[RequirementAssessment]:
        """Classify each requirement as Evidence Found, Missing, Conflicting, or Needs Review."""
        assessments: List[RequirementAssessment] = []
        today_str = reference_date_str or datetime.now(timezone.utc).strftime("%Y-%m-%d")

        for req in requirements:
            evidence_list = matched_evidence_map.get(req.requirement_id, [])

            if not evidence_list:
                # Missing evidence indicates absence of documentation, not proof of lack of qualification
                status = ComplianceStatus.MISSING
                rationale = (
                    f"Evidence was not located in the uploaded material for '{req.title}'. "
                    "This indicates absence of documentation in the submission, not proof of non-qualification."
                )
                discrepancies = ["Required supporting documentation is absent from uploaded submission."]
                recommended_action = (
                    f"Upload or attach verifiable evidence addressing {req.category.value} criteria."
                )
            else:
                # Deterministic check 1: Detect explicit contradiction / disagreement between multiple documents
                conflicts: List[str] = []
                needs_review_reasons: List[str] = []

                # Check if multiple evidence excerpts give divergent values
                extracted_values = [ev.extracted_value for ev in evidence_list if ev.extracted_value]
                if len(set(extracted_values)) > 1 and req.category in (
                    RequirementCategory.FINANCIAL,
                    RequirementCategory.CERTIFICATION,
                ):
                    conflicts.append(
                        f"Divergent values reported across documents: {', '.join(set(extracted_values))}. Both references preserved."
                    )

                # Check for explicit expired markers or dates
                for ev in evidence_list:
                    ev_lower = ev.excerpt.lower()
                    if "expired" in ev_lower or "non-compliant" in ev_lower:
                        conflicts.append(
                            f"Discrepancy in '{ev.filename}' (page {ev.page_number}): Document notes expired or non-compliant status."
                        )

                    # Deterministic check 2: Expiry date comparison
                    if ev.valid_until:
                        try:
                            exp_dt = date.fromisoformat(ev.valid_until)
                            ref_dt = date.fromisoformat(today_str)
                            if exp_dt < ref_dt:
                                conflicts.append(
                                    f"Certificate in '{ev.filename}' (page {ev.page_number}) expired on {ev.valid_until} (before reference date {today_str})."
                                )
                        except ValueError:
                            pass

                # Deterministic check 3: Financial threshold & currency check
                if req.category == RequirementCategory.FINANCIAL and req.threshold_or_criteria:
                    tender_val, tender_curr = _parse_money_val(req.threshold_or_criteria)
                    # Check bidder financial evidence
                    for ev in evidence_list:
                        ev_val, ev_curr = _parse_money_val(ev.extracted_value or ev.excerpt)
                        if tender_val is not None and ev_val is not None:
                            # Rule: Never compare monetary values without checking units and currency
                            if tender_curr and ev_curr and tender_curr != ev_curr:
                                needs_review_reasons.append(
                                    f"Currency mismatch: tender requires {tender_curr} but bidder document specifies {ev_curr}. Currency conversion requires review."
                                )
                            elif tender_curr and not ev_curr:
                                needs_review_reasons.append(
                                    f"Bidder document specifies value without explicit currency ({ev.extracted_value or ev.excerpt[:40]}); currency interpretation is ambiguous."
                                )
                            elif (not tender_curr) and ev_curr:
                                needs_review_reasons.append(
                                    "Tender threshold currency is ambiguous; procurement review required."
                                )
                            else:
                                # Currencies match or are comparable
                                if ev_val < tender_val:
                                    conflicts.append(
                                        f"Extracted financial value ({ev_val:,.0f} {tender_curr or ''}) does not meet the required mandatory threshold ({tender_val:,.0f} {tender_curr or ''})."
                                    )

                # Determine overall status
                avg_confidence = sum(ev.confidence for ev in evidence_list) / len(evidence_list)

                if conflicts:
                    status = ComplianceStatus.CONFLICTING
                    rationale = (
                        f"Located {len(evidence_list)} evidence item(s), but detected conflicts, expired credentials, or criteria shortfalls."
                    )
                    discrepancies = conflicts
                    recommended_action = (
                        "Verify validity dates and resolve conflicting statements with the bidder prior to adjudication."
                    )
                elif needs_review_reasons or avg_confidence < 0.65 or req.needs_review:
                    status = ComplianceStatus.NEEDS_REVIEW
                    rationale = (
                        "Extracted evidence requires human procurement or HSE verification (e.g., currency conversion, ambiguous criteria, or partial match)."
                    )
                    discrepancies = needs_review_reasons or ["Ambiguous match criteria requires human verification."]
                    recommended_action = "Conduct manual verification of extracted evidence against formal tender specifications."
                else:
                    status = ComplianceStatus.EVIDENCE_FOUND
                    rationale = (
                        f"Matched {len(evidence_list)} supporting evidence excerpt(s) in bidder documentation meeting criteria."
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
