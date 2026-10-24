"""Foundational tender requirement extraction service."""

from __future__ import annotations

import re
from typing import List, Optional, Tuple

from app.schemas.compliance import (
    RequirementCategory,
    RequirementPriority,
    SourceReference,
    TenderRequirement,
)
from app.schemas.document import DocumentExtractionResult
from app.services.llm_provider import LLMProviderService

# Category keyword rules for baseline deterministic extraction foundation
_CATEGORY_PATTERNS: List[Tuple[RequirementCategory, str, List[str], bool]] = [
    (
        RequirementCategory.ELIGIBILITY,
        "Bidder Legal & Registration Eligibility",
        ["eligible", "eligibility", "registered", "incorporation", "license", "joint venture"],
        False,
    ),
    (
        RequirementCategory.EXPERIENCE,
        "Similar Project Track Record & Experience",
        ["experience", "similar project", "track record", "completed projects", "years of experience"],
        False,
    ),
    (
        RequirementCategory.FINANCIAL,
        "Minimum Annual Turnover & Financial Capacity",
        ["turnover", "financial", "net worth", "audited", "liquidity", "solvency"],
        False,
    ),
    (
        RequirementCategory.CERTIFICATION,
        "Quality & Management System Certifications",
        ["iso 9001", "iso 14001", "iso 45001", "certification", "accredited", "certificate"],
        True,
    ),
    (
        RequirementCategory.DEADLINE,
        "Submission & Mobilization Deadlines",
        ["deadline", "submission date", "closing date", "completion period", "schedule"],
        False,
    ),
    (
        RequirementCategory.SAFETY,
        "HSE Plan, Work-Permit & Site Safety Compliance",
        ["safety", "hse", "work permit", "ppe", "hazard", "incident", "confined space", "lifting"],
        True,
    ),
]


class RequirementExtractorService:
    """Extracts structured TenderRequirement items with page-level source references."""

    def __init__(self, llm_provider: Optional[LLMProviderService] = None) -> None:
        self.llm_provider = llm_provider or LLMProviderService()

    def extract_requirements(
        self, tender_extraction: DocumentExtractionResult
    ) -> List[TenderRequirement]:
        """Extract baseline requirements from page-level tender text with stable IDs."""
        requirements: List[TenderRequirement] = []
        filename = tender_extraction.metadata.filename
        req_counter = 1

        for page in tender_extraction.pages:
            if not page.text:
                continue

            sentences = [
                s.strip()
                for s in re.split(r"(?<=[.!?;\n])\s+", page.text)
                if len(s.strip()) >= 15
            ]

            for category, default_title, keywords, permit_carryover in _CATEGORY_PATTERNS:
                for sentence in sentences:
                    lower_sentence = sentence.lower()
                    if any(kw in lower_sentence for kw in keywords):
                        req_id = f"REQ-{req_counter:03d}"
                        req_counter += 1
                        excerpt = sentence[:240]
                        requirements.append(
                            TenderRequirement(
                                requirement_id=req_id,
                                category=category,
                                title=default_title,
                                description=sentence[:400],
                                priority=RequirementPriority.MANDATORY,
                                source=SourceReference(
                                    filename=filename,
                                    page_number=page.page_number,
                                    excerpt=excerpt,
                                ),
                                requires_permit_carryover=permit_carryover
                                or (category == RequirementCategory.SAFETY),
                            )
                        )
                        break

        # Ensure at least one baseline requirement is returned for valid text-based tenders
        if not requirements and tender_extraction.pages:
            first_page = tender_extraction.pages[0]
            excerpt = (first_page.text or "General tender compliance criteria.")[:200]
            requirements.append(
                TenderRequirement(
                    requirement_id="REQ-001",
                    category=RequirementCategory.ELIGIBILITY,
                    title="General Tender Eligibility & Submission Compliance",
                    description="Verify general bidder eligibility against tender terms.",
                    priority=RequirementPriority.MANDATORY,
                    source=SourceReference(
                        filename=filename,
                        page_number=first_page.page_number,
                        excerpt=excerpt,
                    ),
                    requires_permit_carryover=False,
                )
            )

        return requirements
