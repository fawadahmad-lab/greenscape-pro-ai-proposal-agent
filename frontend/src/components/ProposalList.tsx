import { Link } from "react-router-dom";
import StatusBadge from "./StatusBadge";
import type { ProposalListItem } from "../types/proposal";

function formatCurrency(value: number | null): string {
  if (value === null || value === undefined) return "—";
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(value);
}

function formatDate(value: string): string {
  return new Date(value).toLocaleDateString("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

export default function ProposalList({ proposals }: { proposals: ProposalListItem[] }) {
  if (proposals.length === 0) {
    return <p className="empty-state">No proposals yet. Create your first one.</p>;
  }

  return (
    <table className="proposal-table">
      <thead>
        <tr>
          <th>Client</th>
          <th>Status</th>
          <th>Estimated Total</th>
          <th>Created</th>
          <th>Action</th>
        </tr>
      </thead>
      <tbody>
        {proposals.map((proposal) => (
          <tr key={proposal.id}>
            <td>{proposal.client_name}</td>
            <td>
              <StatusBadge status={proposal.status} />
            </td>
            <td>{formatCurrency(proposal.estimated_total)}</td>
            <td>{formatDate(proposal.created_at)}</td>
            <td>
              <Link className="btn btn-small" to={`/proposals/${proposal.id}`}>
                View
              </Link>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
