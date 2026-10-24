import React from "react";
import { AlertCircle } from "lucide-react";
import { Header } from "../components/Header";
import { Sidebar, type NavTab } from "../components/Sidebar";
import type { ComplianceAnalysisResult, HealthStatus } from "../types";

interface MainLayoutProps {
  activeTab: NavTab;
  onSelectTab: (tab: NavTab) => void;
  currentAnalysis: ComplianceAnalysisResult | null;
  analyses: ComplianceAnalysisResult[];
  onSelectAnalysis: (analysisId: string) => void;
  onNewAnalysisClick: () => void;
  health: HealthStatus | null;
  children: React.ReactNode;
}

export const MainLayout: React.FC<MainLayoutProps> = ({
  activeTab,
  onSelectTab,
  currentAnalysis,
  analyses,
  onSelectAnalysis,
  onNewAnalysisClick,
  health,
  children
}) => {
  return (
    <div className="app-shell">
      <Sidebar
        activeTab={activeTab}
        onSelectTab={onSelectTab}
        health={health}
      />

      <div className="app-content">
        <Header
          activeTab={activeTab}
          currentAnalysis={currentAnalysis}
          analyses={analyses}
          onSelectAnalysis={onSelectAnalysis}
          onNewAnalysisClick={onNewAnalysisClick}
          health={health}
        />

        <div className="disclaimer-strip" role="note">
          <AlertCircle style={{ width: "14px", height: "14px", flexShrink: 0 }} />
          <span>
            <strong>Decision-Support Notice:</strong> Bid2Work AI assists human MSME bidders and compliance auditors. It does not execute automated legal eligibility determinations, formal tender contract adjudication, or legal work-permit issuance.
          </span>
        </div>

        <main id="main-content" tabIndex={-1}>
          {children}
        </main>
      </div>
    </div>
  );
};
