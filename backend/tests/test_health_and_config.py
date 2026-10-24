"""Tests for health-check endpoints, environment settings, and response envelopes."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.core.config import Settings


def test_health_endpoint_returns_consistent_envelope(client: TestClient) -> None:
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert "X-Request-ID" in response.headers

    payload = response.json()
    assert payload["success"] is True
    assert payload["error"] is None
    assert payload["data"]["status"] == "healthy"
    assert payload["data"]["service"] == "Bid2Work AI"
    assert payload["data"]["database_ready"] is True
    assert payload["meta"]["processing_state"] == "COMPLETED"


def test_root_health_alias_works(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["success"] is True


def test_settings_placeholder_llm_key_detection(monkeypatch) -> None:
    monkeypatch.setenv("LLM_API_KEY", "your_llm_api_key_placeholder_here")
    s1 = Settings()
    assert s1.is_llm_configured is False

    monkeypatch.setenv("LLM_API_KEY", "sk-live-test-key-12345")
    s2 = Settings()
    assert s2.is_llm_configured is True


def test_cors_origins_parsing(monkeypatch) -> None:
    monkeypatch.setenv(
        "CORS_ALLOWED_ORIGINS", "http://localhost:5173, https://bid2work.onrender.com "
    )
    settings = Settings()
    assert settings.cors_allowed_origins == [
        "http://localhost:5173",
        "https://bid2work.onrender.com",
    ]
