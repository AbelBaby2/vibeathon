import React, { useState } from "react";
import {
  CheckCircle,
  Download,
  FileCheck2,
  FileSpreadsheet,
  HardHat,
  Loader2,
  ShieldAlert
} from "lucide-react";
import { StatusBadge } from "../components/StatusBadge";
import { bid2WorkApi } from "../services/apiClient";
import type {
  ComplianceAnalysisResult,
  PermitReadinessResult,
  ReportFormat
} from "../types";

interface ComplianceReportsPageProps {
  currentAnalysis: ComplianceAnalysisResult | null;
  analyses: ComplianceAnalysisResult[];
  permitResult: PermitReadinessResult | null;
  onSelectAnalysis: (analysisId: string) => void;
  onNavigateToAnalysis: () => void;
}

export const ComplianceReportsPage: React.FC<ComplianceReportsPageProps> = ({
  currentAnalysis,
  analyses,
  permitResult,
  onSelectAnalysis,
  onNavigateToAnalysis
}) => {
  const [isDownloadingCsv, setIsDownloadingCsv] = useState(false);
  const [isExportingStructured, setIsExportingStructured] = useState(false);
  const [selectedFormat, setSelectedFormat] = useState<ReportFormat>("MARKDOWN");
  const [includeAuditTrail, setIncludeAuditTrail] = useState(true);
  const [downloadSuccess, setDownloadSuccess] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  if (!currentAnalysis) {
    return (
      <div className="page-container">
        <div className="empty-state">
          <FileSpreadsheet className="empty-state-icon" style={{ width: "48px", height: "48px", color: "var(--navy-400)" }} />
          <h2 className="empty-state-title">No Analysis Selected for Reporting</h2>
          <p className="empty-state-text">
            Execute or select a tender compliance analysis to view findings summaries, evidence traceability tables, and export backend CSV reports.
          </p>
          <button
            type="button"
            className="btn btn-primary"
            onClick={onNavigateToAnalysis}
          >
            Go to Tender Analysis
          </button>
        </div>
      </div>
    );
  }

  // Handle Backend CSV Download
  const handleDownloadCsv = async () => {
    setIsDownloadingCsv(true);
    setErrorMessage(null);
    setDownloadSuccess(null);

    try {
      await bid2WorkApi.downloadReportCsv(currentAnalysis.analysis_id);
      setDownloadSuccess(
        `Successfully downloaded compliance CSV report for ${currentAnalysis.analysis_id}.`
      );
    } catch (err) {
      setErrorMessage(
        err instanceof Error ? err.message : "Failed to generate CSV report from backend."
      );
    } finally {
      setIsDownloadingCsv(false);
    }
  };

  // Handle Structured Export (Markdown, HTML, JSON)
  const handleExportStructured = async () => {
    setIsExportingStructured(true);
    setErrorMessage(null);
    setDownloadSuccess(null);

    try {
      const response = await bid2WorkApi.exportReport({
        analysis_id: currentAnalysis.analysis_id,
        format: selectedFormat,
        include_permit_checklist: Boolean(permitResult),
        include_audit_trail: includeAuditTrail,
        compliance_result: currentAnalysis,
        permit_result: permitResult
      });

      if (response.data) {
        // Trigger browser download of returned report text
        const blob = new Blob([response.data.content], { type: response.data.mime_type });
        const url = URL.createObjectURL(blob);
        const link = document.createElement("a");
        link.href = url;
        link.setAttribute("download", response.data.filename);
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        URL.revokeObjectURL(url);

        setDownloadSuccess(
          `Exported ${selectedFormat} report (${response.data.filename}) successfully.`
        );
      }
    } catch (err) {
      setErrorMessage(
        err instanceof Error ? err.message : "Failed to export report from backend."
      );
    } finally {
      setIsExportingStructured(false);
    }
  };

  // Filter unresolved requirements (Missing, Conflicting, Needs Review)
  const unresolvedAssessments = currentAnalysis.assessments.filter(
    (a) => a.status !== "Evidence Found"
  );

  return (
    <div className="page-container">
      {/* Target Analysis Header & Actions */}
      <div className="card" style={{ marginBottom: "1.5rem" }}>
        <div className="card-header">
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginBottom: "0.25rem" }}>
              <span style={{ fontFamily: "var(--font-mono)", fontSize: "0.8rem", fontWeight: 700, color: "var(--teal-800)" }}>
                {currentAnalysis.analysis_id}
              </span>
              <span className="badge" style={{ backgroundColor: "var(--navy-100)", color: "var(--navy-700)" }}>
                {currentAnalysis.tender_document.filename}
              </span>
            </div>
            <h2 className="card-title">
              <FileSpreadsheet style={{ width: "18px", height: "18px", color: "var(--teal-600)" }} />
              <span>Consolidated Compliance & Work-Permit Report Center</span>
            </h2>
          </div>

          <div style={{ display: "flex", gap: "0.75rem", alignItems: "center" }}>
            {analyses.length > 1 && (
              <select
                className="select"
                style={{ width: "auto", fontSize: "0.78rem", padding: "0.35rem 0.6rem" }}
                value={currentAnalysis.analysis_id}
                onChange={(e) => onSelectAnalysis(e.target.value)}
                aria-label="Select Analysis for Report"
              >
                {analyses.map((a) => (
                  <option key={a.analysis_id} value={a.analysis_id}>
                    {a.analysis_id} — {a.tender_document.filename}
                  </option>
                ))}
              </select>
            )}
            <button
              type="button"
              className="btn btn-primary"
              onClick={handleDownloadCsv}
              disabled={isDownloadingCsv}
              id="btn-download-csv-report"
            >
              {isDownloadingCsv ? (
                <>
                  <Loader2 style={{ width: "15px", height: "15px", animation: "spin 1s linear infinite" }} />
                  <span>Generating CSV...</span>
                </>
              ) : (
                <>
                  <Download style={{ width: "15px", height: "15px" }} />
                  <span>Download CSV Report</span>
                </>
              )}
            </button>
          </div>
        </div>

        {/* Feedback Banners */}
        {downloadSuccess && (
          <div className="alert alert-info" style={{ marginBottom: "1rem" }}>
            <CheckCircle style={{ width: "16px", height: "16px", flexShrink: 0, color: "var(--teal-600)" }} />
            <span>{downloadSuccess}</span>
          </div>
        )}

        {errorMessage && (
          <div className="alert alert-danger" role="alert" style={{ marginBottom: "1rem" }}>
            <ShieldAlert style={{ width: "16px", height: "16px", flexShrink: 0 }} />
            <span>{errorMessage}</span>
          </div>
        )}

        {/* Summary of Findings Rollup */}
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: "0.75rem", padding: "1rem", backgroundColor: "var(--navy-50)", borderRadius: "var(--radius-md)", border: "1px solid var(--border-subtle)", fontSize: "0.8rem" }}>
          <div>
            <div style={{ color: "var(--navy-500)", textTransform: "uppercase", fontSize: "0.7rem" }}>Total Requirements</div>
            <div style={{ fontSize: "1.25rem", fontWeight: 700, color: "var(--navy-900)" }}>
              {currentAnalysis.summary.total_requirements}
            </div>
          </div>
          <div>
            <div style={{ color: "var(--navy-500)", textTransform: "uppercase", fontSize: "0.7rem" }}>Evidence Verified</div>
            <div style={{ fontSize: "1.25rem", fontWeight: 700, color: "#166534" }}>
              {currentAnalysis.summary.evidence_found_count} ({currentAnalysis.summary.overall_readiness_score.toFixed(0)}%)
            </div>
          </div>
          <div>
            <div style={{ color: "var(--navy-500)", textTransform: "uppercase", fontSize: "0.7rem" }}>Missing Gaps</div>
            <div style={{ fontSize: "1.25rem", fontWeight: 700, color: "#991B1B" }}>
              {currentAnalysis.summary.missing_count}
            </div>
          </div>
          <div>
            <div style={{ color: "var(--navy-500)", textTransform: "uppercase", fontSize: "0.7rem" }}>Conflicting Evidence</div>
            <div style={{ fontSize: "1.25rem", fontWeight: 700, color: "#92400E" }}>
              {currentAnalysis.summary.conflicting_count}
            </div>
          </div>
          <div>
            <div style={{ color: "var(--navy-500)", textTransform: "uppercase", fontSize: "0.7rem" }}>Permit Checklist Items</div>
            <div style={{ fontSize: "1.25rem", fontWeight: 700, color: "var(--teal-800)" }}>
              {permitResult ? `${permitResult.summary.total_items} items (${permitResult.summary.readiness_percentage.toFixed(0)}%)` : "Not Simulated"}
            </div>
          </div>
        </div>

        {/* Multi-Format Export Options */}
        <div style={{ marginTop: "1rem", paddingTop: "0.85rem", borderTop: "1px solid var(--border-subtle)", display: "flex", flexWrap: "wrap", alignItems: "center", justifyContent: "space-between", gap: "0.75rem" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "0.75rem", flexWrap: "wrap" }}>
            <span style={{ fontSize: "0.76rem", fontWeight: 600, color: "var(--navy-800)" }}>
              Custom Export Format:
            </span>
            <select
              className="select"
              style={{ width: "auto", padding: "0.3rem 0.6rem", fontSize: "0.76rem" }}
              value={selectedFormat}
              onChange={(e) => setSelectedFormat(e.target.value as ReportFormat)}
              aria-label="Export format"
            >
              <option value="MARKDOWN">Markdown Document (.md)</option>
              <option value="HTML">HTML Standalone Report (.html)</option>
              <option value="JSON">Raw JSON Schema Data (.json)</option>
            </select>

            <label style={{ display: "flex", alignItems: "center", gap: "0.35rem", fontSize: "0.76rem", color: "var(--navy-700)", cursor: "pointer" }}>
              <input
                type="checkbox"
                checked={includeAuditTrail}
                onChange={(e) => setIncludeAuditTrail(e.target.checked)}
                style={{ accentColor: "var(--teal-600)" }}
              />
              <span>Include SQLite Audit Trail</span>
            </label>
          </div>

          <button
            type="button"
            className="btn btn-secondary btn-sm"
            onClick={handleExportStructured}
            disabled={isExportingStructured}
            id="btn-export-structured-report"
          >
            {isExportingStructured ? "Exporting..." : `Export ${selectedFormat}`}
          </button>
        </div>
      </div>

      {/* Unresolved Compliance Gaps Table */}
      <div className="card" style={{ marginBottom: "1.5rem" }}>
        <div className="card-header">
          <div>
            <h2 className="card-title">
              <ShieldAlert style={{ width: "16px", height: "16px", color: "#991B1B" }} />
              <span>Unresolved Compliance Requirements ({unresolvedAssessments.length})</span>
            </h2>
            <p className="card-description">
              Requirements with Missing, Conflicting, or Needs Review status requiring bidder remediation
            </p>
          </div>
        </div>

        <div className="table-container">
          <table className="data-table" aria-label="Unresolved Compliance Requirements">
            <thead>
              <tr>
                <th style={{ width: "100px" }}>ID & Priority</th>
                <th style={{ width: "110px" }}>Category</th>
                <th>Requirement Description</th>
                <th style={{ width: "120px" }}>Status</th>
                <th>Tender Reference</th>
                <th>Recommended Action</th>
              </tr>
            </thead>
            <tbody>
              {unresolvedAssessments.length === 0 ? (
                <tr>
                  <td colSpan={6} style={{ textAlign: "center", padding: "1.75rem", color: "#166534" }}>
                    ✓ All extracted requirements have verifiable supporting evidence. No outstanding compliance gaps.
                  </td>
                </tr>
              ) : (
                unresolvedAssessments.map((assessment) => (
                  <tr key={assessment.requirement_id}>
                    <td>
                      <div style={{ fontFamily: "var(--font-mono)", fontWeight: 600 }}>
                        {assessment.requirement_id}
                      </div>
                      <StatusBadge status={assessment.requirement.priority} type="priority" />
                    </td>
                    <td>
                      <StatusBadge status={assessment.requirement.category} type="category" />
                    </td>
                    <td>
                      <div style={{ fontWeight: 600, color: "var(--navy-900)" }}>
                        {assessment.requirement.title}
                      </div>
                      <div style={{ fontSize: "0.76rem", color: "var(--navy-700)", marginTop: "0.2rem" }}>
                        {assessment.requirement.description}
                      </div>
                    </td>
                    <td>
                      <StatusBadge status={assessment.status} type="compliance" />
                    </td>
                    <td style={{ fontSize: "0.75rem", color: "var(--navy-600)" }}>
                      <strong>{assessment.requirement.source.filename}</strong> (p. {assessment.requirement.source.page_number})
                    </td>
                    <td style={{ fontSize: "0.76rem", color: "#1E40AF" }}>
                      {assessment.recommended_action || "Provide updated accreditation document before deadline."}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Complete Traceability Table */}
      <div className="card" style={{ marginBottom: "1.5rem" }}>
        <div className="card-header">
          <div>
            <h2 className="card-title">
              <FileCheck2 style={{ width: "16px", height: "16px", color: "var(--teal-600)" }} />
              <span>Evidence Traceability Mapping</span>
            </h2>
            <p className="card-description">
              Cross-reference of tender requirements against extracted bidder proof documents
            </p>
          </div>
        </div>

        <div className="table-container">
          <table className="data-table" aria-label="Evidence Traceability Table">
            <thead>
              <tr>
                <th style={{ width: "95px" }}>Clause ID</th>
                <th>Requirement Criteria</th>
                <th style={{ width: "120px" }}>Status</th>
                <th>Bidder Proof Document</th>
                <th>Evidence Excerpt Snippet</th>
              </tr>
            </thead>
            <tbody>
              {currentAnalysis.assessments.map((a) => {
                const ev = a.matched_evidence[0];
                return (
                  <tr key={a.requirement_id}>
                    <td style={{ fontFamily: "var(--font-mono)", fontWeight: 600 }}>
                      {a.requirement_id}
                    </td>
                    <td>
                      <div style={{ fontWeight: 500, color: "var(--navy-900)" }}>{a.requirement.title}</div>
                      <div style={{ fontSize: "0.74rem", color: "var(--navy-600)" }}>
                        {a.requirement.source.filename} (p. {a.requirement.source.page_number})
                      </div>
                    </td>
                    <td>
                      <StatusBadge status={a.status} type="compliance" />
                    </td>
                    <td>
                      {ev ? (
                        <div style={{ fontSize: "0.76rem" }}>
                          <strong>{ev.filename}</strong> (p. {ev.page_number})
                        </div>
                      ) : (
                        <span style={{ color: "var(--navy-400)", fontSize: "0.75rem", fontStyle: "italic" }}>
                          None attached
                        </span>
                      )}
                    </td>
                    <td style={{ fontSize: "0.74rem", color: "var(--navy-700)" }}>
                      {ev ? `"${ev.excerpt.slice(0, 120)}${ev.excerpt.length > 120 ? "..." : ""}"` : "—"}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* Linked Work-Permit Readiness Checklist if Present */}
      {permitResult && (
        <div className="card">
          <div className="card-header">
            <div>
              <h2 className="card-title">
                <HardHat style={{ width: "16px", height: "16px", color: "var(--teal-600)" }} />
                <span>Linked Post-Award Work-Permit Status</span>
              </h2>
              <p className="card-description">
                Safety carryover items linked to {permitResult.contract_reference}
              </p>
            </div>
          </div>

          <div className="table-container">
            <table className="data-table" aria-label="Permit Checklist Status">
              <thead>
                <tr>
                  <th style={{ width: "90px" }}>Item ID</th>
                  <th>Safety Domain & Title</th>
                  <th style={{ width: "110px" }}>Readiness</th>
                  <th style={{ width: "150px" }}>Review State</th>
                  <th>Reviewer Sign-off</th>
                </tr>
              </thead>
              <tbody>
                {permitResult.checklist_items.map((item) => (
                  <tr key={item.item_id}>
                    <td style={{ fontFamily: "var(--font-mono)", fontWeight: 600 }}>{item.item_id}</td>
                    <td>
                      <div style={{ fontWeight: 600, color: "var(--navy-900)" }}>{item.title}</div>
                      <div style={{ fontSize: "0.72rem", color: "var(--navy-500)" }}>
                        Domain: {item.category} • Required: {item.required_document_type}
                      </div>
                    </td>
                    <td>
                      <StatusBadge status={item.status} type="permit" />
                    </td>
                    <td>
                      <StatusBadge status={item.review_status} type="review" />
                    </td>
                    <td style={{ fontSize: "0.76rem" }}>
                      {item.reviewer_name ? `${item.reviewer_name} (${item.reviewer_role})` : "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
};
