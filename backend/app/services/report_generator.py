"""Report generation service for exporting compliance and permit readiness intelligence."""

from __future__ import annotations

import csv
import html
import io
import json
import uuid
from typing import List, Optional

from app.schemas.audit import AuditEvent
from app.schemas.common import DECISION_SUPPORT_DISCLAIMER
from app.schemas.compliance import ComplianceAnalysisResult, ComplianceStatus
from app.schemas.permit import PermitReadinessResult
from app.schemas.report import (
    ExportableReportData,
    ReportExportRequest,
    ReportFormat,
)


class ReportGeneratorService:
    """Formats compliance analysis, work-permit checklist, and audit trail into exportable reports."""

    def generate_compliance_csv(
        self,
        compliance: ComplianceAnalysisResult,
        permit: Optional[PermitReadinessResult] = None,
    ) -> str:
        """Generate a CSV report containing the 9 required compliance fields."""
        output = io.StringIO()
        writer = csv.writer(output, quoting=csv.QUOTE_MINIMAL)

        # Header row
        writer.writerow([
            "requirement_id",
            "category",
            "description",
            "status",
            "evidence_filename",
            "page",
            "excerpt",
            "explanation",
            "review_state",
        ])

        # Map permit checklist items by source requirement ID
        permit_by_req = {}
        if permit:
            for item in permit.checklist_items:
                if item.source_requirement_id:
                    permit_by_req[item.source_requirement_id] = item

        for assessment in compliance.assessments:
            req = assessment.requirement
            permit_item = permit_by_req.get(req.requirement_id)

            if permit_item:
                review_state = permit_item.review_status.value
            elif assessment.status == ComplianceStatus.EVIDENCE_FOUND:
                review_state = "ready_for_review"
            elif assessment.status in (ComplianceStatus.CONFLICTING, ComplianceStatus.NEEDS_REVIEW):
                review_state = "requires_verification"
            else:
                review_state = "incomplete"

            if assessment.matched_evidence:
                for ev in assessment.matched_evidence:
                    writer.writerow([
                        req.requirement_id,
                        req.category.value,
                        req.description,
                        assessment.status.value,
                        ev.filename,
                        ev.page_number,
                        ev.excerpt,
                        assessment.rationale,
                        review_state,
                    ])
            else:
                writer.writerow([
                    req.requirement_id,
                    req.category.value,
                    req.description,
                    assessment.status.value,
                    "",
                    "",
                    "",
                    assessment.rationale,
                    review_state,
                ])

        return output.getvalue()

    def generate_report(
        self,
        request: ReportExportRequest,
        audit_events: List[AuditEvent] | None = None,
    ) -> ExportableReportData:
        """Render an ExportableReportData object in JSON, MARKDOWN, or HTML format."""
        report_id = f"RPT-{uuid.uuid4().hex[:8].upper()}"
        comp = request.compliance_result
        permit = request.permit_result if request.include_permit_checklist else None
        trail = (audit_events or []) if request.include_audit_trail else []

        title = f"Bid2Work AI — Compliance & Permit Readiness Report ({comp.analysis_id})"
        exec_summary = (
            f"Tender '{comp.tender_document.filename}' evaluated against "
            f"{len(comp.bidder_documents)} bidder supporting document(s). "
            f"Overall compliance readiness score: {comp.summary.overall_readiness_score}% "
            f"({comp.summary.evidence_found_count}/{comp.summary.total_requirements} requirements "
            f"with Evidence Found, {comp.summary.mandatory_gap_count} mandatory gap(s))."
        )

        if request.format == ReportFormat.JSON:
            content = json.dumps(
                {
                    "report_id": report_id,
                    "title": title,
                    "executive_summary": exec_summary,
                    "compliance_analysis": comp.model_dump(mode="json"),
                    "permit_readiness": permit.model_dump(mode="json") if permit else None,
                    "audit_trail": [e.model_dump(mode="json") for e in trail],
                    "disclaimer": DECISION_SUPPORT_DISCLAIMER,
                },
                indent=2,
            )
            ext = "json"
            mime = "application/json"
        elif request.format == ReportFormat.HTML:
            content = self._render_html(title, exec_summary, comp, permit, trail)
            ext = "html"
            mime = "text/html"
        else:
            content = self._render_markdown(title, exec_summary, comp, permit, trail)
            ext = "md"
            mime = "text/markdown"

        filename = f"bid2work_report_{comp.analysis_id.lower()}.{ext}"

        return ExportableReportData(
            report_id=report_id,
            analysis_id=request.analysis_id,
            format=request.format,
            title=title,
            executive_summary=exec_summary,
            compliance_analysis=comp,
            permit_readiness=permit,
            audit_trail=trail,
            content=content,
            filename=filename,
            mime_type=mime,
            disclaimer=DECISION_SUPPORT_DISCLAIMER,
        )

    @staticmethod
    def _render_markdown(title, exec_summary, comp, permit, trail) -> str:
        lines = [
            f"# {title}",
            "",
            f"> **Disclaimer:** {DECISION_SUPPORT_DISCLAIMER}",
            "",
            "## 1. Executive Summary",
            exec_summary,
            "",
            "## 2. Tender Compliance Assessment",
            f"- **Tender Document:** `{comp.tender_document.filename}` ({comp.tender_document.page_count} pages)",
            f"- **Total Requirements:** {comp.summary.total_requirements}",
            f"- **Evidence Found:** {comp.summary.evidence_found_count}",
            f"- **Missing:** {comp.summary.missing_count}",
            f"- **Conflicting:** {comp.summary.conflicting_count}",
            f"- **Needs Review:** {comp.summary.needs_review_count}",
            "",
        ]
        for assessment in comp.assessments:
            req = assessment.requirement
            lines.append(
                f"### [{req.requirement_id}] {req.title} — **{assessment.status.value}**"
            )
            lines.append(f"- **Category:** {req.category.value} | **Priority:** {req.priority.value}")
            lines.append(
                f"- **Tender Source:** `{req.source.filename}` (Page {req.source.page_number}) — *\"{req.source.excerpt}\"*"
            )
            lines.append(f"- **Rationale:** {assessment.rationale}")
            if assessment.matched_evidence:
                for ev in assessment.matched_evidence:
                    lines.append(
                        f"  - **Evidence [{ev.evidence_id}]:** `{ev.filename}` (Page {ev.page_number}) — *\"{ev.excerpt}\"*"
                    )
            lines.append("")

        if permit:
            lines.append("## 3. Work-Permit Readiness Checklist")
            lines.append(
                f"- **Permit Pack ID:** `{permit.permit_pack_id}` | **Readiness:** {permit.summary.readiness_percentage}%"
            )
            for item in permit.checklist_items:
                lines.append(
                    f"- **[{item.item_id}] {item.title}** ({item.category.value}): **{item.status.value}**"
                )
            lines.append("")

        if trail:
            lines.append("## 4. Audit Trail")
            for evt in trail:
                lines.append(
                    f"- `{evt.created_at.isoformat()}` [{evt.event_type.value}] {evt.summary}"
                )

        return "\n".join(lines)

    @staticmethod
    def _render_html(title, exec_summary, comp, permit, trail) -> str:
        esc = html.escape
        rows = "".join(
            f"<tr><td>{esc(a.requirement_id)}</td><td>{esc(a.requirement.category.value)}</td>"
            f"<td>{esc(a.requirement.title)}</td><td><strong>{esc(a.status.value)}</strong></td>"
            f"<td>{esc(a.rationale)}</td></tr>"
            for a in comp.assessments
        )
        return (
            f"<!DOCTYPE html><html><head><meta charset='utf-8'><title>{esc(title)}</title></head>"
            f"<body><h1>{esc(title)}</h1>"
            f"<p><em>{esc(DECISION_SUPPORT_DISCLAIMER)}</em></p>"
            f"<h2>Executive Summary</h2><p>{esc(exec_summary)}</p>"
            f"<h2>Compliance Matrix</h2>"
            f"<table border='1' cellpadding='6' cellspacing='0'>"
            f"<thead><tr><th>ID</th><th>Category</th><th>Requirement</th><th>Status</th><th>Rationale</th></tr></thead>"
            f"<tbody>{rows}</tbody></table></body></html>"
        )
