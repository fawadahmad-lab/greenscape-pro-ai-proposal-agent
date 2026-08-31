import StatusBadge from "./StatusBadge";
import type { Proposal, ProposalStatus } from "../types/proposal";

interface ProposalReviewProps {
  proposal: Proposal;
  disabled: boolean;
  onGenerate: () => void;
  onApprove: () => void;
  onSend: () => void;
  error?: string | null;
}

function formatCurrency(value: number | null): string {
  if (value === null || value === undefined) return "—";
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
  }).format(value);
}

function formatQuantity(q: number | null): string {
  if (q === null || q === undefined) return "TBD";
  return q.toLocaleString("en-US");
}

export function canGenerate(status: ProposalStatus): boolean {
  return status === "DRAFT" || status === "FAILED";
}

export function canApprove(status: ProposalStatus): boolean {
  return status === "NEEDS_REVIEW";
}

export function canSend(status: ProposalStatus): boolean {
  return status === "APPROVED";
}

export default function ProposalReview({
  proposal,
  disabled,
  onGenerate,
  onApprove,
  onSend,
  error,
}: ProposalReviewProps) {
  return (
    <div className="proposal-detail">
      <section className="card">
        <h2>Client Information</h2>
        <dl className="info-grid">
          <div>
            <dt>Name</dt>
            <dd>{proposal.client_name}</dd>
          </div>
          <div>
            <dt>Email</dt>
            <dd>{proposal.client_email}</dd>
          </div>
          <div>
            <dt>Address</dt>
            <dd>{proposal.project_address}</dd>
          </div>
          <div>
            <dt>Status</dt>
            <dd>
              <StatusBadge status={proposal.status} />
            </dd>
          </div>
        </dl>
      </section>

      <section className="card">
        <h2>Original Site Walk Notes</h2>
        <p className="pre-wrap notes">{proposal.site_walk_notes}</p>
      </section>

      {proposal.project_summary && (
        <section className="card">
          <h2>AI Project Summary</h2>
          <p>{proposal.project_summary}</p>
        </section>
      )}

      {proposal.scope_json && proposal.scope_json.length > 0 && (
        <section className="card">
          <h2>Scope of Work</h2>
          <table className="detail-table">
            <thead>
              <tr>
                <th>Requested Work</th>
                <th>Pricing Item</th>
                <th>Qty</th>
                <th>Unit</th>
                <th>Unit Price</th>
                <th>Line Total</th>
                <th>Confidence</th>
              </tr>
            </thead>
            <tbody>
              {proposal.scope_json.map((item, idx) => {
                const priced = proposal.pricing_json?.[idx];
                return (
                  <tr key={idx}>
                    <td>{item.requested_work}</td>
                    <td>
                      {priced?.catalog_item_name ?? item.catalog_item_name ?? "Unmatched"}
                      {priced?.quantity_uncertain && (
                        <span className="uncertain-tag" title="Quantity requires confirmation">
                          needs qty
                        </span>
                      )}
                    </td>
                    <td>{priced ? formatQuantity(priced.quantity) : formatQuantity(item.quantity)}</td>
                    <td>{priced?.unit ?? ""}</td>
                    <td>{priced ? formatCurrency(priced.unit_price) : "—"}</td>
                    <td>{priced ? formatCurrency(priced.line_total) : "—"}</td>
                    <td>{Math.round((priced?.confidence ?? item.confidence) * 100)}%</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
          <div className="total-row">
            <strong>Estimated Total</strong>
            <strong>{formatCurrency(proposal.estimated_total)}</strong>
          </div>
          <p className="hint">
            Pricing is calculated deterministically in application code and labeled
            as a draft estimate pending final human review. Demo/sample catalog only.
          </p>
        </section>
      )}

      <div className="review-sections">
        {(proposal.assumptions_json?.length ?? 0) > 0 && (
          <section className="card">
            <h2>Assumptions</h2>
            <ul>
              {proposal.assumptions_json!.map((item, idx) => (
                <li key={idx}>{item}</li>
              ))}
            </ul>
          </section>
        )}

        {(proposal.clarifying_questions_json?.length ?? 0) > 0 && (
          <section className="card">
            <h2>Clarifying Questions</h2>
            <ul>
              {proposal.clarifying_questions_json!.map((item, idx) => (
                <li key={idx}>{item}</li>
              ))}
            </ul>
          </section>
        )}

        {(proposal.risk_flags_json?.length ?? 0) > 0 && (
          <section className="card">
            <h2>Risk Flags</h2>
            <ul>
              {proposal.risk_flags_json!.map((item, idx) => (
                <li key={idx}>{item}</li>
              ))}
            </ul>
          </section>
        )}
      </div>

      {proposal.generated_proposal && (
        <section className="card">
          <h2>Generated Proposal Draft</h2>
          <div className="proposal-draft">{proposal.generated_proposal}</div>
          <p className="hint">
            This is a draft estimate pending final human review. It is not a binding
            quote and does not include claims about permits or HOA approvals.
          </p>
        </section>
      )}

      {error && <div className="form-error">{error}</div>}

      <section className="card action-bar">
        {proposal.status === "DRAFT" && (
          <button
            className="btn btn-primary"
            onClick={onGenerate}
            disabled={disabled || !canGenerate(proposal.status)}
          >
            Generate Proposal with AI
          </button>
        )}

        {proposal.status === "GENERATING" && (
          <p className="generating-message">
            Generating proposal with AI… please wait. This can take a short while.
          </p>
        )}

        {proposal.status === "FAILED" && (
          <div>
            <p className="error-message">
              Generation failed. The proposal was not left stuck; you can review the
              notes and retry generation.
            </p>
            <button
              className="btn btn-primary"
              onClick={onGenerate}
              disabled={disabled}
            >
              Retry Generation
            </button>
          </div>
        )}

        {proposal.status === "NEEDS_REVIEW" && (
          <button
            className="btn btn-success"
            onClick={onApprove}
            disabled={disabled || !canApprove(proposal.status)}
          >
            Approve Proposal
          </button>
        )}

        {proposal.status === "APPROVED" && (
          <button
            className="btn btn-primary"
            onClick={onSend}
            disabled={disabled || !canSend(proposal.status)}
          >
            Send Notification
          </button>
        )}

        {proposal.status === "SENT" && proposal.sent_at && (
          <p className="sent-message">
            Proposal sent on {new Date(proposal.sent_at).toLocaleString()}.
          </p>
        )}

        {proposal.status === "SENT" && !proposal.sent_at && (
          <p className="sent-message">Proposal has been sent.</p>
        )}
      </section>
    </div>
  );
}
