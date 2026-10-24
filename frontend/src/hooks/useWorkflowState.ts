import { useCallback, useEffect, useState } from "react";
import { bid2WorkApi } from "../services/apiClient";
import type {
  AuditEvent,
  ComplianceAnalysisResult,
  HealthStatus,
  PermitReadinessResult,
  ProcessingState
} from "../types";

export interface WorkflowState {
  health: HealthStatus | null;
  processingState: ProcessingState;
  errorMessage: string | null;
  complianceResult: ComplianceAnalysisResult | null;
  permitResult: PermitReadinessResult | null;
  auditEvents: AuditEvent[];
  refreshHealth: () => Promise<void>;
}

export function useWorkflowState(): WorkflowState {
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [processingState, setProcessingState] =
    useState<ProcessingState>("IDLE");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [complianceResult] = useState<ComplianceAnalysisResult | null>(null);
  const [permitResult] = useState<PermitReadinessResult | null>(null);
  const [auditEvents] = useState<AuditEvent[]>([]);

  const refreshHealth = useCallback(async () => {
    try {
      const response = await bid2WorkApi.getHealth();
      if (response.data) {
        setHealth(response.data);
      }
      setErrorMessage(null);
    } catch (err) {
      setProcessingState("IDLE");
      setErrorMessage(
        err instanceof Error
          ? err.message
          : "Backend health check unreachable."
      );
    }
  }, []);

  useEffect(() => {
    void refreshHealth();
  }, [refreshHealth]);

  return {
    health,
    processingState,
    errorMessage,
    complianceResult,
    permitResult,
    auditEvents,
    refreshHealth
  };
}
