import React from "react";
import { PlusCircle } from "lucide-react";
import type { NavTab } from "./Sidebar";
import type { ComplianceAnalysisResult, HealthStatus } from "../types";

interface HeaderProps {
  activeTab: NavTab;
  currentAnalysis: ComplianceAnalysisResult | null;
  analyses: ComplianceAnalysisResult[];
  onSelectAnalysis: (analysisId: string) => void;
  onNewAnalysisClick: () => void;
  health: HealthStatus | null;
}

const TAB_TITLES: Record<NavTab, { title: string; subtitle: string }> = {
  overview: {
    title: "Overview Dashboard",
    subtitle: "Consolidated tender compliance health and work-permit mobilization status"
  },
  analysis: {
    title: "Tender Compliance Analysis",
    subtitle: "Evidence-driven requirement extraction and bidder document matching"
  },
  permits: {
    title: "Work-Permit Readiness",
    subtitle: "Post-award safety criteria carryover and reviewer qualification audit"
  },
  reports: {
    title: "Compliance Reports & Audit",
    subtitle: "Consolidated findings, evidence traceability, and backend CSV exports"
  }
};

export const Header: React.FC<HeaderProps> = ({
  activeTab,
  currentAnalysis,
  analyses,
  onSelectAnalysis,
  onNewAnalysisClick,
  health
}) => {
  const { title, subtitle } = TAB_TITLES[activeTab];

  return (
    <header className="app-header">
      <div className="header-title-group">
        <h1>{title}</h1>
        <p>{subtitle}</p>
      </div>

      <div className="header-controls">
        {analyses.length > 0 && (
          <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
            <label htmlFor="active-analysis-select" style={{ fontSize: "0.76rem", color: "var(--navy-600)", fontWeight: 500 }}>
              Active Tender:
            </label>
            <select
              id="active-analysis-select"
              className="select"
              style={{ width: "auto", minWidth: "190px", padding: "0.35rem 0.6rem", fontSize: "0.78rem" }}
              value={currentAnalysis?.analysis_id || ""}
              onChange={(e) => onSelectAnalysis(e.target.value)}
            >
              {analyses.map((a) => (
                <option key={a.analysis_id} value={a.analysis_id}>
                  {a.analysis_id} — {a.tender_document.filename}
                </option>
              ))}
            </select>
          </div>
        )}

        <div className="status-pill" style={{ display: "inline-flex", alignItems: "center", gap: "0.35rem" }}>
          <span
            style={{
              width: "7px",
              height: "7px",
              borderRadius: "50%",
              backgroundColor: health?.status === "healthy" ? "#10B981" : "#F59E0B"
            }}
          />
          <span style={{ fontSize: "0.74rem", color: "var(--navy-700)" }}>
            {health?.llm_configured ? "LLM Online" : "Deterministic Engine"}
          </span>
        </div>

        <button
          type="button"
          className="btn btn-primary btn-sm"
          onClick={onNewAnalysisClick}
          id="btn-new-tender-analysis"
        >
          <PlusCircle style={{ width: "15px", height: "15px" }} />
          <span>New Tender Analysis</span>
        </button>
      </div>
    </header>
  );
};
