import React from "react";
import { useWorkflowState } from "../hooks/useWorkflowState";
import { MainLayout } from "../layouts/MainLayout";
import { ComplianceReportsPage } from "./ComplianceReportsPage";
import { OverviewPage } from "./OverviewPage";
import { PermitReadinessPage } from "./PermitReadinessPage";
import { TenderAnalysisPage } from "./TenderAnalysisPage";

export const DashboardPage: React.FC = () => {
  const {
    activeTab,
    setActiveTab,
    health,
    analyses,
    currentAnalysis,
    permitResult,
    auditEvents,
    isAnalyzing,
    errorMessage,
    selectAnalysis,
    runAnalysis,
    simulateAward,
    updateChecklistItem
  } = useWorkflowState();

  return (
    <MainLayout
      activeTab={activeTab}
      onSelectTab={setActiveTab}
      currentAnalysis={currentAnalysis}
      analyses={analyses}
      onSelectAnalysis={(id) => void selectAnalysis(id)}
      onNewAnalysisClick={() => setActiveTab("analysis")}
      health={health}
    >
      {activeTab === "overview" && (
        <OverviewPage
          currentAnalysis={currentAnalysis}
          analyses={analyses}
          permitResult={permitResult}
          auditEvents={auditEvents}
          onSelectAnalysis={(id) => void selectAnalysis(id)}
          onNavigateToTab={setActiveTab}
        />
      )}

      {activeTab === "analysis" && (
        <TenderAnalysisPage
          currentAnalysis={currentAnalysis}
          onAnalyze={runAnalysis}
          isAnalyzing={isAnalyzing}
          errorMessage={errorMessage}
        />
      )}

      {activeTab === "permits" && (
        <PermitReadinessPage
          currentAnalysis={currentAnalysis}
          permitResult={permitResult}
          onSimulateAward={simulateAward}
          onItemUpdated={updateChecklistItem}
          onNavigateToAnalysis={() => setActiveTab("analysis")}
        />
      )}

      {activeTab === "reports" && (
        <ComplianceReportsPage
          currentAnalysis={currentAnalysis}
          analyses={analyses}
          permitResult={permitResult}
          onSelectAnalysis={(id) => void selectAnalysis(id)}
          onNavigateToAnalysis={() => setActiveTab("analysis")}
        />
      )}
    </MainLayout>
  );
};
