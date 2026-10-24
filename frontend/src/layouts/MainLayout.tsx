import React from "react";
import type { HealthStatus, ProcessingState } from "../types";

interface MainLayoutProps {
  health: HealthStatus | null;
  processingState: ProcessingState;
  children: React.ReactNode;
}

export const MainLayout: React.FC<MainLayoutProps> = ({
  health,
  processingState,
  children
}) => {
  return (
    <div className="app-shell">
      <header className="app-header">
        <div className="header-brand">
          <span className="brand-badge">B2W</span>
          <div>
            <h1 className="brand-title">Bid2Work AI</h1>
            <p className="brand-subtitle">
              Tender Compliance &amp; Work-Permit Readiness Intelligence
            </p>
          </div>
        </div>
        <div className="header-status">
          <span className="status-pill">State: {processingState}</span>
          <span
            className={`status-pill ${
              health?.status === "healthy" ? "status-ok" : "status-warn"
            }`}
          >
            API: {health ? `${health.status} (v${health.version})` : "connecting..."}
          </span>
        </div>
      </header>

      <div className="disclaimer-banner" role="note">
        <strong>Decision-Support Notice:</strong> Bid2Work AI is a decision-support
        intelligence tool, not an automated legal eligibility decision-maker or an
        official permit-issuing system.
      </div>

      <main className="app-main">{children}</main>
    </div>
  );
};
