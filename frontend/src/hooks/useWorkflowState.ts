import { useCallback, useEffect, useState } from "react";
import { bid2WorkApi } from "../services/apiClient";
import type { NavTab } from "../components/Sidebar";
import type {
  AuditEvent,
  AwardRequestPayload,
  ComplianceAnalysisResult,
  HealthStatus,
  PermitChecklistItem,
  PermitReadinessResult
} from "../types";

export interface WorkflowState {
  activeTab: NavTab;
  setActiveTab: (tab: NavTab) => void;
  health: HealthStatus | null;
  analyses: ComplianceAnalysisResult[];
  currentAnalysis: ComplianceAnalysisResult | null;
  permitResult: PermitReadinessResult | null;
  auditEvents: AuditEvent[];
  isAnalyzing: boolean;
  errorMessage: string | null;
  refreshHealth: () => Promise<void>;
  selectAnalysis: (analysisId: string) => Promise<void>;
  runAnalysis: (tenderFile: File, bidderFiles: File[]) => Promise<void>;
  simulateAward: (payload: AwardRequestPayload) => Promise<void>;
  updateChecklistItem: (updatedItem: PermitChecklistItem) => void;
}

export function useWorkflowState(): WorkflowState {
  const [activeTab, setActiveTab] = useState<NavTab>("overview");
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [analyses, setAnalyses] = useState<ComplianceAnalysisResult[]>([]);
  const [currentAnalysis, setCurrentAnalysis] =
    useState<ComplianceAnalysisResult | null>(null);
  const [permitResult, setPermitResult] =
    useState<PermitReadinessResult | null>(null);
  const [auditEvents, setAuditEvents] = useState<AuditEvent[]>([]);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Load audit trail for a specific analysis
  const loadAuditEvents = useCallback(async (analysisId?: string) => {
    try {
      const response = await bid2WorkApi.listAuditEvents(analysisId, 50);
      if (response.data) {
        setAuditEvents(response.data.events);
      }
    } catch {
      // Non-critical background fetch
    }
  }, []);

  // Load permit readiness for an analysis
  const loadPermitReadiness = useCallback(async (analysisId: string) => {
    try {
      const response = await bid2WorkApi.getPermitReadiness(analysisId, false);
      setPermitResult(response.data || null);
    } catch {
      setPermitResult(null);
    }
  }, []);

  // Select an analysis
  const selectAnalysis = useCallback(
    async (analysisId: string) => {
      setErrorMessage(null);
      const found = analyses.find((a) => a.analysis_id === analysisId);
      if (found) {
        setCurrentAnalysis(found);
        await Promise.all([
          loadPermitReadiness(analysisId),
          loadAuditEvents(analysisId)
        ]);
      } else {
        try {
          const resp = await bid2WorkApi.getAnalysis(analysisId);
          if (resp.data) {
            setCurrentAnalysis(resp.data);
            await Promise.all([
              loadPermitReadiness(analysisId),
              loadAuditEvents(analysisId)
            ]);
          }
        } catch (err) {
          setErrorMessage(
            err instanceof Error ? err.message : "Failed to load selected analysis."
          );
        }
      }
    },
    [analyses, loadPermitReadiness, loadAuditEvents]
  );

  // Refresh health and load saved analyses on initial startup
  const refreshHealth = useCallback(async () => {
    try {
      const response = await bid2WorkApi.getHealth();
      if (response.data) {
        setHealth(response.data);
      }
      setErrorMessage(null);
    } catch (err) {
      setErrorMessage(
        err instanceof Error ? err.message : "Backend health service unreachable."
      );
    }
  }, []);

  // Initial load
  useEffect(() => {
    let isMounted = true;

    async function initialize() {
      try {
        const [healthResp, analysisResp] = await Promise.all([
          bid2WorkApi.getHealth().catch(() => null),
          bid2WorkApi.listAnalyses(20).catch(() => null)
        ]);

        if (!isMounted) return;

        if (healthResp?.data) {
          setHealth(healthResp.data);
        }

        if (analysisResp?.data && analysisResp.data.length > 0) {
          setAnalyses(analysisResp.data);
          const latest = analysisResp.data[0];
          setCurrentAnalysis(latest);
          void loadPermitReadiness(latest.analysis_id);
          void loadAuditEvents(latest.analysis_id);
        } else {
          // If no specific analysis, load system audit events
          void loadAuditEvents();
        }
      } catch (err) {
        if (isMounted) {
          setErrorMessage(
            err instanceof Error ? err.message : "Failed to connect to backend service."
          );
        }
      }
    }

    void initialize();

    return () => {
      isMounted = false;
    };
  }, [loadPermitReadiness, loadAuditEvents]);

  // Run full compliance analysis
  const runAnalysis = useCallback(
    async (tenderFile: File, bidderFiles: File[]) => {
      setIsAnalyzing(true);
      setErrorMessage(null);

      try {
        const response = await bid2WorkApi.analyzeCompliance(tenderFile, bidderFiles);
        if (response.data) {
          const newResult = response.data;
          setCurrentAnalysis(newResult);
          setAnalyses((prev) => [newResult, ...prev.filter((a) => a.analysis_id !== newResult.analysis_id)]);
          setPermitResult(null); // Reset permit result until award simulated
          setActiveTab("analysis"); // Move to analysis view
          void loadAuditEvents(newResult.analysis_id);
        }
      } catch (err) {
        setErrorMessage(
          err instanceof Error
            ? err.message
            : "Compliance analysis failed. Verify that uploaded PDFs contain selectable text."
        );
      } finally {
        setIsAnalyzing(false);
      }
    },
    [loadAuditEvents]
  );

  // Simulate Contract Award
  const simulateAward = useCallback(
    async (payload: AwardRequestPayload) => {
      if (!currentAnalysis) return;
      setErrorMessage(null);

      try {
        const response = await bid2WorkApi.simulateAwardForAnalysis(
          currentAnalysis.analysis_id,
          payload
        );
        if (response.data) {
          setPermitResult(response.data);
          void loadAuditEvents(currentAnalysis.analysis_id);
        }
      } catch (err) {
        setErrorMessage(
          err instanceof Error
            ? err.message
            : "Failed to simulate contract award and build checklist."
        );
      }
    },
    [currentAnalysis, loadAuditEvents]
  );

  // Update a checklist item's human review state in memory
  const updateChecklistItem = useCallback(
    (updatedItem: PermitChecklistItem) => {
      setPermitResult((prev) => {
        if (!prev) return null;
        const newItems = prev.checklist_items.map((i) =>
          i.item_id === updatedItem.item_id ? updatedItem : i
        );

        // Recalculate summary metrics
        const verifiedCount = newItems.filter((i) => i.status === "Verified").length;
        const readinessPercentage =
          newItems.length > 0 ? (verifiedCount / newItems.length) * 100 : 0;

        return {
          ...prev,
          checklist_items: newItems,
          summary: {
            ...prev.summary,
            verified_count: verifiedCount,
            readiness_percentage: readinessPercentage
          }
        };
      });

      if (currentAnalysis) {
        void loadAuditEvents(currentAnalysis.analysis_id);
      }
    },
    [currentAnalysis, loadAuditEvents]
  );

  return {
    activeTab,
    setActiveTab,
    health,
    analyses,
    currentAnalysis,
    permitResult,
    auditEvents,
    isAnalyzing,
    errorMessage,
    refreshHealth,
    selectAnalysis,
    runAnalysis,
    simulateAward,
    updateChecklistItem
  };
}
