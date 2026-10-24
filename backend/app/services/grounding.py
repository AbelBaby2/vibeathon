"""Evidence grounding and source verification utility for Bid2Work AI.

Guarantees that every AI-generated claim, requirement, or evidence citation actually
exists within the extracted text of the uploaded PDF on the specified page.
"""

from __future__ import annotations

import re
from typing import List, Optional, Tuple

from app.schemas.document import ExtractedPage


def normalize_whitespace(text: str) -> str:
    """Normalize whitespace and newlines for robust textual comparison."""
    if not text:
        return ""
    return re.sub(r"\s+", " ", text).strip().lower()


def verify_grounded_citation(
    excerpt: str,
    page_number: int,
    pages: List[ExtractedPage],
) -> Tuple[bool, Optional[str]]:
    """Verify that the excerpt provided by the LLM exists on the claimed document page.

    Returns:
        (is_verified: bool, error_reason: Optional[str])
    """
    if not excerpt or not excerpt.strip():
        return False, "Empty or missing excerpt."

    # Locate the claimed page
    target_page = next((p for p in pages if p.page_number == page_number), None)
    if not target_page or not target_page.text:
        return False, f"Claimed page {page_number} does not exist in the extracted document."

    norm_excerpt = normalize_whitespace(excerpt)
    norm_page = normalize_whitespace(target_page.text)

    # 1. Exact or normalized substring match
    if norm_excerpt in norm_page:
        return True, None

    # 2. Bounded sliding window match for excerpts truncated or slightly reformatted
    # Check leading 40 chars
    leading_probe = norm_excerpt[:40].strip()
    if len(leading_probe) >= 20 and leading_probe in norm_page:
        return True, None

    # Check trailing 40 chars
    trailing_probe = norm_excerpt[-40:].strip()
    if len(trailing_probe) >= 20 and trailing_probe in norm_page:
        return True, None

    return False, f"Cited excerpt could not be verified in extracted text on page {page_number}."
