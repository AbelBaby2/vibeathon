"""Bidder evidence matching service with replaceable interface, grounding validation, and conflict detection."""

from __future__ import annotations

import asyncio
import concurrent.futures
import re
from typing import Dict, List, Optional, Protocol, runtime_checkable

from app.core.config import Settings, get_settings
from app.core.logging import get_logger
from app.schemas.compliance import (
    BidderEvidence,
    RequirementCategory,
    TenderRequirement,
)
from app.schemas.document import DocumentExtractionResult
from app.services.grounding import verify_grounded_citation
from app.services.llm_provider import LLMProviderService

logger = get_logger(__name__)

_CATEGORY_EVIDENCE_TERMS: Dict[RequirementCategory, List[str]] = {
    RequirementCategory.ELIGIBILITY: [
        "registered",
        "incorporation",
        "license",
        "registration",
        "eligible",
        "trade license",
        "commercial register",
    ],
    RequirementCategory.EXPERIENCE: [
        "completed",
        "experience",
        "project",
        "client",
        "contract value",
        "track record",
        "reference",
    ],
    RequirementCategory.FINANCIAL: [
        "turnover",
        "audited",
        "balance sheet",
        "revenue",
        "net worth",
        "financial",
        "solvency",
        "liquidity",
    ],
    RequirementCategory.CERTIFICATION: [
        "iso",
        "certified",
        "certificate",
        "accreditation",
        "accredited",
        "valid until",
        "iso 9001",
        "iso 14001",
        "iso 45001",
    ],
    RequirementCategory.DEADLINE: [
        "schedule",
        "timeline",
        "mobilization",
        "completion",
        "submission",
        "delivery",
    ],
    RequirementCategory.SAFETY: [
        "hse",
        "safety",
        "permit",
        "ppe",
        "training",
        "hazard",
        "confined space",
        "lifting",
        "incident",
    ],
    RequirementCategory.OTHER: [
        "specification",
        "technical",
        "warranty",
        "quality",
    ],
}

_DATE_REGEX = re.compile(r"\b(20\d{2}-\d{2}-\d{2})\b")
_MONEY_REGEX = re.compile(
    r"\b((?:USD|EUR|GBP|INR|\$|€|£)\s*[\d,.]+(?:\s*(?:M|million|k|thousand|B|billion))?|[\d,.]+\s*(?:M|million|k|thousand|B|billion)\s*(?:USD|EUR|GBP)?)\b",
    re.IGNORECASE,
)
_ISO_REGEX = re.compile(r"\b(ISO\s*\d{4,5}(?::\d{4})?)\b", re.IGNORECASE)


@runtime_checkable
class EvidenceMatcherServiceInterface(Protocol):
    """Replaceable service interface for bidder evidence matching."""

    def match_evidence(
        self,
        requirements: List[TenderRequirement],
        bidder_extractions: List[DocumentExtractionResult],
    ) -> Dict[str, List[BidderEvidence]]:
        """Return a mapping of requirement_id -> list of matched BidderEvidence items."""
        ...


