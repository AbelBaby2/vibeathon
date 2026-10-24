"""Health and readiness check endpoints."""

from __future__ import annotations

import os
from pathlib import Path

from fastapi import APIRouter, status
from fastapi.responses import JSONResponse

from app.core.config import get_settings
from app.core.logging import get_request_id
from app.db.sqlite import check_database_health
from app.schemas.common import ApiMeta, ApiResponse, HealthStatus, ProcessingState

router = APIRouter(tags=["Health"])


@router.get("/health", response_model=ApiResponse[HealthStatus])
@router.get("/api/v1/health", response_model=ApiResponse[HealthStatus])
async def get_health() -> ApiResponse[HealthStatus]:
    """Return service health, configuration limits, and readiness status."""
    settings = get_settings()
    db_ok = check_database_health()

    health = HealthStatus(
        status="healthy",
        service=settings.app_name,
        version=settings.app_version,
        environment=settings.app_env,
        llm_enabled=settings.llm_enabled,
        llm_configured=settings.is_llm_configured,
        llm_provider=settings.llm_provider,
        llm_model=settings.llm_model,
        database_ready=db_ok,
        max_upload_size_mb=settings.max_upload_size_mb,
        max_bidder_files=settings.max_bidder_files,
    )
    return ApiResponse[HealthStatus](
        success=True,
        data=health,
        meta=ApiMeta(
            request_id=get_request_id(),
            processing_state=ProcessingState.COMPLETED,
            version=settings.app_version,
        ),
    )


@router.get("/api/v1/health/ready")
async def get_readiness() -> JSONResponse:
    """Readiness check verifying database connectivity, storage, and configuration."""
    settings = get_settings()
    db_ok = check_database_health()
    temp_dir = Path(settings.temp_upload_dir)
    storage_ok = temp_dir.exists() and os.access(str(temp_dir), os.W_OK)

    # In live mode (LLM_ENABLED=true), a valid key is required for readiness
    llm_ready = (not settings.llm_enabled) or settings.is_llm_configured
    is_ready = db_ok and storage_ok and llm_ready

    payload = {
        "ready": is_ready,
        "database_ready": db_ok,
        "storage_ready": storage_ok,
        "llm_ready": llm_ready,
        "configuration": {
            "max_upload_size_mb": settings.max_upload_size_mb,
            "max_bidder_files": settings.max_bidder_files,
            "max_pages_per_pdf": settings.max_pages_per_pdf,
            "llm_enabled": settings.llm_enabled,
            "llm_configured": settings.is_llm_configured,
        },
    }

    status_code = status.HTTP_200_OK if is_ready else status.HTTP_503_SERVICE_UNAVAILABLE
    envelope = ApiResponse(
        success=is_ready,
        data=payload,
        meta=ApiMeta(
            request_id=get_request_id(),
            processing_state=ProcessingState.COMPLETED if is_ready else ProcessingState.FAILED,
            version=settings.app_version,
        ),
    )
    return JSONResponse(status_code=status_code, content=envelope.model_dump(mode="json"))
