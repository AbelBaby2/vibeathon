"""Tests for deterministic Python compliance checks (financial, currency, dates, certificate expiry)."""

from __future__ import annotations

from app.schemas.compliance import (
    BidderEvidence,
    ComplianceStatus,
    RequirementCategory,
    RequirementPriority,
    SourceReference,
    TenderRequirement,
)
from app.services.compliance_rules import ComplianceRulesService, _parse_money_val


def test_money_parser_units_and_currencies() -> None:
    """Validate numerical parsing of currency strings with multipliers."""
    val1, curr1 = _parse_money_val("USD 5M")
    assert val1 == 5_000_000.0
    assert curr1 == "USD"

    val2, curr2 = _parse_money_val("€2.5 million")
    assert val2 == 2_500_000.0
    assert curr2 == "EUR"

    val3, curr3 = _parse_money_val("$500k")
    assert val3 == 500_000.0
    assert curr3 == "USD"


def test_financial_threshold_compliant() -> None:
    """Bidder turnover satisfying required threshold results in Evidence Found."""
    rules = ComplianceRulesService()
    req = TenderRequirement(
        requirement_id="REQ-FIN-001",
        category=RequirementCategory.FINANCIAL,
        title="Annual Turnover",
        description="Minimum turnover USD 5M.",
        priority=RequirementPriority.MANDATORY,
        source=SourceReference(filename="tender.pdf", page_number=1, excerpt="USD 5M turnover"),
        threshold_or_criteria="USD 5M",
    )
    evidence = BidderEvidence(
        evidence_id="EVD-001",
        requirement_id="REQ-FIN-001",
        source_document_id="DOC-B-001",
        filename="financials.pdf",
        page_number=2,
        excerpt="Annual audited turnover reached USD 8.5M in 2025.",
        extracted_value="USD 8.5M",
        confidence=0.9,
    )

    assessments = rules.evaluate_requirements([req], {req.requirement_id: [evidence]})
    assert assessments[0].status == ComplianceStatus.EVIDENCE_FOUND
    assert len(assessments[0].discrepancies) == 0


def test_financial_currency_mismatch_returns_needs_review() -> None:
    """Never compare monetary values with differing currencies; return needs_review."""
    rules = ComplianceRulesService()
    req = TenderRequirement(
        requirement_id="REQ-FIN-002",
        category=RequirementCategory.FINANCIAL,
        title="Annual Turnover",
        description="Minimum turnover USD 5M.",
        priority=RequirementPriority.MANDATORY,
        source=SourceReference(filename="tender.pdf", page_number=1, excerpt="USD 5M turnover"),
        threshold_or_criteria="USD 5M",
    )
    # Bidder specifies turnover in EUR without confirmed exchange rate
    evidence = BidderEvidence(
        evidence_id="EVD-002",
        requirement_id="REQ-FIN-002",
        source_document_id="DOC-B-002",
        filename="euro_financials.pdf",
        page_number=1,
        excerpt="Turnover is EUR 4.8M.",
        extracted_value="EUR 4.8M",
        confidence=0.85,
    )

    assessments = rules.evaluate_requirements([req], {req.requirement_id: [evidence]})
    assert assessments[0].status == ComplianceStatus.NEEDS_REVIEW
    assert any("currency mismatch" in d.lower() for d in assessments[0].discrepancies)


def test_certificate_expiry_check_against_reference_date() -> None:
    """Certificate valid_until date prior to reference date flags conflict."""
    rules = ComplianceRulesService()
    req = TenderRequirement(
        requirement_id="REQ-CERT-001",
        category=RequirementCategory.CERTIFICATION,
        title="ISO 45001 Certification",
        description="Bidder must maintain valid ISO 45001.",
        priority=RequirementPriority.MANDATORY,
        source=SourceReference(filename="tender.pdf", page_number=1, excerpt="Valid ISO 45001"),
        threshold_or_criteria="ISO 45001",
    )
    # Expired certificate
    evidence = BidderEvidence(
        evidence_id="EVD-003",
        requirement_id="REQ-CERT-001",
        source_document_id="DOC-B-003",
        filename="iso_cert.pdf",
        page_number=1,
        excerpt="ISO 45001 valid until 2024-01-01.",
        valid_until="2024-01-01",
        confidence=0.9,
    )

    assessments = rules.evaluate_requirements(
        [req],
        {req.requirement_id: [evidence]},
        reference_date_str="2026-10-01",
    )
    assert assessments[0].status == ComplianceStatus.CONFLICTING
    assert any("expired" in d.lower() for d in assessments[0].discrepancies)