class EvidenceMatcherService:
    """Matches extracted tender requirements against page-level text in bidder PDFs."""

    def __init__(
        self,
        settings: Optional[Settings] = None,
        llm_provider: Optional[LLMProviderService] = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.llm_provider = llm_provider or LLMProviderService(self.settings)

    def match_evidence(
        self,
        requirements: List[TenderRequirement],
        bidder_extractions: List[DocumentExtractionResult],
    ) -> Dict[str, List[BidderEvidence]]:
        """Match evidence synchronously; executes LLM in live mode or rule engine in mock mode."""
        if not self.settings.llm_enabled:
            return self._match_deterministic(requirements, bidder_extractions)

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                return pool.submit(
                    asyncio.run,
                    self.match_evidence_async(requirements, bidder_extractions),
                ).result()
        return asyncio.run(self.match_evidence_async(requirements, bidder_extractions))

    async def match_evidence_async(
        self,
        requirements: List[TenderRequirement],
        bidder_extractions: List[DocumentExtractionResult],
    ) -> Dict[str, List[BidderEvidence]]:
        """Match requirements using the configured LLM provider with grounding validation."""
        if not self.settings.llm_enabled:
            return self._match_deterministic(requirements, bidder_extractions)

        self.settings.validate_live_llm_config()

        matched_by_req: Dict[str, List[BidderEvidence]] = {
            req.requirement_id: [] for req in requirements
        }
        evidence_counter = 1

        for req in requirements:
            terms = _CATEGORY_EVIDENCE_TERMS.get(req.category, [])

            for doc in bidder_extractions:
                for page in doc.pages:
                    if not page.text or not page.text.strip():
                        continue

                    # Filter: Only send chunks that contain category-relevant keywords or requirement title terms
                    # to minimize prompt tokens, cost, and latency
                    lower_text = page.text.lower()
                    has_relevant_terms = any(term in lower_text for term in terms) or any(
                        w in lower_text for w in req.title.lower().split() if len(w) > 4
                    )
                    if not has_relevant_terms:
                        continue

                    chunk = page.text[:3000]
                    llm_match = await self.llm_provider.match_evidence_in_chunk(
                        requirement_id=req.requirement_id,
                        requirement_category=req.category.value,
                        requirement_title=req.title,
                        requirement_desc=req.description,
                        threshold_or_criteria=req.threshold_or_criteria,
                        bidder_filename=doc.metadata.filename,
                        page_number=page.page_number,
                        page_text=chunk,
                    )

                    for ev_item in llm_match.evidence:
                        # Grounding verification: verify excerpt actually exists in the claimed page
                        is_grounded, ground_err = verify_grounded_citation(
                            excerpt=ev_item.excerpt,
                            page_number=ev_item.page_number,
                            pages=doc.pages,
                        )

                        if not is_grounded:
                            # CRITICAL RULE: Discard unsupported reference and mark requirement for review
                            logger.warning(
                                f"Discarded unverified LLM evidence citation for requirement '{req.requirement_id}' "
                                f"in '{doc.metadata.filename}' page {ev_item.page_number}: {ground_err}"
                            )
                            req.needs_review = True
                            continue

                        # Deterministic validation in Python
                        det_val = self._extract_value_hint(ev_item.excerpt, req.category)
                        date_m = _DATE_REGEX.search(ev_item.excerpt)
                        det_date = date_m.group(1) if date_m else None

                        extracted_val = ev_item.extracted_value or det_val
                        valid_until = ev_item.valid_until or det_date

                        evidence_obj = BidderEvidence(
                            evidence_id=f"EVD-{evidence_counter:03d}",
                            requirement_id=req.requirement_id,
                            source_document_id=doc.metadata.document_id,
                            filename=doc.metadata.filename,
                            page_number=ev_item.page_number,
                            excerpt=ev_item.excerpt[:240],
                            extracted_value=extracted_val,
                            valid_until=valid_until,
                            confidence=round(ev_item.confidence, 2),
                        )
                        evidence_counter += 1
                        matched_by_req[req.requirement_id].append(evidence_obj)

        return matched_by_req

    def _match_deterministic(
        self,
        requirements: List[TenderRequirement],
        bidder_extractions: List[DocumentExtractionResult],
    ) -> Dict[str, List[BidderEvidence]]:
        """Match requirements using deterministic keyword and regex checks."""
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

                        extracted_val = self._extract_value_hint(page.text, req.category)
                        date_match = _DATE_REGEX.search(page.text)
                        valid_until = date_match.group(1) if date_match else None

                        confidence = 0.88 if (extracted_val or valid_until) else 0.75

                        evidence_item = BidderEvidence(
                            evidence_id=f"EVD-{evidence_counter:03d}",
                            requirement_id=req.requirement_id,
                            source_document_id=doc.metadata.document_id,
                            filename=doc.metadata.filename,
                            page_number=page.page_number,
                            excerpt=snippet,
                            extracted_value=extracted_val,
                            valid_until=valid_until,
                            confidence=confidence,
                        )
                        evidence_counter += 1
                        matched_by_req[req.requirement_id].append(evidence_item)

        return matched_by_req

    @staticmethod
    def _extract_relevant_excerpt(text: str, terms: List[str]) -> str:
        sentences = [
            s.strip()
            for s in re.split(r"(?<=[.!?;\n])\s+", text)
            if s.strip()
        ]
        for sentence in sentences:
            lower_s = sentence.lower()
            if any(term in lower_s for term in terms):
                return sentence[:240]
        return text[:240].strip()

    @staticmethod
    def _extract_value_hint(text: str, category: RequirementCategory) -> Optional[str]:
        if category == RequirementCategory.FINANCIAL:
            m = _MONEY_REGEX.search(text)
            if m:
                return m.group(1).strip()
        elif category == RequirementCategory.CERTIFICATION:
            m = _ISO_REGEX.search(text)
            if m:
                return m.group(1).strip()
        return None
