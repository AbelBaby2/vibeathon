import React, { useMemo, useState } from "react";
import {
  Eye,
  FileCheck2,
  FileText,
  Filter,
  Search,
  Upload
} from "lucide-react";
import { FileUploadSection } from "../components/FileUploadSection";
import { RequirementDetailDrawer } from "../components/RequirementDetailDrawer";
import { StatusBadge } from "../components/StatusBadge";
import type {
  ComplianceAnalysisResult,
  RequirementAssessment
} from "../types";

interface TenderAnalysisPageProps {
  currentAnalysis: ComplianceAnalysisResult | null;
  onAnalyze: (tenderFile: File, bidderFiles: File[]) => Promise<void>;
  isAnalyzing: boolean;
  errorMessage: string | null;
}

export const TenderAnalysisPage: React.FC<TenderAnalysisPageProps> = ({
  currentAnalysis,
  onAnalyze,
  isAnalyzing,
  errorMessage
}) => {
  const [selectedAssessment, setSelectedAssessment] =
    useState<RequirementAssessment | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>("ALL");
  const [categoryFilter, setCategoryFilter] = useState<string>("ALL");
  const [showUploadForm, setShowUploadForm] = useState(!currentAnalysis);

  const assessments = currentAnalysis?.assessments || [];

  const filteredAssessments = useMemo(() => {
    return assessments.filter((a) => {
      // Status filter
      if (statusFilter !== "ALL" && a.status !== statusFilter) {
        return false;
      }
      // Category filter
      if (categoryFilter !== "ALL" && a.requirement.category !== categoryFilter) {
        return false;
      }
      // Text search
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase();
        const matchesId = a.requirement_id.toLowerCase().includes(q);
        const matchesTitle = a.requirement.title.toLowerCase().includes(q);
        const matchesDesc = a.requirement.description.toLowerCase().includes(q);
        const matchesExcerpt = a.matched_evidence.some((e) =>
          e.excerpt.toLowerCase().includes(q) || e.filename.toLowerCase().includes(q)
        );
        const matchesSource = a.requirement.source.excerpt.toLowerCase().includes(q);
        return matchesId || matchesTitle || matchesDesc || matchesExcerpt || matchesSource;
      }
      return true;
    });
  }, [assessments, statusFilter, categoryFilter, searchQuery]);

  return (
    <div className="page-container">
      {/* Upload Zone (collapsible or expanded) */}
      <div style={{ marginBottom: "1.5rem" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.75rem" }}>
          <div>
            <h2 style={{ margin: 0, fontSize: "1.1rem", color: "var(--navy-900)" }}>
              Tender Document Upload & Execution
            </h2>
            <p style={{ margin: "0.2rem 0 0", fontSize: "0.78rem", color: "var(--navy-600)" }}>
              Upload an industrial tender PDF and bidder supporting files to extract requirements and evaluate compliance.
            </p>
          </div>
          {currentAnalysis && (
            <button
              type="button"
              className="btn btn-secondary btn-sm"
              onClick={() => setShowUploadForm(!showUploadForm)}
            >
              <Upload style={{ width: "13px", height: "13px" }} />
              <span>{showUploadForm ? "Hide Upload Form" : "Upload Another Tender"}</span>
            </button>
          )}
        </div>

        {(showUploadForm || !currentAnalysis) && (
          <FileUploadSection
            onAnalyze={async (tender, bidders) => {
              await onAnalyze(tender, bidders);
              setShowUploadForm(false);
            }}
            isAnalyzing={isAnalyzing}
            errorMessage={errorMessage}
          />
        )}
      </div>

      {/* Analysis Results View */}
      {currentAnalysis ? (
        <div className="card">
          <div className="card-header">
            <div>
              <div style={{ display: "flex", alignItems: "center", gap: "0.6rem", marginBottom: "0.3rem" }}>
                <span style={{ fontFamily: "var(--font-mono)", fontSize: "0.78rem", fontWeight: 700, color: "var(--teal-800)" }}>
                  {currentAnalysis.analysis_id}
                </span>
                <span className="badge" style={{ backgroundColor: "var(--navy-100)", color: "var(--navy-700)" }}>
                  {currentAnalysis.tender_document.filename}
                </span>
                <span className="badge" style={{ backgroundColor: "#F0FDF4", color: "#166534", borderColor: "#BBF7D0" }}>
                  Score: {currentAnalysis.summary.overall_readiness_score.toFixed(0)}%
                </span>
              </div>
              <h2 className="card-title">
                <FileCheck2 style={{ width: "18px", height: "18px", color: "var(--teal-600)" }} />
                <span>Extracted Requirements & Evidence Compliance Findings</span>
              </h2>
            </div>

            <div style={{ display: "flex", gap: "0.5rem" }}>
              <span className="badge badge-status-found">
                {currentAnalysis.summary.evidence_found_count} Found
              </span>
              <span className="badge badge-status-missing">
                {currentAnalysis.summary.missing_count} Missing
              </span>
              <span className="badge badge-status-conflicting">
                {currentAnalysis.summary.conflicting_count} Conflict
              </span>
              <span className="badge badge-status-review">
                {currentAnalysis.summary.needs_review_count} Review
              </span>
            </div>
          </div>

          {/* Search & Filter Toolbar */}
          <div style={{ display: "grid", gridTemplateColumns: "1fr auto auto", gap: "0.75rem", marginBottom: "1.25rem", alignItems: "center" }}>
            <div style={{ position: "relative" }}>
              <Search
                style={{
                  position: "absolute",
                  left: "0.75rem",
                  top: "50%",
                  transform: "translateY(-50%)",
                  width: "15px",
                  height: "15px",
                  color: "var(--navy-400)"
                }}
              />
              <input
                type="text"
                className="input"
                style={{ paddingLeft: "2.25rem" }}
                placeholder="Search clause text, criteria, ID, or bidder evidence..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                id="search-requirements-input"
              />
            </div>

            <div style={{ display: "flex", alignItems: "center", gap: "0.4rem" }}>
              <Filter style={{ width: "14px", height: "14px", color: "var(--navy-500)" }} />
              <select
                className="select"
                style={{ width: "auto" }}
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                aria-label="Filter by Compliance Status"
                id="filter-compliance-status"
              >
                <option value="ALL">All Compliance States</option>
                <option value="Evidence Found">Evidence Found</option>
                <option value="Missing">Missing</option>
                <option value="Conflicting">Conflicting</option>
                <option value="Needs Review">Needs Review</option>
              </select>
            </div>

            <div>
              <select
                className="select"
                style={{ width: "auto" }}
                value={categoryFilter}
                onChange={(e) => setCategoryFilter(e.target.value)}
                aria-label="Filter by Requirement Category"
                id="filter-requirement-category"
              >
                <option value="ALL">All Categories</option>
                <option value="ELIGIBILITY">Eligibility</option>
                <option value="EXPERIENCE">Experience</option>
                <option value="FINANCIAL">Financial</option>
                <option value="CERTIFICATION">Certification</option>
                <option value="DEADLINE">Deadline</option>
                <option value="SAFETY">Safety</option>
                <option value="OTHER">Other</option>
              </select>
            </div>
          </div>

          {/* Requirements Table */}
          <div className="table-container">
            <table className="data-table" aria-label="Tender Requirements Compliance Table">
              <thead>
                <tr>
                  <th style={{ width: "110px" }}>ID & Priority</th>
                  <th style={{ width: "110px" }}>Category</th>
                  <th>Requirement Specification</th>
                  <th style={{ width: "130px" }}>Status</th>
                  <th>Supporting Evidence Trace</th>
                  <th style={{ width: "160px" }}>Tender Source</th>
                  <th style={{ width: "90px", textAlign: "right" }}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {filteredAssessments.length === 0 ? (
                  <tr>
                    <td colSpan={7} style={{ textAlign: "center", padding: "2.5rem 1rem", color: "var(--navy-500)" }}>
                      No tender requirements match the selected search or filter criteria.
                    </td>
                  </tr>
                ) : (
                  filteredAssessments.map((assessment) => {
                    const req = assessment.requirement;
                    const firstEvidence = assessment.matched_evidence[0];

                    return (
                      <tr
                        key={assessment.requirement_id}
                        onClick={() => setSelectedAssessment(assessment)}
                        style={{ cursor: "pointer" }}
                      >
                        <td>
                          <div style={{ fontFamily: "var(--font-mono)", fontWeight: 600, fontSize: "0.78rem" }}>
                            {req.requirement_id}
                          </div>
                          <div style={{ marginTop: "0.2rem" }}>
                            <StatusBadge status={req.priority} type="priority" />
                          </div>
                        </td>

                        <td>
                          <StatusBadge status={req.category} type="category" />
                          {req.requires_permit_carryover && (
                            <div style={{ marginTop: "0.25rem" }}>
                              <span className="badge" style={{ backgroundColor: "#F3E8FF", color: "#6B21A8", borderColor: "#E9D5FF", fontSize: "0.68rem" }}>
                                Carryover
                              </span>
                            </div>
                          )}
                        </td>

                        <td>
                          <div style={{ fontWeight: 600, color: "var(--navy-900)", marginBottom: "0.2rem" }}>
                            {req.title}
                          </div>
                          <div style={{ color: "var(--navy-700)", fontSize: "0.78rem", lineHeight: 1.4 }}>
                            {req.description}
                          </div>
                          {req.threshold_or_criteria && (
                            <div style={{ marginTop: "0.25rem", fontSize: "0.72rem", color: "var(--navy-500)" }}>
                              Threshold: <strong>{req.threshold_or_criteria}</strong>
                            </div>
                          )}
                        </td>

                        <td>
                          <StatusBadge status={assessment.status} type="compliance" />
                        </td>

                        <td>
                          {firstEvidence ? (
                            <div>
                              <div style={{ fontWeight: 500, fontSize: "0.76rem", color: "var(--navy-800)" }}>
                                {firstEvidence.filename} (p. {firstEvidence.page_number})
                              </div>
                              <blockquote style={{ margin: "0.2rem 0 0", paddingLeft: "0.5rem", borderLeft: "2px solid var(--border-medium)", color: "var(--navy-600)", fontStyle: "italic", fontSize: "0.74rem" }}>
                                "{firstEvidence.excerpt.slice(0, 110)}
                                {firstEvidence.excerpt.length > 110 ? "..." : ""}"
                              </blockquote>
                              {assessment.matched_evidence.length > 1 && (
                                <span style={{ fontSize: "0.68rem", color: "var(--teal-700)", fontWeight: 600 }}>
                                  +{assessment.matched_evidence.length - 1} additional proof file(s)
                                </span>
                              )}
                            </div>
                          ) : (
                            <span style={{ color: "var(--navy-400)", fontSize: "0.76rem", fontStyle: "italic" }}>
                              No bidder evidence matched
                            </span>
                          )}
                        </td>

                        <td>
                          <div style={{ fontSize: "0.75rem", color: "var(--navy-700)" }}>
                            <strong>{req.source.filename}</strong>
                          </div>
                          <div style={{ fontSize: "0.72rem", color: "var(--navy-500)" }}>
                            Page {req.source.page_number}
                          </div>
                        </td>

                        <td style={{ textAlign: "right" }}>
                          <button
                            type="button"
                            className="btn btn-outline btn-sm"
                            onClick={(e) => {
                              e.stopPropagation();
                              setSelectedAssessment(assessment);
                            }}
                            title="Inspect complete evidence trace and rationale"
                          >
                            <Eye style={{ width: "13px", height: "13px" }} />
                            <span>Details</span>
                          </button>
                        </td>
                      </tr>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>
        </div>
      ) : (
        <div className="empty-state">
          <FileText className="empty-state-icon" style={{ width: "44px", height: "44px", color: "var(--navy-400)" }} />
          <h2 className="empty-state-title">No Tender Loaded</h2>
          <p className="empty-state-text">
            Upload your tender PDF and bidder supporting documents above to execute compliance extraction and view the clause trace table.
          </p>
        </div>
      )}

      {/* Slide-out Evidence Detail Drawer */}
      <RequirementDetailDrawer
        assessment={selectedAssessment}
        onClose={() => setSelectedAssessment(null)}
      />
    </div>
  );
};
