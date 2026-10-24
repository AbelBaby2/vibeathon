"""External LLM API client abstraction configured through environment variables."""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional, Type, TypeVar

from openai import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    AsyncOpenAI,
    AuthenticationError,
    RateLimitError,
)
from pydantic import BaseModel, ValidationError

from app.core.config import Settings, get_settings
from app.core.exceptions import ConfigurationError, ExternalLLMError
from app.core.logging import get_logger
from app.services.prompts import (
    LLMConflictExplanation,
    LLMEvidenceMatchingResult,
    LLMRequirementExtractionResult,
    LLMSafetyMappingResult,
    build_conflict_explanation_prompts,
    build_evidence_matching_prompts,
    build_requirement_extraction_prompts,
    build_safety_mapping_prompts,
)

logger = get_logger(__name__)

T = TypeVar("T", bound=BaseModel)


class LLMProviderService:
    """Client wrapper for an external OpenAI-compatible LLM API endpoint."""

    def __init__(
        self,
        settings: Optional[Settings] = None,
        client: Optional[AsyncOpenAI] = None,
    ) -> None:
        self.settings = settings or get_settings()
        self._client = client

    @property
    def is_configured(self) -> bool:
        """Return True if a valid non-placeholder API key is available."""
        return self.settings.is_llm_configured

    @property
    def is_enabled(self) -> bool:
        """Return True if live LLM mode is enabled."""
        return self.settings.llm_enabled

    @property
    def client(self) -> AsyncOpenAI:
        """Return initialized AsyncOpenAI client or raise ConfigurationError."""
        if self._client is None:
            self.settings.validate_live_llm_config()
            self._client = AsyncOpenAI(
                api_key=self.settings.llm_api_key,
                base_url=self.settings.llm_base_url or None,
                timeout=float(self.settings.llm_timeout_seconds),
                max_retries=0,  # Explicit retry budget managed in complete_structured
            )
        return self._client

    def get_provider_metadata(self) -> Dict[str, Any]:
        """Return non-sensitive configuration metadata for health and diagnostics."""
        return {
            "provider": self.settings.llm_provider,
            "base_url": self.settings.llm_base_url,
            "model": self.settings.llm_model,
            "enabled": self.settings.llm_enabled,
            "configured": self.is_configured,
            "timeout_seconds": self.settings.llm_timeout_seconds,
            "max_retries": self.settings.llm_max_retries,
        }

    async def complete_structured(
        self,
        system_prompt: str,
        user_prompt: str,
        response_model: Type[T],
        temperature: float = 0.1,
    ) -> T:
        """Send chat completion request and validate response against Pydantic schema."""
        max_retries = self.settings.llm_max_retries
        attempts = 0
        last_error: Optional[Exception] = None
        current_user_prompt = user_prompt

        while attempts <= max_retries:
            attempts += 1
            try:
                response = await self.client.chat.completions.create(
                    model=self.settings.llm_model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": current_user_prompt},
                    ],
                    response_format={"type": "json_object"},
                    temperature=temperature,
                )
                choice = response.choices[0]
                content = choice.message.content or "{}"
                return response_model.model_validate_json(content)
            except (json.JSONDecodeError, ValidationError) as exc:
                last_error = exc
                logger.warning(
                    f"LLM response failed schema validation (attempt {attempts}/{max_retries + 1})"
                )
                if attempts <= max_retries:
                    current_user_prompt = (
                        f"{user_prompt}\n\n"
                        f"CORRECTION: Your previous output failed schema validation ({type(exc).__name__}). "
                        f"Return strictly valid JSON adhering to the specified schema."
                    )
            except AuthenticationError as exc:
                logger.error("LLM provider authentication failed: invalid API key.")
                raise ConfigurationError(
                    "LLM API authentication failed. Please check your LLM_API_KEY."
                ) from exc
            except RateLimitError as exc:
                logger.error("LLM provider rate limit exceeded.")
                raise ExternalLLMError(
                    "LLM provider rate limit reached. Please retry after some time."
                ) from exc
            except APITimeoutError as exc:
                logger.error(
                    f"LLM request timed out after {self.settings.llm_timeout_seconds}s."
                )
                raise ExternalLLMError(
                    "LLM provider request timed out. Try again or increase LLM_TIMEOUT_SECONDS."
                ) from exc
            except APIConnectionError as exc:
                logger.error("LLM provider connection failed; endpoint unreachable.")
                raise ExternalLLMError(
                    "LLM provider connection failed or host is unreachable."
                ) from exc
            except APIStatusError as exc:
                logger.error(f"LLM provider returned HTTP error {exc.status_code}.")
                raise ExternalLLMError(
                    f"LLM provider request failed with status {exc.status_code}."
                ) from exc
            except (ConfigurationError, ExternalLLMError):
                raise
            except Exception as exc:
                logger.error(f"Unexpected error during LLM invocation: {type(exc).__name__}")
                raise ExternalLLMError(f"LLM invocation failed: {type(exc).__name__}") from exc

        raise ExternalLLMError(
            f"Failed to obtain valid structured output from LLM after {max_retries + 1} attempts."
        ) from last_error

    async def complete_json(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.1,
    ) -> Dict[str, Any]:
        """Send chat completion request expecting raw JSON dictionary."""
        class _RawJsonModel(BaseModel):
            class Config:
                extra = "allow"

        # Delegate through structured completion to ensure same retry and error handling
        try:
            res = await self.complete_structured(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                response_model=_RawJsonModel,
                temperature=temperature,
            )
            return res.model_dump()
        except Exception:
            # Fallback direct parse if needed
            self.settings.validate_live_llm_config()
            response = await self.client.chat.completions.create(
                model=self.settings.llm_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                response_format={"type": "json_object"},
                temperature=temperature,
            )
            content = response.choices[0].message.content or "{}"
            return json.loads(content)

    async def extract_requirements_from_chunk(
        self,
        document_filename: str,
        page_number: int,
        page_text: str,
    ) -> LLMRequirementExtractionResult:
        """Extract structured tender requirements from a single document page chunk."""
        system_prompt, user_prompt = build_requirement_extraction_prompts(
            document_filename=document_filename,
            page_number=page_number,
            page_text=page_text,
        )
        return await self.complete_structured(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            response_model=LLMRequirementExtractionResult,
        )

    async def match_evidence_in_chunk(
        self,
        requirement_id: str,
        requirement_category: str,
        requirement_title: str,
        requirement_desc: str,
        threshold_or_criteria: Optional[str],
        bidder_filename: str,
        page_number: int,
        page_text: str,
    ) -> LLMEvidenceMatchingResult:
        """Search for verifiable evidence addressing a requirement in a bidder page chunk."""
        system_prompt, user_prompt = build_evidence_matching_prompts(
            requirement_id=requirement_id,
            requirement_category=requirement_category,
            requirement_title=requirement_title,
            requirement_desc=requirement_desc,
            threshold_or_criteria=threshold_or_criteria,
            bidder_filename=bidder_filename,
            page_number=page_number,
            page_text=page_text,
        )
        return await self.complete_structured(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            response_model=LLMEvidenceMatchingResult,
        )

    async def explain_conflict(
        self,
        requirement_id: str,
        requirement_title: str,
        conflicting_snippets: List[dict],
    ) -> LLMConflictExplanation:
        """Generate a neutral, grounded explanation of conflicting bidder statements."""
        system_prompt, user_prompt = build_conflict_explanation_prompts(
            requirement_id=requirement_id,
            requirement_title=requirement_title,
            conflicting_snippets=conflicting_snippets,
        )
        return await self.complete_structured(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            response_model=LLMConflictExplanation,
        )

    async def map_safety_requirements(
        self,
        safety_requirements: List[dict],
    ) -> LLMSafetyMappingResult:
        """Map tender safety requirements into work-permit checklist attributes."""
        system_prompt, user_prompt = build_safety_mapping_prompts(
            safety_requirements=safety_requirements
        )
        return await self.complete_structured(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            response_model=LLMSafetyMappingResult,
        )
