"""Health and readiness check endpoints."""

from __future__ import annotations

from fastapi import APIRouter

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
