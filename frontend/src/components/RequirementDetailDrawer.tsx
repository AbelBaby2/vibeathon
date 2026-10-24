import React, { useEffect } from "react";
import { AlertCircle, FileText, X } from "lucide-react";
import { StatusBadge } from "./StatusBadge";
import type { RequirementAssessment } from "../types";

interface RequirementDetailDrawerProps {
  assessment: RequirementAssessment | null;
  onClose: () => void;
}

export const RequirementDetailDrawer: React.FC<RequirementDetailDrawerProps> = ({
  assessment,
  onClose
}) => {
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [onClose]);

  if (!assessment) return null;

  const req = assessment.requirement;

  return (
    <div className="drawer-backdrop" onClick={onClose} role="dialog" aria-modal="true" aria-labelledby="drawer-title">
      <div className="drawer-panel" onClick={(e) => e.stopPropagation()}>
        <div className="drawer-header">
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginBottom: "0.25rem" }}>
              <span style={{ fontFamily: "var(--font-mono)", fontSize: "0.75rem", color: "var(--navy-500)", fontWeight: 600 }}>
                {req.requirement_id}
              </span>
              <StatusBadge status={req.priority} type="priority" />
              <StatusBadge status={req.category} type="category" />
              {req.requires_permit_carryover && (
                <span className="badge" style={{ backgroundColor: "#F3E8FF", color: "#6B21A8", borderColor: "#E9D5FF" }}>
                  Permit Carryover
                </span>
              )}
            </div>
            <h2 id="drawer-title" style={{ margin: 0, fontSize: "1.05rem", color: "var(--navy-900)" }}>
              {req.title}
            </h2>
          </div>
          <button
            type="button"
            className="btn btn-outline btn-icon"
            onClick={onClose}
            aria-label="Close detail panel"
          >
            <X style={{ width: "18px", height: "18px" }} />
          </button>
        </div>

        <div className="drawer-body">
          {/* Compliance Status & Rationale */}
          <div style={{ marginBottom: "1.5rem", padding: "1rem", backgroundColor: "var(--navy-50)", borderRadius: "var(--radius-md)", border: "1px solid var(--border-subtle)" }}>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "0.5rem" }}>
              <span style={{ fontSize: "0.78rem", fontWeight: 600, color: "var(--navy-700)", textTransform: "uppercase" }}>
                Evaluation Assessment
              </span>
              <StatusBadge status={assessment.status} type="compliance" />
            </div>
            <p style={{ margin: 0, fontSize: "0.85rem", color: "var(--navy-800)", lineHeight: 1.5 }}>
              {assessment.rationale}
            </p>

            {assessment.discrepancies && assessment.discrepancies.length > 0 && (
              <div style={{ marginTop: "0.75rem", borderTop: "1px dashed var(--border-medium)", paddingTop: "0.6rem" }}>
                <span style={{ fontSize: "0.75rem", fontWeight: 600, color: "#991B1B", display: "flex", alignItems: "center", gap: "0.3rem" }}>
                  <AlertCircle style={{ width: "14px", height: "14px" }} /> Identified Discrepancies
                </span>
                <ul style={{ margin: "0.3rem 0 0", paddingLeft: "1.2rem", fontSize: "0.78rem", color: "#991B1B" }}>
                  {assessment.discrepancies.map((d, i) => (
                    <li key={i}>{d}</li>
                  ))}
                </ul>
              </div>
            )}

            {assessment.recommended_action && (
              <div style={{ marginTop: "0.75rem", padding: "0.6rem 0.75rem", backgroundColor: "#EFF6FF", borderRadius: "var(--radius-sm)", border: "1px solid #BFDBFE", fontSize: "0.78rem", color: "#1E40AF" }}>
                <strong>Recommendation:</strong> {assessment.recommended_action}
              </div>
            )}
          </div>

          {/* Tender Requirement Description & Source */}
          <div style={{ marginBottom: "1.5rem" }}>
            <h3 style={{ fontSize: "0.85rem", fontWeight: 600, color: "var(--navy-900)", marginBottom: "0.5rem" }}>
              Tender Requirement Specification
            </h3>
            <p style={{ fontSize: "0.82rem", color: "var(--navy-800)", margin: "0 0 0.75rem", lineHeight: 1.5 }}>
              {req.description}
            </p>
            {req.threshold_or_criteria && (
              <div style={{ fontSize: "0.78rem", color: "var(--navy-600)", marginBottom: "0.75rem" }}>
                <strong>Target Criteria / Threshold:</strong> {req.threshold_or_criteria}
              </div>
            )}

            {/* Tender Source Excerpt */}
            <div style={{ padding: "0.75rem 0.85rem", backgroundColor: "#FFFFFF", border: "1px solid var(--border-subtle)", borderRadius: "var(--radius-md)", fontSize: "0.78rem" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "0.4rem", color: "var(--navy-500)", marginBottom: "0.35rem", fontSize: "0.74rem" }}>
                <FileText style={{ width: "13px", height: "13px" }} />
                <span>Source: <strong>{req.source.filename}</strong> (Page {req.source.page_number})</span>
              </div>
              <blockquote style={{ margin: 0, paddingLeft: "0.75rem", borderLeft: "2px solid var(--teal-600)", color: "var(--navy-700)", fontStyle: "italic", fontSize: "0.8rem" }}>
                "{req.source.excerpt}"
              </blockquote>
            </div>
          </div>

          {/* Matched Bidder Supporting Evidence */}
          <div>
            <h3 style={{ fontSize: "0.85rem", fontWeight: 600, color: "var(--navy-900)", marginBottom: "0.5rem", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
              <span>Matched Bidder Supporting Evidence</span>
              <span style={{ fontSize: "0.74rem", fontWeight: 500, color: "var(--navy-500)" }}>
                {assessment.matched_evidence.length} found
              </span>
            </h3>

            {assessment.matched_evidence.length === 0 ? (
              <div style={{ padding: "1.25rem", textAlign: "center", backgroundColor: "var(--navy-50)", border: "1px dashed var(--border-medium)", borderRadius: "var(--radius-md)", color: "var(--navy-500)", fontSize: "0.8rem" }}>
                No verifiable evidence was located in uploaded bidder supporting files.
              </div>
            ) : (
              <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
                {assessment.matched_evidence.map((ev, idx) => (
                  <div
                    key={ev.evidence_id || idx}
                    style={{
                      padding: "0.85rem",
                      backgroundColor: "#FFFFFF",
                      border: "1px solid var(--border-subtle)",
                      borderRadius: "var(--radius-md)",
                      fontSize: "0.8rem"
                    }}
                  >
                    <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "0.4rem" }}>
                      <span style={{ fontWeight: 600, color: "var(--navy-800)" }}>
                        {ev.filename}
                      </span>
                      <span className="badge" style={{ backgroundColor: "#F0FDFA", color: "#0F766E", borderColor: "#99F6E4", fontSize: "0.7rem" }}>
                        Page {ev.page_number} • Match Confidence: {Math.round(ev.confidence * 100)}%
                      </span>
                    </div>

                    <blockquote style={{ margin: "0.4rem 0", paddingLeft: "0.65rem", borderLeft: "2px solid var(--border-medium)", color: "var(--navy-700)", fontStyle: "italic", fontSize: "0.78rem" }}>
                      "{ev.excerpt}"
                    </blockquote>

                    {(ev.extracted_value || ev.valid_until) && (
                      <div style={{ display: "flex", gap: "1rem", marginTop: "0.5rem", fontSize: "0.74rem", color: "var(--navy-600)" }}>
                        {ev.extracted_value && (
                          <span>Extracted Value: <strong>{ev.extracted_value}</strong></span>
                        )}
                        {ev.valid_until && (
                          <span>Valid Until: <strong>{ev.valid_until}</strong></span>
                        )}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
