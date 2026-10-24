import React from "react";
import type { ComplianceStatus, HealthStatus } from "../types";

interface WorkflowOverviewProps {
  health: HealthStatus | null;
  errorMessage: string | null;
  onRetryHealth: () => void;
}

const WORKFLOW_STEPS = [
  "1. Upload one text-based tender PDF and one or more bidder supporting PDFs.",
  "2. Extract and retain page-level text and source references (filename + page).",
  "3. Identify tender requirements (eligibility, experience, financial, certifications, deadlines, safety).",
  "4. Match each requirement against evidence in bidder documents.",
  "5. Flag requirements as Evidence Found, Missing, Conflicting, or Needs Review.",
  "6. Display evidence excerpts, source filenames, and 1-based page numbers.",
  "7. Simulate a contract award to carry safety requirements into a work-permit readiness checklist.",
  "8. Check supporting safety documents, qualifications, approvals, expiry dates, and unresolved conditions.",
  "9. Track compliance status and SQLite-backed audit events.",
  "10. Export a structured report (Markdown, JSON, or HTML)."
];

const COMPLIANCE_STATUSES: ComplianceStatus[] = [
  "Evidence Found",
  "Missing",
  "Conflicting",
  "Needs Review"
];

export const WorkflowOverview: React.FC<WorkflowOverviewProps> = ({
  health,
  errorMessage,
  onRetryHealth
}) => {
  return (
    <div className="dashboard-grid">
      <section className="card">
        <h2>Product Workflow Foundation</h2>
        <p className="card-lead">
          End-to-end decision-support pipeline from tender PDF ingestion to
          post-award work-permit readiness.
        </p>
        <ol className="workflow-list">
          {WORKFLOW_STEPS.map((step) => (
            <li key={step}>{step}</li>
          ))}
        </ol>
      </section>

      <section className="card">
        <h2>Shared Contracts &amp; System Readiness</h2>
        <p className="card-lead">
          Pydantic &amp; TypeScript schemas initialized for documents,
          requirements, evidence, compliance assessments, work permits, audit
          logs, and report exports.
        </p>

        <div className="badge-row">
          {COMPLIANCE_STATUSES.map((status) => (
            <span key={status} className="compliance-badge">
              {status}
            </span>
          ))}
        </div>

        {errorMessage && (
          <div className="error-alert">
            <span>{errorMessage}</span>
            <button type="button" onClick={onRetryHealth} className="btn-retry">
              Retry Check
            </button>
          </div>
        )}

        <div className="telemetry-box">
          <div>
            <strong>Backend Service:</strong> {health?.service ?? "Pending"}
          </div>
          <div>
            <strong>Environment:</strong> {health?.environment ?? "development"}
          </div>
          <div>
            <strong>Upload Safeguards:</strong> Max{" "}
            {health?.max_upload_size_mb ?? 25} MB /{" "}
            {health?.max_bidder_files ?? 10} Bidder PDFs
          </div>
          <div>
            <strong>Audit SQLite DB:</strong>{" "}
            {health?.database_ready ? "Ready" : "Standby"}
          </div>
          <div>
            <strong>LLM Provider:</strong>{" "}
            {health
              ? `${health.llm_provider} (${health.llm_model}) — ${
                  health.llm_configured ? "Configured" : "Awaiting API Key"
                }`
              : "Checking..."}
          </div>
        </div>
      </section>
    </div>
  );
};
