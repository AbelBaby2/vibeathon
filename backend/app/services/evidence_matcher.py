"""Foundational bidder evidence matching service."""

from __future__ import annotations

import re
from typing import Dict, List, Optional

from app.schemas.compliance import (
    BidderEvidence,
    RequirementCategory,
    TenderRequirement,
)
from app.schemas.document import DocumentExtractionResult
from app.services.llm_provider import LLMProviderService

_CATEGORY_EVIDENCE_TERMS: Dict[RequirementCategory, List[str]] = {
    RequirementCategory.ELIGIBILITY: [
        "registered",
        "incorporation",
        "license",
        "registration",
        "eligible",
    ],
    RequirementCategory.EXPERIENCE: [
        "completed",
        "experience",
        "project",
        "client",
        "contract value",
    ],
    RequirementCategory.FINANCIAL: [
        "turnover",
        "audited",
        "balance sheet",
        "revenue",
        "net worth",
    ],
    RequirementCategory.CERTIFICATION: [
        "iso",
        "certified",
        "certificate",
        "accreditation",
    ],
    RequirementCategory.DEADLINE: [
        "schedule",
        "timeline",
        "mobilization",
        "completion",
        "submission",
    ],
    RequirementCategory.SAFETY: [
        "hse",
        "safety",
        "permit",
        "ppe",
        "training",
        "hazard",
    ],
}

_DATE_REGEX = re.compile(r"\b(20\d{2}-\d{2}-\d{2})\b")


class EvidenceMatcherService:
    """Matches extracted tender requirements against page-level text in bidder PDFs."""

    def __init__(self, llm_provider: Optional[LLMProviderService] = None) -> None:
        self.llm_provider = llm_provider or LLMProviderService()

    def match_evidence(
        self,
        requirements: List[TenderRequirement],
        bidder_extractions: List[DocumentExtractionResult],
    ) -> Dict[str, List[BidderEvidence]]:
        """Return a mapping of requirement_id -> list of matched BidderEvidence items."""
        matched_by_req: Dict[str, List[BidderEvidence]] = {
            req.requirement_id: [] for req in requirements
        }
        evidence_counter = 1

        for req in requirements:
            search_terms = _CATEGORY_EVIDENCE_TERMS.get(req.category, [])
            for doc in bidder_extractions:
                for page in doc.pages:
                    if not page.text:
                        continue
                    lower_text = page.text.lower()
                    if any(term in lower_text for term in search_terms):
                        snippet = self._extract_relevant_excerpt(page.text, search_terms)
                        date_match = _DATE_REGEX.search(page.text)
                        valid_until = date_match.group(1) if date_match else None

                        evidence_item = BidderEvidence(
                            evidence_id=f"EVD-{evidence_counter:03d}",
                            requirement_id=req.requirement_id,
                            source_document_id=doc.metadata.document_id,
                            filename=doc.metadata.filename,
                            page_number=page.page_number,
                            excerpt=snippet,
                            valid_until=valid_until,
                            confidence=0.82,
                        )
                        evidence_counter += 1
                        matched_by_req[req.requirement_id].append(evidence_item)

        return matched_by_req

    @staticmethod
    def _extract_relevant_excerpt(text: str, terms: List[str]) -> str:
        sentences = [s.strip() for s in re.split(r"(?<=[.!?;\n])\s+", text) if s.strip()]
        for sentence in sentences:
            lower_s = sentence.lower()
            if any(term in lower_s for term in terms):
                return sentence[:240]
        return text[:240].strip()
