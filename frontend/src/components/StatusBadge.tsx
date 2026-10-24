import React from "react";
import type { ComplianceStatus, HumanReviewStatus, PermitItemStatus, RequirementPriority } from "../types";

interface StatusBadgeProps {
  status: ComplianceStatus | PermitItemStatus | HumanReviewStatus | RequirementPriority | string;
  type?: "compliance" | "permit" | "review" | "priority" | "category";
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({ status, type = "compliance" }) => {
  let badgeClass = "badge";

  if (type === "compliance") {
    switch (status) {
      case "Evidence Found":
        badgeClass += " badge-status-found";
        break;
      case "Missing":
        badgeClass += " badge-status-missing";
        break;
      case "Conflicting":
        badgeClass += " badge-status-conflicting";
        break;
      case "Needs Review":
      default:
        badgeClass += " badge-status-review";
        break;
    }
  } else if (type === "permit") {
    switch (status) {
      case "Verified":
        badgeClass += " badge-verified";
        break;
      case "Expired":
        badgeClass += " badge-expired";
        break;
      case "Conflicting":
        badgeClass += " badge-conflict";
        break;
      case "Pending Evidence":
      case "Needs Review":
      default:
        badgeClass += " badge-pending";
        break;
    }
  } else if (type === "review") {
    switch (status) {
      case "approved_by_reviewer":
        badgeClass += " badge-approved";
        break;
      case "ready_for_review":
        badgeClass += " badge-status-review";
        break;
      case "requires_verification":
        badgeClass += " badge-conflict";
        break;
      case "incomplete":
      default:
        badgeClass += " badge-incomplete";
        break;
    }
  } else if (type === "priority") {
    switch (status) {
      case "MANDATORY":
        badgeClass += " badge-priority-mandatory";
        break;
      case "RECOMMENDED":
        badgeClass += " badge-priority-recommended";
        break;
      case "INFORMATIONAL":
      default:
        badgeClass += " badge-priority-informational";
        break;
    }
  } else if (type === "category") {
    badgeClass += " badge-category";
  }

  // Format display text for review states
  let displayText = String(status);
  if (type === "review") {
    switch (status) {
      case "approved_by_reviewer":
        displayText = "Approved by Reviewer";
        break;
      case "ready_for_review":
        displayText = "Ready for Review";
        break;
      case "requires_verification":
        displayText = "Requires Verification";
        break;
      case "incomplete":
        displayText = "Incomplete";
        break;
    }
  }

  return <span className={badgeClass}>{displayText}</span>;
};
