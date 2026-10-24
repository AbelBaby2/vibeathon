import React from "react";
import {
  AlertTriangle,
  ArrowRight,
  FileCheck2,
  FileText,
  HardHat,
  History,
  PlusCircle,
  ShieldCheck
} from "lucide-react";
import type { AuditEvent, ComplianceAnalysisResult, PermitReadinessResult } from "../types";

interface OverviewPageProps {
  currentAnalysis: ComplianceAnalysisResult | null;
  analyses: ComplianceAnalysisResult[];
  permitResult: PermitReadinessResult | null;
  auditEvents: AuditEvent[];
  onSelectAnalysis: (analysisId: string) => void;
  onNavigateToTab: (tab: "analysis" | "permits" | "reports") => void;
}

export const OverviewPage: React.FC<OverviewPageProps> = ({
  currentAnalysis,
  analyses,
  permitResult,
  auditEvents,
  onSelectAnalysis,
  onNavigateToTab
}) => {
  if (!currentAnalysis) {
    return (
      <div className="page-container">
        <div className="empty-state">
          <FileCheck2 className="empty-state-icon" style={{ width: "48px", height: "48px", color: "var(--teal-600)" }} />
          <h2 className="empty-state-title">No Tender Analysis Found</h2>
          <p className="empty-state-text">
            Bid2Work AI provides automated compliance extraction, evidence tracing, and post-award work-permit verification. Upload your first tender PDF to begin.
          </p>
          <button
            type="button"
            className="btn btn-primary"
            onClick={() => onNavigateToTab("analysis")}
            id="btn-overview-start-analysis"
          >
            <PlusCircle style={{ width: "16px", height: "16px" }} />
            <span>New Tender Analysis</span>
          </button>
        </div>
      </div>
    );
  }

  const summary = currentAnalysis.summary;

  return (
    <div className="page-container">
      {/* Metric Cards Row */}
      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-card-label">Total Requirements</div>
          <div className="stat-card-value">{summary.total_requirements}</div>
          <div className="stat-card-detail">
            {summary.safety_requirements_count} safety / permit carryover
          </div>
        </div>

        <div className="stat-card" style={{ borderLeft: "3px solid #166534" }}>
          <div className="stat-card-label" style={{ color: "#166534" }}>Evidence Found</div>
          <div className="stat-card-value" style={{ color: "#166534" }}>
            {summary.evidence_found_count}
          </div>
          <div className="stat-card-detail">
            {summary.overall_readiness_score.toFixed(0)}% tender compliance score
          </div>
        </div>

        <div className="stat-card" style={{ borderLeft: "3px solid #991B1B" }}>
          <div className="stat-card-label" style={{ color: "#991B1B" }}>Missing Evidence</div>
          <div className="stat-card-value" style={{ color: "#991B1B" }}>
            {summary.missing_count}
          </div>
          <div className="stat-card-detail">
            {summary.mandatory_gap_count} critical mandatory gaps
          </div>
        </div>

        <div className="stat-card" style={{ borderLeft: "3px solid #92400E" }}>
          <div className="stat-card-label" style={{ color: "#92400E" }}>Conflicting Evidence</div>
          <div className="stat-card-value" style={{ color: "#92400E" }}>
            {summary.conflicting_count}
          </div>
          <div className="stat-card-detail">Discrepant bidder values</div>
        </div>

        <div className="stat-card" style={{ borderLeft: "3px solid #334155" }}>
          <div className="stat-card-label" style={{ color: "#334155" }}>Needs Review</div>
          <div className="stat-card-value" style={{ color: "#334155" }}>
            {summary.needs_review_count}
          </div>
          <div className="stat-card-detail">Requires reviewer verification</div>
        </div>
      </div>

      {/* Two Column Layout: Tender Summary & Work-Permit Readiness */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(360px, 1fr))", gap: "1.5rem", marginBottom: "1.75rem" }}>
        {/* Active Analysis Info Card */}
        <div className="card">
          <div className="card-header">
            <div>
              <h2 className="card-title">
                <FileText style={{ width: "16px", height: "16px", color: "var(--teal-600)" }} />
                <span>Active Tender Document</span>
              </h2>
              <p className="card-description">
                Analysis session {currentAnalysis.analysis_id}
              </p>
            </div>
            <button
              type="button"
              className="btn btn-outline btn-sm"
              onClick={() => onNavigateToTab("analysis")}
            >
              <span>View Requirements</span>
              <ArrowRight style={{ width: "13px", height: "13px" }} />
            </button>
          </div>

          <div style={{ fontSize: "0.82rem", display: "grid", gap: "0.6rem" }}>
            <div style={{ display: "flex", justifyContent: "space-between" }}>
              <span style={{ color: "var(--navy-600)" }}>Tender File:</span>
              <strong style={{ color: "var(--navy-900)" }}>{currentAnalysis.tender_document.filename}</strong>
            </div>
            <div style={{ display: "flex", justifyContent: "space-between" }}>
              <span style={{ color: "var(--navy-600)" }}>Page Count:</span>
              <span>{currentAnalysis.tender_document.page_count} pages</span>
            </div>
            <div style={{ display: "flex", justifyContent: "space-between" }}>
              <span style={{ color: "var(--navy-600)" }}>Bidder Documents:</span>
              <span>{currentAnalysis.bidder_documents.length} supporting files</span>
            </div>
            <div style={{ display: "flex", justifyContent: "space-between" }}>
              <span style={{ color: "var(--navy-600)" }}>Analyzed On:</span>
              <span>{new Date(currentAnalysis.created_at).toLocaleString()}</span>
            </div>

            {/* Category breakdown pills */}
            <div style={{ marginTop: "0.5rem", paddingTop: "0.75rem", borderTop: "1px solid var(--border-subtle)" }}>
              <div style={{ fontSize: "0.72rem", color: "var(--navy-500)", textTransform: "uppercase", marginBottom: "0.4rem", fontWeight: 600 }}>
                Requirement Categories:
              </div>
              <div style={{ display: "flex", flexWrap: "wrap", gap: "0.4rem" }}>
                {Object.entries(summary.by_category || {}).map(([cat, count]) => (
                  <span key={cat} className="badge badge-category">
                    {cat}: {count}
                  </span>
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* Work-Permit Readiness Summary Card */}
        <div className="card">
          <div className="card-header">
            <div>
              <h2 className="card-title">
                <HardHat style={{ width: "16px", height: "16px", color: "var(--teal-600)" }} />
                <span>Work-Permit Readiness</span>
              </h2>
              <p className="card-description">
                {permitResult ? `Contract Ref: ${permitResult.contract_reference}` : "Pre-award transition state"}
              </p>
            </div>
            <button
              type="button"
              className="btn btn-outline btn-sm"
              onClick={() => onNavigateToTab("permits")}
            >
              <span>{permitResult ? "View Checklist" : "Simulate Award"}</span>
              <ArrowRight style={{ width: "13px", height: "13px" }} />
            </button>
          </div>

          {permitResult ? (
            <div style={{ fontSize: "0.82rem" }}>
              <div style={{ marginBottom: "0.75rem" }}>
                <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "0.3rem" }}>
                  <span style={{ color: "var(--navy-600)" }}>Mobilization Readiness:</span>
                  <strong style={{ color: "var(--teal-800)" }}>
                    {permitResult.summary.readiness_percentage.toFixed(0)}% Verified
                  </strong>
                </div>
                <div style={{ width: "100%", height: "8px", backgroundColor: "var(--navy-100)", borderRadius: "var(--radius-pill)", overflow: "hidden" }}>
                  <div
                    style={{
                      width: `${permitResult.summary.readiness_percentage}%`,
                      height: "100%",
                      backgroundColor: "var(--teal-600)",
                      borderRadius: "var(--radius-pill)"
                    }}
                  />
                </div>
              </div>

              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0.5rem", marginBottom: "0.75rem", fontSize: "0.76rem" }}>
                <div style={{ padding: "0.5rem", backgroundColor: "var(--status-found-bg)", borderRadius: "var(--radius-sm)", color: "var(--status-found-text)" }}>
                  Verified: <strong>{permitResult.summary.verified_count}</strong>
                </div>
                <div style={{ padding: "0.5rem", backgroundColor: "var(--status-review-bg)", borderRadius: "var(--radius-sm)", color: "var(--status-review-text)" }}>
                  Pending Evidence: <strong>{permitResult.summary.pending_count}</strong>
                </div>
                <div style={{ padding: "0.5rem", backgroundColor: "var(--status-missing-bg)", borderRadius: "var(--radius-sm)", color: "var(--status-missing-text)" }}>
                  Expired Items: <strong>{permitResult.summary.expired_count}</strong>
                </div>
                <div style={{ padding: "0.5rem", backgroundColor: "#FEF3C7", borderRadius: "var(--radius-sm)", color: "#92400E" }}>
                  Blocking Conditions: <strong>{permitResult.summary.blocking_conditions_count}</strong>
                </div>
              </div>

              {permitResult.summary.blocking_conditions_count > 0 && (
                <div className="alert alert-warning" style={{ margin: 0, padding: "0.5rem 0.75rem", fontSize: "0.74rem" }}>
                  <AlertTriangle style={{ width: "14px", height: "14px", flexShrink: 0 }} />
                  <span>{permitResult.summary.blocking_conditions_count} item(s) block operational site mobilization.</span>
                </div>
              )}
            </div>
          ) : (
            <div style={{ textAlign: "center", padding: "1.25rem 0.5rem", color: "var(--navy-600)", fontSize: "0.8rem" }}>
              <HardHat style={{ width: "28px", height: "28px", color: "var(--navy-400)", margin: "0 auto 0.5rem" }} />
              <p style={{ margin: "0 0 0.75rem", lineHeight: 1.4 }}>
                Contract award simulation has not been triggered yet. Simulate award to automatically generate your post-award HSE and permit checklist.
              </p>
              <button
                type="button"
                className="btn btn-secondary btn-sm"
                onClick={() => onNavigateToTab("permits")}
                id="btn-overview-trigger-award"
              >
                Simulate Contract Award Now
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Recent Analyses List */}
      <div className="card" style={{ marginBottom: "1.75rem" }}>
        <div className="card-header">
          <div>
            <h2 className="card-title">
              <History style={{ width: "16px", height: "16px", color: "var(--teal-600)" }} />
              <span>Saved Compliance Intelligence Analyses</span>
            </h2>
            <p className="card-description">
              Select any past tender run to inspect evidence traces and reports
            </p>
          </div>
          <button
            type="button"
            className="btn btn-primary btn-sm"
            onClick={() => onNavigateToTab("analysis")}
          >
            <PlusCircle style={{ width: "14px", height: "14px" }} />
            <span>New Analysis</span>
          </button>
        </div>

        <div className="table-container">
          <table className="data-table">
            <thead>
              <tr>
                <th>Analysis ID</th>
                <th>Tender Filename</th>
                <th>Created At</th>
                <th>Requirements</th>
                <th>Readiness Score</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {analyses.map((a) => {
                const isSelected = a.analysis_id === currentAnalysis.analysis_id;
                return (
                  <tr key={a.analysis_id} style={{ backgroundColor: isSelected ? "var(--teal-50)" : undefined }}>
                    <td style={{ fontFamily: "var(--font-mono)", fontWeight: 600 }}>
                      {a.analysis_id}
                      {isSelected && (
                        <span className="badge" style={{ marginLeft: "0.5rem", backgroundColor: "var(--teal-600)", color: "#FFFFFF" }}>
                          Active
                        </span>
                      )}
                    </td>
                    <td style={{ fontWeight: 500 }}>{a.tender_document.filename}</td>
                    <td style={{ color: "var(--navy-600)", fontSize: "0.78rem" }}>
                      {new Date(a.created_at).toLocaleDateString()}
                    </td>
                    <td>{a.summary.total_requirements} items</td>
                    <td>
                      <span style={{ fontWeight: 600, color: a.summary.overall_readiness_score > 60 ? "#166534" : "#991B1B" }}>
                        {a.summary.overall_readiness_score.toFixed(0)}%
                      </span>
                    </td>
                    <td>
                      <button
                        type="button"
                        className="btn btn-outline btn-sm"
                        onClick={() => {
                          onSelectAnalysis(a.analysis_id);
                          onNavigateToTab("analysis");
                        }}
                      >
                        Inspect
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* Audit Trail Section */}
      {auditEvents.length > 0 && (
        <div className="card">
          <div className="card-header">
            <div>
              <h2 className="card-title">
                <ShieldCheck style={{ width: "16px", height: "16px", color: "var(--teal-600)" }} />
                <span>Immutable SQLite Audit Trail</span>
              </h2>
              <p className="card-description">
                Audited regulatory and human review verification actions
              </p>
            </div>
          </div>

          <div className="table-container">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Timestamp</th>
                  <th>Actor</th>
                  <th>Event Type</th>
                  <th>Summary</th>
                </tr>
              </thead>
              <tbody>
                {auditEvents.slice(0, 8).map((ev) => (
                  <tr key={ev.event_id}>
                    <td style={{ fontSize: "0.75rem", color: "var(--navy-600)", whiteSpace: "nowrap" }}>
                      {new Date(ev.created_at).toLocaleTimeString()}
                    </td>
                    <td>
                      <span className="badge" style={{ backgroundColor: ev.actor === "USER" ? "#EFF6FF" : "var(--navy-100)", color: ev.actor === "USER" ? "#1E40AF" : "var(--navy-700)" }}>
                        {ev.actor}
                      </span>
                    </td>
                    <td style={{ fontFamily: "var(--font-mono)", fontSize: "0.75rem", fontWeight: 600 }}>
                      {ev.event_type}
                    </td>
                    <td style={{ fontSize: "0.78rem" }}>{ev.summary}</td>
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
