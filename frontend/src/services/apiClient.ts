import type {
  ApiResponse,
  AuditLogListResponse,
  AwardRequestPayload,
  AwardSimulationRequest,
  ComplianceAnalysisResult,
  DocumentRole,
  DocumentUploadBatchResponse,
  ExportableReportData,
  HealthStatus,
  PermitChecklistItem,
  PermitItemUpdateRequest,
  PermitReadinessResult,
  ReportExportRequest
} from "../types";

const RAW_BASE_URL = (import.meta.env.VITE_API_BASE_URL as string | undefined) || "";
export const API_BASE_URL = RAW_BASE_URL.replace(/\/+$/, "");

async function parseEnvelope<T>(response: Response): Promise<ApiResponse<T>> {
  const payload = (await response.json()) as ApiResponse<T>;
  if (!response.ok || !payload.success) {
    const errMsg =
      payload?.error?.message || `HTTP ${response.status}: Request failed`;
    throw new Error(errMsg);
  }
  return payload;
}

export const bid2WorkApi = {
  async getHealth(): Promise<ApiResponse<HealthStatus>> {
    const response = await fetch(`${API_BASE_URL}/api/v1/health`, {
      method: "GET",
      headers: { Accept: "application/json" }
    });
    return parseEnvelope<HealthStatus>(response);
  },

  async listAnalyses(limit = 20): Promise<ApiResponse<ComplianceAnalysisResult[]>> {
    const response = await fetch(`${API_BASE_URL}/api/v1/analysis?limit=${limit}`, {
      method: "GET",
      headers: { Accept: "application/json" }
    });
    return parseEnvelope<ComplianceAnalysisResult[]>(response);
  },

  async getAnalysis(analysisId: string): Promise<ApiResponse<ComplianceAnalysisResult>> {
    const response = await fetch(`${API_BASE_URL}/api/v1/analysis/${encodeURIComponent(analysisId)}`, {
      method: "GET",
      headers: { Accept: "application/json" }
    });
    return parseEnvelope<ComplianceAnalysisResult>(response);
  },

  async uploadDocuments(
    files: File[],
    roles?: DocumentRole[]
  ): Promise<ApiResponse<DocumentUploadBatchResponse>> {
    const formData = new FormData();
    files.forEach((f) => formData.append("files", f));
    if (roles && roles.length === files.length) {
      roles.forEach((r) => formData.append("roles", r));
    }
    const response = await fetch(`${API_BASE_URL}/api/v1/documents/upload`, {
      method: "POST",
      body: formData
    });
    return parseEnvelope<DocumentUploadBatchResponse>(response);
  },

  async analyzeCompliance(
    tenderFile: File,
    bidderFiles: File[]
  ): Promise<ApiResponse<ComplianceAnalysisResult>> {
    const formData = new FormData();
    formData.append("tender_file", tenderFile);
    bidderFiles.forEach((bf) => formData.append("bidder_files", bf));

    const response = await fetch(`${API_BASE_URL}/api/v1/compliance/analyze`, {
      method: "POST",
      body: formData
    });
    return parseEnvelope<ComplianceAnalysisResult>(response);
  },

  async createAnalysisFromIds(
    tenderDocumentId: string,
    bidderDocumentIds: string[]
  ): Promise<ApiResponse<ComplianceAnalysisResult>> {
    const response = await fetch(`${API_BASE_URL}/api/v1/analysis`, {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "application/json" },
      body: JSON.stringify({
        tender_document_id: tenderDocumentId,
        bidder_document_ids: bidderDocumentIds
      })
    });
    return parseEnvelope<ComplianceAnalysisResult>(response);
  },

  async simulateAward(
    request: AwardSimulationRequest
  ): Promise<ApiResponse<PermitReadinessResult>> {
    const response = await fetch(`${API_BASE_URL}/api/v1/permits/simulate-award`, {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "application/json" },
      body: JSON.stringify(request)
    });
    return parseEnvelope<PermitReadinessResult>(response);
  },

  async simulateAwardForAnalysis(
    analysisId: string,
    payload: AwardRequestPayload = {}
  ): Promise<ApiResponse<PermitReadinessResult>> {
    const response = await fetch(`${API_BASE_URL}/api/v1/analysis/${encodeURIComponent(analysisId)}/award`, {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "application/json" },
      body: JSON.stringify({
        contract_reference: payload.contract_reference || "CTR-SIM-001",
        planned_start_date: payload.planned_start_date || null,
        site_location: payload.site_location || "Primary Operational Site"
      })
    });
    return parseEnvelope<PermitReadinessResult>(response);
  },

  async getPermitReadiness(
    analysisId: string,
    autoSimulate = false
  ): Promise<ApiResponse<PermitReadinessResult | null>> {
    const response = await fetch(
      `${API_BASE_URL}/api/v1/analysis/${encodeURIComponent(analysisId)}/permit-readiness?auto_simulate=${autoSimulate}`,
      {
        method: "GET",
        headers: { Accept: "application/json" }
      }
    );
    return parseEnvelope<PermitReadinessResult | null>(response);
  },

  async updatePermitItem(
    itemId: string,
    update: PermitItemUpdateRequest
  ): Promise<ApiResponse<PermitChecklistItem>> {
    const response = await fetch(`${API_BASE_URL}/api/v1/permit-items/${encodeURIComponent(itemId)}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json", Accept: "application/json" },
      body: JSON.stringify(update)
    });
    return parseEnvelope<PermitChecklistItem>(response);
  },

  async downloadReportCsv(analysisId: string): Promise<string> {
    const response = await fetch(
      `${API_BASE_URL}/api/v1/analysis/${encodeURIComponent(analysisId)}/report`,
      {
        method: "GET",
        headers: { Accept: "text/csv" }
      }
    );
    if (!response.ok) {
      let errMsg = `Failed to download CSV: HTTP ${response.status}`;
      try {
        const errJson = await response.json();
        errMsg = errJson?.error?.message || errMsg;
      } catch {
        // Fall back to HTTP status message
      }
      throw new Error(errMsg);
    }
    const csvText = await response.text();
    const blob = new Blob([csvText], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.setAttribute("download", `compliance_report_${analysisId.toLowerCase()}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
    return csvText;
  },

  async listAuditEvents(
    analysisId?: string,
    limit = 50
  ): Promise<ApiResponse<AuditLogListResponse>> {
    const params = new URLSearchParams({ limit: String(limit) });
    if (analysisId) {
      params.set("analysis_id", analysisId);
    }
    const response = await fetch(`${API_BASE_URL}/api/v1/audit/events?${params.toString()}`, {
      method: "GET",
      headers: { Accept: "application/json" }
    });
    return parseEnvelope<AuditLogListResponse>(response);
  },

  async exportReport(
    request: ReportExportRequest
  ): Promise<ApiResponse<ExportableReportData>> {
    const response = await fetch(`${API_BASE_URL}/api/v1/reports/export`, {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "application/json" },
      body: JSON.stringify(request)
    });
    return parseEnvelope<ExportableReportData>(response);
  }
};
