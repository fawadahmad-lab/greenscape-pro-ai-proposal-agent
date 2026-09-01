import { Link } from "react-router-dom";
import { FileText, ArrowRight, Calendar, Plus } from "lucide-react";
import StatusBadge from "./StatusBadge";
import EmptyState from "./EmptyState";
import Button from "./Button";
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
    return (
      <EmptyState
        icon={<FileText size={30} />}
        title="No proposals yet"
        description="Create your first proposal to get started. The AI will turn your site-walk notes into a priced, review-ready draft."
        action={
          <Button as="link" to="/proposals/new" icon={<Plus size={18} />}>
            New Proposal
          </Button>
        }
      />
    );
  }

  return (
    <div>
      {/* Desktop table */}
      <div className="proposal-list-table table-scroll">
        <table className="proposal-table">
          <thead>
            <tr>
              <th>Client</th>
              <th>Status</th>
              <th>Estimated Total</th>
              <th>Created</th>
              <th style={{ textAlign: "right" }}>Action</th>
            </tr>
          </thead>
          <tbody>
            {proposals.map((proposal) => (
              <tr key={proposal.id}>
                <td>
                  <strong>{proposal.client_name}</strong>{" "}
                  <span style={{ color: "var(--gp-ink-faint)" }}>#{proposal.id}</span>
                </td>
                <td>
                  <StatusBadge status={proposal.status} />
                </td>
                <td style={{ fontWeight: 700, whiteSpace: "nowrap" }}>
                  {formatCurrency(proposal.estimated_total)}
                </td>
                <td>{formatDate(proposal.created_at)}</td>
                <td style={{ textAlign: "right" }}>
                  <Link
                    className="btn btn-secondary btn-sm"
                    to={`/proposals/${proposal.id}`}
                  >
                    View{" "}
                    <ArrowRight size={15} style={{ marginLeft: 2 }} aria-hidden="true" />
                  </Link>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Mobile cards */}
      <div className="proposal-list">
        {proposals.map((proposal) => (
          <Link
            key={proposal.id}
            to={`/proposals/${proposal.id}`}
            className="proposal-row"
          >
            <div className="proposal-row-main">
              <span className="proposal-row-title">
                {proposal.client_name}{" "}
                <span style={{ fontWeight: 500, color: "var(--gp-ink-faint)" }}>
                  #{proposal.id}
                </span>
              </span>
              <StatusBadge status={proposal.status} />
              <div className="proposal-row-meta">
                <span>
                  <Calendar size={15} aria-hidden="true" />
                  {formatDate(proposal.created_at)}
                </span>
              </div>
            </div>
            <div className="proposal-row-total">
              <span className="sr-only">Estimated total: </span>
              {formatCurrency(proposal.estimated_total)}
            </div>
            <div className="proposal-row-actions">
              <span className="btn btn-secondary btn-sm">View</span>
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}
