import type {
  ApiResponse,
  AuditLogListResponse,
  AwardSimulationRequest,
  ComplianceAnalysisResult,
  DocumentExtractionResult,
  DocumentRole,
  ExportableReportData,
  HealthStatus,
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

  async extractDocument(
    file: File,
    role: DocumentRole = "TENDER"
  ): Promise<ApiResponse<DocumentExtractionResult>> {
    const formData = new FormData();
    formData.append("file", file);
    formData.append("role", role);

    const response = await fetch(`${API_BASE_URL}/api/v1/compliance/extract`, {
      method: "POST",
      body: formData
    });
    return parseEnvelope<DocumentExtractionResult>(response);
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

  async simulateAward(
    request: AwardSimulationRequest
  ): Promise<ApiResponse<PermitReadinessResult>> {
    const response = await fetch(
      `${API_BASE_URL}/api/v1/permits/simulate-award`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(request)
      }
    );
    return parseEnvelope<PermitReadinessResult>(response);
  },

  async listAuditEvents(
    analysisId?: string,
    limit = 50
  ): Promise<ApiResponse<AuditLogListResponse>> {
    const params = new URLSearchParams({ limit: String(limit) });
    if (analysisId) {
      params.set("analysis_id", analysisId);
    }
    const response = await fetch(
      `${API_BASE_URL}/api/v1/audit/events?${params.toString()}`,
      {
        method: "GET",
        headers: { Accept: "application/json" }
      }
    );
    return parseEnvelope<AuditLogListResponse>(response);
  },

  async exportReport(
    request: ReportExportRequest
  ): Promise<ApiResponse<ExportableReportData>> {
    const response = await fetch(`${API_BASE_URL}/api/v1/reports/export`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(request)
    });
    return parseEnvelope<ExportableReportData>(response);
  }
};
