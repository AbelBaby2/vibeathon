"""External LLM API client abstraction configured through environment variables."""

from __future__ import annotations

import json
from typing import Any, Dict, Optional

import httpx

from app.core.config import Settings, get_settings
from app.core.exceptions import ExternalLLMError
from app.core.logging import get_logger

logger = get_logger(__name__)


class LLMProviderService:
    """Client wrapper for an external OpenAI-compatible LLM API endpoint."""

    def __init__(self, settings: Optional[Settings] = None) -> None:
        self.settings = settings or get_settings()

    @property
    def is_configured(self) -> bool:
        """Return True if a valid non-placeholder API key is available."""
        return self.settings.is_llm_configured

    def get_provider_metadata(self) -> Dict[str, Any]:
        """Return non-sensitive configuration metadata for health and diagnostics."""
        return {
            "provider": self.settings.llm_provider,
            "base_url": self.settings.llm_base_url,
            "model": self.settings.llm_model,
            "configured": self.is_configured,
            "timeout_seconds": self.settings.llm_timeout_seconds,
        }

    async def complete_json(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.1,
    ) -> Dict[str, Any]:
        """Send a chat completion request expecting a structured JSON object response."""
        if not self.is_configured:
            raise ExternalLLMError(
                "External LLM API is not configured. Set LLM_API_KEY in environment variables."
            )

        endpoint = f"{self.settings.llm_base_url.rstrip('/')}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.settings.llm_api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.settings.llm_model,
            "temperature": temperature,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }

        try:
            async with httpx.AsyncClient(
                timeout=float(self.settings.llm_timeout_seconds)
            ) as client:
                response = await client.post(endpoint, headers=headers, json=payload)
                response.raise_for_status()
                body = response.json()
                content = (
                    body.get("choices", [{}])[0]
                    .get("message", {})
                    .get("content", "{}")
                )
                return json.loads(content)
        except httpx.HTTPError as exc:
            logger.error(f"External LLM HTTP error: {exc}")
            raise ExternalLLMError(f"LLM API request failed: {exc}") from exc
        except (json.JSONDecodeError, KeyError, IndexError) as exc:
            logger.error(f"External LLM response parse error: {exc}")
            raise ExternalLLMError(
                "Failed to parse structured JSON from LLM provider response."
            ) from exc
