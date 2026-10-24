import React from "react";
import { WorkflowOverview } from "../components/WorkflowOverview";
import { useWorkflowState } from "../hooks/useWorkflowState";
import { MainLayout } from "../layouts/MainLayout";

export const DashboardPage: React.FC = () => {
  const { health, processingState, errorMessage, refreshHealth } =
    useWorkflowState();

  return (
    <MainLayout health={health} processingState={processingState}>
      <WorkflowOverview
        health={health}
        errorMessage={errorMessage}
        onRetryHealth={() => void refreshHealth()}
      />
    </MainLayout>
  );
};
