import React from "react";
import {
  FileCheck2,
  FileText,
  HardHat,
  LayoutDashboard
} from "lucide-react";
import type { HealthStatus } from "../types";

export type NavTab = "overview" | "analysis" | "permits" | "reports";

interface SidebarProps {
  activeTab: NavTab;
  onSelectTab: (tab: NavTab) => void;
  health: HealthStatus | null;
}

export const Sidebar: React.FC<SidebarProps> = ({
  activeTab,
  onSelectTab,
  health
}) => {
  const isHealthy = health?.status === "healthy" || health?.status === "ok";

  return (
    <aside className="app-sidebar" aria-label="Main Navigation">
      <div className="sidebar-header">
        <div className="brand-wrapper">
          <div className="brand-icon-box" aria-hidden="true">
            B2W
          </div>
          <div className="brand-info">
            <span className="brand-name">Bid2Work AI</span>
            <span className="brand-tagline">Tender & Permit Intel</span>
          </div>
        </div>
      </div>

      <nav className="sidebar-nav">
        <button
          type="button"
          className={`nav-item ${activeTab === "overview" ? "active" : ""}`}
          onClick={() => onSelectTab("overview")}
          aria-current={activeTab === "overview" ? "page" : undefined}
        >
          <LayoutDashboard className="nav-icon" />
          <span>Overview</span>
        </button>

        <button
          type="button"
          className={`nav-item ${activeTab === "analysis" ? "active" : ""}`}
          onClick={() => onSelectTab("analysis")}
          aria-current={activeTab === "analysis" ? "page" : undefined}
        >
          <FileCheck2 className="nav-icon" />
          <span>Tender Analysis</span>
        </button>

        <button
          type="button"
          className={`nav-item ${activeTab === "permits" ? "active" : ""}`}
          onClick={() => onSelectTab("permits")}
          aria-current={activeTab === "permits" ? "page" : undefined}
        >
          <HardHat className="nav-icon" />
          <span>Work-Permit Readiness</span>
        </button>

        <button
          type="button"
          className={`nav-item ${activeTab === "reports" ? "active" : ""}`}
          onClick={() => onSelectTab("reports")}
          aria-current={activeTab === "reports" ? "page" : undefined}
        >
          <FileText className="nav-icon" />
          <span>Compliance Reports</span>
        </button>
      </nav>

      <div className="sidebar-footer">
        <div className="sidebar-status-box">
          <div style={{ display: "flex", alignItems: "center", marginBottom: "0.25rem" }}>
            <span className={`status-indicator-dot ${isHealthy ? "" : "warn"}`} />
            <strong style={{ color: "#E2E8F0", fontSize: "0.78rem" }}>
              {isHealthy ? "Backend Connected" : "Connecting..."}
            </strong>
          </div>
          <div style={{ fontSize: "0.7rem", color: "#94A3B8" }}>
            {health?.llm_configured ? "Real LLM Mode" : "Deterministic Engine / Mock"}
          </div>
        </div>
      </div>
    </aside>
  );
};
