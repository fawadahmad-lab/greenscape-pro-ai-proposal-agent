import type { ProposalStatus } from "../types/proposal";
import { STATUS_LABELS } from "../types/proposal";

const STATUS_CLASSES: Record<ProposalStatus, string> = {
  DRAFT: "status-draft",
  GENERATING: "status-generating",
  NEEDS_REVIEW: "status-needs-review",
  APPROVED: "status-approved",
  SENT: "status-sent",
  FAILED: "status-failed",
};

export default function StatusBadge({ status }: { status: ProposalStatus }) {
  return (
    <span className={`status-badge ${STATUS_CLASSES[status]}`}>
      <span className="status-dot" aria-hidden="true" />
      {STATUS_LABELS[status]}
    </span>
  );
}
