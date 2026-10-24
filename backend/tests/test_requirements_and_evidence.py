"""Tests for requirement extraction, evidence matching, and conflict preservation."""

from __future__ import annotations

from app.schemas.compliance import (
    ComplianceStatus,
    RequirementCategory,
    RequirementPriority,
)
from app.schemas.document import DocumentExtractionResult, DocumentMetadata, DocumentRole, ExtractedPage
from app.services.compliance_rules import ComplianceRulesService
from app.services.evidence_matcher import EvidenceMatcherService, EvidenceMatcherServiceInterface
from app.services.requirement_extractor import RequirementExtractorService


def test_requirement_extraction_detects_categories_priority_and_criteria() -> None:
    """Validate extraction of categories, mandatory vs optional priorities, and criteria."""
    pages = [
        ExtractedPage(
            page_number=1,
            text=(
                "Section 1.1: The bidder must hold valid ISO 45001 certification. "
                "Section 1.2: Minimum annual audited turnover of USD 5M is mandatory. "
                "Section 1.3: Bidder should preferably provide 3 client reference letters."
            ),
            char_count=200,
            word_count=35,
        ),
        ExtractedPage(
            page_number=2,
            text=(
                "Section 2.1: Submission deadline is 2026-11-15. "
                "Section 2.2: Mandatory confined space and site safety permit compliance."
            ),
            char_count=130,
            word_count=20,
        ),
    ]

    extraction = DocumentExtractionResult(
        metadata=DocumentMetadata(
            document_id="DOC-TENDER-001",
            filename="master_tender.pdf",
            role=DocumentRole.TENDER,
            file_size_bytes=10000,
            page_count=2,
        ),
        pages=pages,
        total_chars=330,
        is_text_based=True,
    )

    req_service = RequirementExtractorService()
    requirements = req_service.extract_requirements(extraction)

    assert len(requirements) >= 4
    categories = {r.category for r in requirements}
    assert RequirementCategory.CERTIFICATION in categories
    assert RequirementCategory.FINANCIAL in categories
    assert RequirementCategory.SAFETY in categories
    assert RequirementCategory.DEADLINE in categories

    # Check stable IDs and source references
    for req in requirements:
        assert req.requirement_id.startswith("REQ-")
        assert req.source.filename == "master_tender.pdf"
        assert req.source.page_number in (1, 2)
        assert len(req.source.excerpt) > 0
        assert req.expected_evidence is not None

    # Check criteria extraction
    fin_req = next(r for r in requirements if r.category == RequirementCategory.FINANCIAL)
    assert "USD 5M" in (fin_req.threshold_or_criteria or "")
    assert fin_req.priority == RequirementPriority.MANDATORY


def test_evidence_matcher_satisfies_service_interface() -> None:
    """Ensure EvidenceMatcherService implements replaceable EvidenceMatcherServiceInterface."""
    matcher = EvidenceMatcherService()
    assert isinstance(matcher, EvidenceMatcherServiceInterface)


def test_missing_evidence_does_not_claim_disqualification() -> None:
    """A missing match must state absence of documentation, not proof of lack of qualification."""
    req_service = RequirementExtractorService()
    rules_service = ComplianceRulesService()

    extraction = DocumentExtractionResult(
        metadata=DocumentMetadata(
            document_id="DOC-T-1",
            filename="tender.pdf",
            role=DocumentRole.TENDER,
            file_size_bytes=5000,
            page_count=1,
        ),
        pages=[
            ExtractedPage(
                page_number=1,
                text="Bidder must have offshore marine safety certification.",
                char_count=55,
                word_count=8,
            )
        ],
        total_chars=55,
        is_text_based=True,
    )

    requirements = req_service.extract_requirements(extraction)
    assessments = rules_service.evaluate_requirements(
        requirements=requirements,
        matched_evidence_map={requirements[0].requirement_id: []},
    )

    assessment = assessments[0]
    assert assessment.status == ComplianceStatus.MISSING
    assert "not proof of non-qualification" in assessment.rationale.lower()


def test_conflicting_evidence_preserves_both_references() -> None:
    """If two bidder documents disagree, both references are preserved and flagged."""
    req_service = RequirementExtractorService()
    evidence_matcher = EvidenceMatcherService()
    rules_service = ComplianceRulesService()

    tender = DocumentExtractionResult(
        metadata=DocumentMetadata(
            document_id="DOC-TENDER-001",
            filename="tender.pdf",
            role=DocumentRole.TENDER,
            file_size_bytes=5000,
            page_count=1,
        ),
        pages=[
            ExtractedPage(
                page_number=1,
                text="Clause 1: Minimum annual audited turnover of USD 10M required.",
                char_count=65,
                word_count=10,
            )
        ],
        total_chars=65,
        is_text_based=True,
    )
    reqs = req_service.extract_requirements(tender)

    # Document 1 reports turnover of USD 12M
    doc_1 = DocumentExtractionResult(
        metadata=DocumentMetadata(
            document_id="DOC-BIDDER-001",
            filename="audited_accounts_2025.pdf",
            role=DocumentRole.BIDDER_SUPPORTING,
            file_size_bytes=4000,
            page_count=1,
        ),
        pages=[
            ExtractedPage(
                page_number=3,
                text="Audited annual turnover for year 2025 is USD 12M.",
                char_count=50,
                word_count=8,
            )
        ],
        total_chars=50,
        is_text_based=True,
    )

    # Document 2 reports contradictory turnover of USD 4M
    doc_2 = DocumentExtractionResult(
        metadata=DocumentMetadata(
            document_id="DOC-BIDDER-002",
            filename="provisional_balance_sheet.pdf",
            role=DocumentRole.BIDDER_SUPPORTING,
            file_size_bytes=4000,
            page_count=1,
        ),
        pages=[
            ExtractedPage(
                page_number=1,
                text="Provisional annual turnover is USD 4M.",
                char_count=40,
                word_count=6,
            )
        ],
        total_chars=40,
        is_text_based=True,
    )

    matched = evidence_matcher.match_evidence(reqs, [doc_1, doc_2])
    assessments = rules_service.evaluate_requirements(reqs, matched)

    assessment = assessments[0]
    assert assessment.status == ComplianceStatus.CONFLICTING
    # Both references must be preserved
    filenames = {e.filename for e in assessment.matched_evidence}
    assert "audited_accounts_2025.pdf" in filenames
    assert "provisional_balance_sheet.pdf" in filenames
    assert len(assessment.discrepancies) >= 1
