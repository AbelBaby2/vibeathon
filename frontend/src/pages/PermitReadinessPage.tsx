import React, { useState } from "react";
import {
  AlertCircle,
  AlertTriangle,
  Calendar,
  HardHat,
  MapPin,
  Pencil,
  Sparkles
} from "lucide-react";
import { PermitReviewModal } from "../components/PermitReviewModal";
import { StatusBadge } from "../components/StatusBadge";
import type {
  AwardRequestPayload,
  ComplianceAnalysisResult,
  PermitChecklistItem,
  PermitReadinessResult
} from "../types";

interface PermitReadinessPageProps {
  currentAnalysis: ComplianceAnalysisResult | null;
  permitResult: PermitReadinessResult | null;
  onSimulateAward: (payload: AwardRequestPayload) => Promise<void>;
  onItemUpdated: (item: PermitChecklistItem) => void;
  onNavigateToAnalysis: () => void;
}

export const PermitReadinessPage: React.FC<PermitReadinessPageProps> = ({
  currentAnalysis,
  permitResult,
  onSimulateAward,
  onItemUpdated,
  onNavigateToAnalysis
}) => {
  const [contractReference, setContractReference] = useState("CTR-SIM-001");
  const [plannedStartDate, setPlannedStartDate] = useState(
    new Date(Date.now() + 14 * 86400000).toISOString().split("T")[0]
  );
  const [siteLocation, setSiteLocation] = useState("Primary Operational Site");
  const [isSimulating, setIsSimulating] = useState(false);
  const [selectedItemForReview, setSelectedItemForReview] =
    useState<PermitChecklistItem | null>(null);

  const [categoryFilter, setCategoryFilter] = useState<string>("ALL");
  const [statusFilter, setStatusFilter] = useState<string>("ALL");

  if (!currentAnalysis) {
    return (
      <div className="page-container">
        <div className="empty-state">
          <HardHat className="empty-state-icon" style={{ width: "48px", height: "48px", color: "var(--navy-400)" }} />
          <h2 className="empty-state-title">No Active Tender Analysis Selected</h2>
          <p className="empty-state-text">
            Work-permit readiness is generated from tender safety requirements and bidder evidence. Please upload and analyze a tender document first.
          </p>
          <button
            type="button"
            className="btn btn-primary"
            onClick={onNavigateToAnalysis}
          >
            Go to Tender Analysis
          </button>
        </div>
      </div>
    );
  }

  // Handle Award Simulation
  const handleSimulateSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSimulating(true);
    try {
      await onSimulateAward({
        contract_reference: contractReference.trim() || "CTR-SIM-001",
        planned_start_date: plannedStartDate || null,
        site_location: siteLocation.trim() || "Primary Operational Site"
      });
    } finally {
      setIsSimulating(false);
    }
  };

  // Filter Checklist Items
  const checklistItems = permitResult?.checklist_items || [];
  const filteredItems = checklistItems.filter((item) => {
    if (categoryFilter !== "ALL" && item.category !== categoryFilter) return false;
    if (statusFilter !== "ALL" && item.status !== statusFilter) return false;
    return true;
  });

  return (
    <div className="page-container">
      {/* State 1: Award Not Yet Simulated */}
      {!permitResult ? (
        <div className="card" style={{ maxWidth: "780px", margin: "2rem auto" }}>
          <div className="card-header">
            <div>
              <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginBottom: "0.25rem" }}>
                <span className="badge" style={{ backgroundColor: "#F3E8FF", color: "#6B21A8", borderColor: "#E9D5FF" }}>
                  Tender: {currentAnalysis.tender_document.filename}
                </span>
                <span className="badge" style={{ backgroundColor: "var(--navy-100)", color: "var(--navy-700)" }}>
                  {currentAnalysis.summary.safety_requirements_count} safety requirement(s) detected
                </span>
              </div>
              <h2 className="card-title">
                <HardHat style={{ width: "20px", height: "20px", color: "var(--teal-600)" }} />
                <span>Simulate Contract Award & Mobilization Readiness</span>
              </h2>
            </div>
          </div>

          <div style={{ fontSize: "0.85rem", color: "var(--navy-700)", lineHeight: 1.5, marginBottom: "1.5rem" }}>
            <p style={{ marginTop: 0 }}>
              Before a tender is awarded, safety, statutory licensing, and equipment inspection clauses remain advisory compliance checks.
            </p>
            <p>
              Simulating contract award activates the <strong>Work-Permit Readiness Intelligence Engine</strong>, which carries forward all HSE clauses into an actionable pre-mobilization checklist, verifies document validity dates against the planned start date, and records audit verification events.
            </p>
          </div>

          <form onSubmit={handleSimulateSubmit}>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem", marginBottom: "1.25rem" }}>
              <div className="form-group" style={{ margin: 0 }}>
                <label htmlFor="sim-contract-ref" className="form-label">
                  Simulated Contract Reference *
                </label>
                <input
                  id="sim-contract-ref"
                  type="text"
                  className="input"
                  value={contractReference}
                  onChange={(e) => setContractReference(e.target.value)}
                  required
                  placeholder="e.g. CTR-SIM-2026"
                />
                <span className="form-hint">Reference code to identify this simulated contract.</span>
              </div>

              <div className="form-group" style={{ margin: 0 }}>
                <label htmlFor="sim-start-date" className="form-label">
                  Planned Site Mobilization Date
                </label>
                <input
                  id="sim-start-date"
                  type="date"
                  className="input"
                  value={plannedStartDate}
                  onChange={(e) => setPlannedStartDate(e.target.value)}
                />
                <span className="form-hint">Used to evaluate expiration of certificates.</span>
              </div>
            </div>

            <div className="form-group" style={{ marginBottom: "1.5rem" }}>
              <label htmlFor="sim-site-location" className="form-label">
                Operational Site / Facility
              </label>
              <input
                id="sim-site-location"
                type="text"
                className="input"
                value={siteLocation}
                onChange={(e) => setSiteLocation(e.target.value)}
                placeholder="e.g. Terminal 3 Offshore Platform"
              />
            </div>

            <div style={{ display: "flex", justifyContent: "flex-end" }}>
              <button
                type="submit"
                className="btn btn-primary"
                disabled={isSimulating}
                id="btn-simulate-award-submit"
              >
                <Sparkles style={{ width: "16px", height: "16px" }} />
                <span>{isSimulating ? "Generating Checklist..." : "Simulate Contract Award"}</span>
              </button>
            </div>
          </form>
        </div>
      ) : (
        /* State 2: Award Has Been Simulated */
        <div>
          {/* Readiness Summary Header */}
          <div className="card" style={{ marginBottom: "1.5rem" }}>
            <div className="card-header">
              <div>
                <div style={{ display: "flex", alignItems: "center", gap: "0.6rem", marginBottom: "0.3rem" }}>
                  <span style={{ fontFamily: "var(--font-mono)", fontSize: "0.8rem", fontWeight: 700, color: "var(--teal-800)" }}>
                    {permitResult.contract_reference}
                  </span>
                  <span className="badge" style={{ backgroundColor: "#F0FDFA", color: "#0F766E", borderColor: "#99F6E4" }}>
                    Pack ID: {permitResult.permit_pack_id}
                  </span>
                  {permitResult.site_location && (
                    <span className="badge" style={{ backgroundColor: "var(--navy-100)", color: "var(--navy-700)" }}>
                      <MapPin style={{ width: "11px", height: "11px" }} /> {permitResult.site_location}
                    </span>
                  )}
                  {permitResult.planned_start_date && (
                    <span className="badge" style={{ backgroundColor: "var(--navy-100)", color: "var(--navy-700)" }}>
                      <Calendar style={{ width: "11px", height: "11px" }} /> Mobilization: {permitResult.planned_start_date}
                    </span>
                  )}
                </div>
                <h2 className="card-title">
                  <HardHat style={{ width: "18px", height: "18px", color: "var(--teal-600)" }} />
                  <span>Post-Award Work-Permit Readiness Checklist</span>
                </h2>
              </div>

              <div style={{ textAlign: "right" }}>
                <div style={{ fontSize: "0.72rem", color: "var(--navy-500)", textTransform: "uppercase", fontWeight: 600 }}>
                  Mobilization Readiness
                </div>
                <div style={{ fontSize: "1.5rem", fontWeight: 700, color: permitResult.summary.readiness_percentage > 70 ? "#166534" : "#92400E" }}>
                  {permitResult.summary.readiness_percentage.toFixed(0)}%
                </div>
              </div>
            </div>

            {/* Checklist Metrics Breakdown */}
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(130px, 1fr))", gap: "0.75rem", marginBottom: "1rem" }}>
              <div style={{ padding: "0.6rem", backgroundColor: "var(--navy-50)", borderRadius: "var(--radius-sm)", border: "1px solid var(--border-subtle)" }}>
                <div style={{ fontSize: "0.7rem", color: "var(--navy-500)", textTransform: "uppercase" }}>Total Items</div>
                <div style={{ fontSize: "1.2rem", fontWeight: 700, color: "var(--navy-900)" }}>
                  {permitResult.summary.total_items}
                </div>
              </div>
              <div style={{ padding: "0.6rem", backgroundColor: "var(--status-found-bg)", borderRadius: "var(--radius-sm)", border: "1px solid var(--status-found-border)" }}>
                <div style={{ fontSize: "0.7rem", color: "var(--status-found-text)", textTransform: "uppercase" }}>Verified</div>
                <div style={{ fontSize: "1.2rem", fontWeight: 700, color: "var(--status-found-text)" }}>
                  {permitResult.summary.verified_count}
                </div>
              </div>
              <div style={{ padding: "0.6rem", backgroundColor: "var(--status-review-bg)", borderRadius: "var(--radius-sm)", border: "1px solid var(--status-review-border)" }}>
                <div style={{ fontSize: "0.7rem", color: "var(--status-review-text)", textTransform: "uppercase" }}>Pending</div>
                <div style={{ fontSize: "1.2rem", fontWeight: 700, color: "var(--status-review-text)" }}>
                  {permitResult.summary.pending_count}
                </div>
              </div>
              <div style={{ padding: "0.6rem", backgroundColor: "var(--status-missing-bg)", borderRadius: "var(--radius-sm)", border: "1px solid var(--status-missing-border)" }}>
                <div style={{ fontSize: "0.7rem", color: "var(--status-missing-text)", textTransform: "uppercase" }}>Expired</div>
                <div style={{ fontSize: "1.2rem", fontWeight: 700, color: "var(--status-missing-text)" }}>
                  {permitResult.summary.expired_count}
                </div>
              </div>
              <div style={{ padding: "0.6rem", backgroundColor: "#FEF3C7", borderRadius: "var(--radius-sm)", border: "1px solid #FDE68A" }}>
                <div style={{ fontSize: "0.7rem", color: "#92400E", textTransform: "uppercase" }}>Blocking</div>
                <div style={{ fontSize: "1.2rem", fontWeight: 700, color: "#92400E" }}>
                  {permitResult.summary.blocking_conditions_count}
                </div>
              </div>
            </div>

            {/* Blocking Conditions Alert */}
            {permitResult.unresolved_conditions && permitResult.unresolved_conditions.length > 0 && (
              <div className="alert alert-warning" style={{ margin: 0 }}>
                <AlertTriangle style={{ width: "16px", height: "16px", flexShrink: 0 }} />
                <div>
                  <strong>{permitResult.unresolved_conditions.length} Outstanding Mobilization Condition(s):</strong>
                  <ul style={{ margin: "0.25rem 0 0", paddingLeft: "1.2rem", fontSize: "0.76rem" }}>
                    {permitResult.unresolved_conditions.map((cond, i) => (
                      <li key={i}>{cond}</li>
                    ))}
                  </ul>
                </div>
              </div>
            )}
          </div>

          {/* Checklist Table */}
          <div className="card" style={{ marginBottom: "1.5rem" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem" }}>
              <div style={{ display: "flex", gap: "0.75rem", flexWrap: "wrap" }}>
                <select
                  className="select"
                  style={{ width: "auto" }}
                  value={statusFilter}
                  onChange={(e) => setStatusFilter(e.target.value)}
                  aria-label="Filter by Readiness Status"
                  id="filter-permit-status"
                >
                  <option value="ALL">All Readiness States</option>
                  <option value="Verified">Verified</option>
                  <option value="Pending Evidence">Pending Evidence</option>
                  <option value="Expired">Expired</option>
                  <option value="Conflicting">Conflicting</option>
                  <option value="Needs Review">Needs Review</option>
                </select>

                <select
                  className="select"
                  style={{ width: "auto" }}
                  value={categoryFilter}
                  onChange={(e) => setCategoryFilter(e.target.value)}
                  aria-label="Filter by Safety Domain"
                  id="filter-permit-category"
                >
                  <option value="ALL">All Safety Domains</option>
                  <option value="HSE_POLICY">HSE Policy</option>
                  <option value="WORKER_QUALIFICATION">Worker Qualification</option>
                  <option value="EQUIPMENT_CERTIFICATION">Equipment Certification</option>
                  <option value="SITE_APPROVAL">Site Approval</option>
                  <option value="INSURANCE_LIABILITY">Insurance & Liability</option>
                  <option value="EMERGENCY_RESPONSE">Emergency Response</option>
                  <option value="HAZARD_CONTROL">Hazard Control</option>
                </select>
              </div>

              <div style={{ fontSize: "0.76rem", color: "var(--navy-600)" }}>
                Showing <strong>{filteredItems.length}</strong> of {checklistItems.length} items
              </div>
            </div>

            <div className="table-container">
              <table className="data-table" aria-label="Work-Permit Checklist">
                <thead>
                  <tr>
                    <th style={{ width: "95px" }}>Item ID</th>
                    <th style={{ width: "130px" }}>Domain</th>
                    <th>Safety / Operational Requirement</th>
                    <th style={{ width: "120px" }}>Readiness</th>
                    <th style={{ width: "160px" }}>Human Review State</th>
                    <th style={{ width: "160px" }}>Reviewer Sign-off</th>
                    <th style={{ width: "120px", textAlign: "right" }}>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredItems.length === 0 ? (
                    <tr>
                      <td colSpan={7} style={{ textAlign: "center", padding: "2rem", color: "var(--navy-500)" }}>
                        No checklist items match the current filter selection.
                      </td>
                    </tr>
                  ) : (
                    filteredItems.map((item) => (
                      <tr key={item.item_id}>
                        <td style={{ fontFamily: "var(--font-mono)", fontWeight: 600 }}>
                          {item.item_id}
                          {item.source_requirement_id && (
                            <div style={{ fontSize: "0.68rem", color: "var(--navy-500)", marginTop: "0.15rem" }}>
                              via {item.source_requirement_id}
                            </div>
                          )}
                        </td>

                        <td>
                          <span className="badge badge-category">{item.category}</span>
                        </td>

                        <td>
                          <div style={{ fontWeight: 600, color: "var(--navy-900)", marginBottom: "0.2rem" }}>
                            {item.title}
                          </div>
                          <div style={{ color: "var(--navy-700)", fontSize: "0.78rem", lineHeight: 1.4 }}>
                            {item.description}
                          </div>
                          <div style={{ marginTop: "0.3rem", fontSize: "0.72rem", color: "var(--navy-500)" }}>
                            Required: <strong>{item.required_document_type}</strong>
                            {item.expiry_date && (
                              <span style={{ marginLeft: "0.75rem", color: item.is_expired ? "#991B1B" : undefined, fontWeight: item.is_expired ? 700 : undefined }}>
                                Expiry: {item.expiry_date} {item.is_expired && "(EXPIRED)"}
                              </span>
                            )}
                          </div>
                        </td>

                        <td>
                          <StatusBadge status={item.status} type="permit" />
                        </td>

                        <td>
                          <StatusBadge status={item.review_status} type="review" />
                        </td>

                        <td>
                          {item.reviewer_name ? (
                            <div style={{ fontSize: "0.76rem" }}>
                              <strong style={{ color: "var(--navy-800)" }}>{item.reviewer_name}</strong>
                              <div style={{ color: "var(--navy-500)", fontSize: "0.7rem" }}>
                                {item.reviewer_role}
                              </div>
                            </div>
                          ) : (
                            <span style={{ color: "var(--navy-400)", fontSize: "0.75rem", fontStyle: "italic" }}>
                              Awaiting Auditor
                            </span>
                          )}
                        </td>

                        <td style={{ textAlign: "right" }}>
                          <button
                            type="button"
                            className="btn btn-outline btn-sm"
                            onClick={() => setSelectedItemForReview(item)}
                            title="Update human review state and record audit log"
                          >
                            <Pencil style={{ width: "12px", height: "12px" }} />
                            <span>Review</span>
                          </button>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>

          {/* Legal / Operational Notice */}
          <div className="alert alert-info" style={{ fontSize: "0.74rem" }}>
            <AlertCircle style={{ width: "16px", height: "16px", flexShrink: 0 }} />
            <div>
              <strong>Audited Demonstration Notice:</strong> Reviewer approval actions demonstrate verifiable audit trail recording in SQLite. This system serves as a decision-support and readiness tool; it does not issue formal statutory permits-to-work or replace mandatory physical site inspections.
            </div>
          </div>
        </div>
      )}

      {/* Human Review Modal */}
      <PermitReviewModal
        item={selectedItemForReview}
        onClose={() => setSelectedItemForReview(null)}
        onUpdated={(updated) => {
          onItemUpdated(updated);
          setSelectedItemForReview(null);
        }}
      />
    </div>
  );
};
