"""Application exceptions and FastAPI error handler registrations."""

from __future__ import annotations

from typing import List, Optional

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.core.logging import get_logger, get_request_id
from app.schemas.common import (
    ApiError,
    ApiErrorDetail,
    ApiMeta,
    ApiResponse,
    ErrorCode,
    ProcessingState,
)

logger = get_logger(__name__)


class AppError(Exception):
    """Base application exception with structured error code and HTTP status."""

    def __init__(
        self,
        message: str,
        code: ErrorCode = ErrorCode.INTERNAL_ERROR,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        details: Optional[List[ApiErrorDetail]] = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or []


class UploadLimitExceededError(AppError):
    """Raised when uploaded file size, count, or page count exceeds configured limits."""

    def __init__(
        self, message: str, details: Optional[List[ApiErrorDetail]] = None
    ) -> None:
        super().__init__(
            message=message,
            code=ErrorCode.UPLOAD_LIMIT_EXCEEDED,
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            details=details,
        )


class InvalidFileTypeError(AppError):
    """Raised when a non-PDF or corrupted file is uploaded."""

    def __init__(
        self, message: str, details: Optional[List[ApiErrorDetail]] = None
    ) -> None:
        super().__init__(
            message=message,
            code=ErrorCode.INVALID_FILE_TYPE,
            status_code=status.HTTP_400_BAD_REQUEST,
            details=details,
        )


class PDFExtractionError(AppError):
    """Raised when pypdf fails to parse or extract readable content from a PDF."""

    def __init__(
        self, message: str, details: Optional[List[ApiErrorDetail]] = None
    ) -> None:
        super().__init__(
            message=message,
            code=ErrorCode.PDF_EXTRACTION_ERROR,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            details=details,
        )


class ExternalLLMError(AppError):
    """Raised when an external LLM API call fails and no fallback is permitted."""

    def __init__(
        self, message: str, details: Optional[List[ApiErrorDetail]] = None
    ) -> None:
        super().__init__(
            message=message,
            code=ErrorCode.LLM_PROVIDER_ERROR,
            status_code=status.HTTP_502_BAD_GATEWAY,
            details=details,
        )


def _build_error_response(
    status_code: int,
    code: ErrorCode,
    message: str,
    details: Optional[List[ApiErrorDetail]] = None,
) -> JSONResponse:
    req_id = get_request_id()
    envelope = ApiResponse(
        success=False,
        data=None,
        error=ApiError(
            code=code,
            message=message,
            details=details or [],
            request_id=req_id,
        ),
        meta=ApiMeta(
            request_id=req_id,
            processing_state=ProcessingState.FAILED,
        ),
    )
    return JSONResponse(
        status_code=status_code,
        content=envelope.model_dump(mode="json"),
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Attach standardized JSON error handlers to the FastAPI instance."""

    @app.exception_handler(AppError)
    async def handle_app_error(_: Request, exc: AppError) -> JSONResponse:
        logger.warning(
            f"Application error [{exc.code}]: {exc.message}",
            extra={"extra_fields": {"error_code": exc.code.value}},
        )
        return _build_error_response(
            status_code=exc.status_code,
            code=exc.code,
            message=exc.message,
            details=exc.details,
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(
        _: Request, exc: RequestValidationError
    ) -> JSONResponse:
        details = [
            ApiErrorDetail(
                field=".".join(str(loc) for loc in err.get("loc", [])),
                message=err.get("msg", "Invalid value"),
                code=err.get("type", "validation_error"),
            )
            for err in exc.errors()
        ]
        logger.info("Request validation failed", extra={"extra_fields": {"count": len(details)}})
        return _build_error_response(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            code=ErrorCode.VALIDATION_ERROR,
            message="Request payload or parameters failed validation.",
            details=details,
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_error(_: Request, exc: Exception) -> JSONResponse:
        logger.exception(f"Unhandled server exception: {exc}")
        return _build_error_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            code=ErrorCode.INTERNAL_ERROR,
            message="An unexpected internal server error occurred.",
        )
