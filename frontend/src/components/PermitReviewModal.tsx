import React, { useState } from "react";
import { AlertTriangle, ShieldAlert, X } from "lucide-react";
import { StatusBadge } from "./StatusBadge";
import { bid2WorkApi } from "../services/apiClient";
import type { HumanReviewStatus, PermitChecklistItem } from "../types";

interface PermitReviewModalProps {
  item: PermitChecklistItem | null;
  onClose: () => void;
  onUpdated: (updatedItem: PermitChecklistItem) => void;
}

export const PermitReviewModal: React.FC<PermitReviewModalProps> = ({
  item,
  onClose,
  onUpdated
}) => {
  if (!item) return null;

  const [reviewStatus, setReviewStatus] = useState<HumanReviewStatus>(
    item.review_status || "incomplete"
  );
  const [reviewerName, setReviewerName] = useState(item.reviewer_name || "Lead HSE Officer");
  const [reviewerRole, setReviewerRole] = useState(item.reviewer_role || "hse_officer");
  const [isAuthorized, setIsAuthorized] = useState(true);
  const [reviewerNotes, setReviewerNotes] = useState(
    item.reviewer_notes || "Documented evidence cross-checked against statutory criteria."
  );
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    setErrorMessage(null);

    try {
      const response = await bid2WorkApi.updatePermitItem(item.item_id, {
        review_status: reviewStatus,
        reviewer_name: reviewerName.trim() || null,
        reviewer_role: reviewerRole || null,
        is_authorized_reviewer: isAuthorized,
        reviewer_notes: reviewerNotes.trim() || null
      });

      if (response.data) {
        onUpdated(response.data);
        onClose();
      }
    } catch (err) {
      setErrorMessage(
        err instanceof Error
          ? err.message
          : "Failed to update review status. Please verify permissions."
      );
    } finally {
      setIsSubmitting(false);
    }
  };

  const isApprovedSelected = reviewStatus === "approved_by_reviewer";

  return (
    <div className="modal-backdrop" onClick={onClose} role="dialog" aria-modal="true" aria-labelledby="modal-title">
      <div className="modal-dialog" onClick={(e) => e.stopPropagation()}>
        <form onSubmit={handleSubmit}>
          <div className="modal-header">
            <div>
              <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginBottom: "0.2rem" }}>
                <span style={{ fontFamily: "var(--font-mono)", fontSize: "0.75rem", color: "var(--navy-500)", fontWeight: 600 }}>
                  {item.item_id}
                </span>
                <StatusBadge status={item.status} type="permit" />
                <StatusBadge status={item.review_status} type="review" />
              </div>
              <h2 id="modal-title" style={{ margin: 0, fontSize: "1.05rem", color: "var(--navy-900)" }}>
                Review Work-Permit Requirement
              </h2>
            </div>
            <button
              type="button"
              className="btn btn-outline btn-icon"
              onClick={onClose}
              aria-label="Close dialog"
            >
              <X style={{ width: "16px", height: "16px" }} />
            </button>
          </div>

          <div className="modal-body">
            {errorMessage && (
              <div className="alert alert-danger" role="alert">
                <ShieldAlert style={{ width: "16px", height: "16px", flexShrink: 0 }} />
                <span>{errorMessage}</span>
              </div>
            )}

            {/* Item Summary */}
            <div style={{ marginBottom: "1.25rem", padding: "0.75rem", backgroundColor: "var(--navy-50)", borderRadius: "var(--radius-md)", border: "1px solid var(--border-subtle)", fontSize: "0.8rem" }}>
              <strong style={{ color: "var(--navy-900)", display: "block", marginBottom: "0.25rem" }}>
                {item.title}
              </strong>
              <div style={{ color: "var(--navy-700)", lineHeight: 1.4 }}>
                {item.description}
              </div>
              <div style={{ marginTop: "0.5rem", display: "flex", flexWrap: "wrap", gap: "0.75rem", fontSize: "0.74rem", color: "var(--navy-600)" }}>
                <span>Doc: <strong>{item.required_document_type}</strong></span>
                {item.qualification_reference && (
                  <span>Ref: <strong>{item.qualification_reference}</strong></span>
                )}
                {item.expiry_date && (
                  <span>
                    Expires: <strong>{item.expiry_date}</strong>{" "}
                    {item.is_expired && <span style={{ color: "#DC2626", fontWeight: 700 }}>(EXPIRED)</span>}
                  </span>
                )}
              </div>
            </div>

            {/* Target Review Status */}
            <div className="form-group">
              <label htmlFor="target-review-status" className="form-label">
                Target Verification State *
              </label>
              <select
                id="target-review-status"
                className="select"
                value={reviewStatus}
                onChange={(e) => setReviewStatus(e.target.value as HumanReviewStatus)}
                required
              >
                <option value="incomplete">Incomplete — Missing evidence or credentials</option>
                <option value="requires_verification">Requires Verification — Conflicting or unverified</option>
                <option value="ready_for_review">Ready for Review — Evidence attached for auditor</option>
                <option value="approved_by_reviewer">Approved by Reviewer — Qualified human auditor sign-off</option>
              </select>
            </div>

            {/* Reviewer Details (enabled when approving) */}
            <div style={{ padding: "1rem", backgroundColor: isApprovedSelected ? "#F0FDFA" : "#FFFFFF", border: `1px solid ${isApprovedSelected ? "#99F6E4" : "var(--border-subtle)"}`, borderRadius: "var(--radius-md)", marginBottom: "1rem" }}>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0.75rem", marginBottom: "0.75rem" }}>
                <div className="form-group" style={{ margin: 0 }}>
                  <label htmlFor="reviewer-name-input" className="form-label">
                    Reviewer Name {isApprovedSelected && "*"}
                  </label>
                  <input
                    id="reviewer-name-input"
                    type="text"
                    className="input"
                    value={reviewerName}
                    onChange={(e) => setReviewerName(e.target.value)}
                    required={isApprovedSelected}
                    placeholder="e.g. Elena Vance"
                  />
                </div>

                <div className="form-group" style={{ margin: 0 }}>
                  <label htmlFor="reviewer-role-select" className="form-label">
                    Auditor Role {isApprovedSelected && "*"}
                  </label>
                  <select
                    id="reviewer-role-select"
                    className="select"
                    value={reviewerRole}
                    onChange={(e) => setReviewerRole(e.target.value)}
                  >
                    <option value="hse_officer">HSE Officer (Authorized)</option>
                    <option value="authorised_reviewer">Authorised Reviewer</option>
                    <option value="site_safety_officer">Site Safety Officer</option>
                    <option value="safety_auditor">Safety Auditor</option>
                    <option value="lead_auditor">Lead Auditor</option>
                    <option value="procurement_lead">Procurement Lead</option>
                  </select>
                </div>
              </div>

              {isApprovedSelected && (
                <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginTop: "0.5rem" }}>
                  <input
                    type="checkbox"
                    id="is-auth-reviewer-checkbox"
                    checked={isAuthorized}
                    onChange={(e) => setIsAuthorized(e.target.checked)}
                    style={{ accentColor: "var(--teal-600)" }}
                  />
                  <label htmlFor="is-auth-reviewer-checkbox" style={{ fontSize: "0.78rem", color: "var(--navy-800)", fontWeight: 500, cursor: "pointer" }}>
                    I confirm I am an authorised human reviewer with qualification to evaluate this requirement.
                  </label>
                </div>
              )}
            </div>

            {/* Reviewer Notes */}
            <div className="form-group">
              <label htmlFor="reviewer-notes-area" className="form-label">
                Audited Reviewer Notes / Rationale
              </label>
              <textarea
                id="reviewer-notes-area"
                className="textarea"
                rows={3}
                value={reviewerNotes}
                onChange={(e) => setReviewerNotes(e.target.value)}
                placeholder="Document verification findings, caveats, or mobilization instructions..."
              />
            </div>

            {/* Demonstration Warning */}
            <div className="alert alert-warning" style={{ margin: 0, fontSize: "0.73rem" }}>
              <AlertTriangle style={{ width: "15px", height: "15px", flexShrink: 0 }} />
              <div>
                <strong>Demonstration Workflow:</strong> Reviewer approval records an audited compliance review in the SQLite ledger. This interface does not issue a formal statutory work permit, and automatic issuance is strictly disallowed.
              </div>
            </div>
          </div>

          <div className="modal-footer">
            <button
              type="button"
              className="btn btn-secondary"
              onClick={onClose}
              disabled={isSubmitting}
            >
              Cancel
            </button>
            <button
              type="submit"
              className="btn btn-primary"
              disabled={isSubmitting}
              id="btn-submit-review-update"
            >
              {isSubmitting ? "Saving Audit Entry..." : "Save Review Status"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
