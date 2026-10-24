"""Exportable report data contracts for compliance and permit readiness."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field

from app.schemas.audit import AuditEvent
from app.schemas.common import DECISION_SUPPORT_DISCLAIMER
from app.schemas.compliance import ComplianceAnalysisResult
from app.schemas.permit import PermitReadinessResult


class ReportFormat(str, Enum):
    """Supported report export formats."""

    JSON = "JSON"
    MARKDOWN = "MARKDOWN"
    HTML = "HTML"


class ReportExportRequest(BaseModel):
    """Request payload for exporting a consolidated compliance and permit report."""

    analysis_id: str = Field(
        ..., min_length=1, description="Compliance analysis session ID."
    )
    format: ReportFormat = Field(
        default=ReportFormat.MARKDOWN,
        description="Desired output report format (JSON, MARKDOWN, or HTML).",
    )
    include_permit_checklist: bool = Field(
        default=True,
        description="Whether to include the post-award work-permit checklist section.",
    )
    include_audit_trail: bool = Field(
        default=True,
        description="Whether to include the audit event trail section.",
    )
    compliance_result: ComplianceAnalysisResult = Field(
        ..., description="Compliance analysis result to include in the report."
    )
    permit_result: Optional[PermitReadinessResult] = Field(
        default=None,
        description="Optional work-permit readiness result to include.",
    )


class ExportableReportData(BaseModel):
    """Structured exportable report payload including rendered content and metadata."""

    report_id: str = Field(
        ..., description="Stable identifier for the generated report (e.g., RPT-001)."
    )
    analysis_id: str = Field(
        ..., description="Originating compliance analysis session ID."
    )
    generated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp of report generation.",
    )
    format: ReportFormat = Field(..., description="Format of the rendered report.")
    title: str = Field(..., description="Report title.")
    executive_summary: str = Field(
        ..., description="High-level narrative summary of compliance and permit readiness."
    )
    compliance_analysis: ComplianceAnalysisResult = Field(
        ..., description="Full compliance analysis snapshot."
    )
    permit_readiness: Optional[PermitReadinessResult] = Field(
        default=None, description="Optional work-permit readiness snapshot."
    )
    audit_trail: List[AuditEvent] = Field(
        default_factory=list, description="Audit events included in the export."
    )
    content: str = Field(
        ..., description="Serialized report content in the requested format."
    )
    filename: str = Field(
        ..., description="Suggested download filename with extension."
    )
    mime_type: str = Field(
        ..., description="MIME type corresponding to the requested format."
    )
    disclaimer: str = Field(
        default=DECISION_SUPPORT_DISCLAIMER,
        description="Mandatory decision-support disclaimer.",
    )
