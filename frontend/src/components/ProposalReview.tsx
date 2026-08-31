import StatusBadge from "./StatusBadge";
import ProposalMarkdown from "./ProposalMarkdown";
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
  if (value === null || value === undefined) return "TBD";
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
  }).format(value);
}

function formatQuantity(q: number | null): string {
  if (q === null || q === undefined) return "TBD";
  return q.toLocaleString("en-US");
}

function formatDateTime(value: string): string {
  if (!value) return "";
  const d = new Date(value);
  return d.toLocaleString("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
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
  const pricedItems = proposal.pricing_json ?? [];
  const tbdItems = pricedItems.filter((item) => !item.is_priced);

  return (
    <div className="proposal-detail">
      {/* Client Information */}
      <section className="card">
        <h2 className="section-title">Client Information</h2>
        <dl className="info-grid">
          <div>
            <dt>Client Name</dt>
            <dd>{proposal.client_name}</dd>
          </div>
          <div>
            <dt>Email</dt>
            <dd>
              <a href={`mailto:${proposal.client_email}`}>{proposal.client_email}</a>
            </dd>
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

      {/* Site Walk Notes */}
      <section className="card">
        <h2 className="section-title">Site Walk Notes</h2>
        <div className="notes pre-wrap">{proposal.site_walk_notes}</div>
      </section>

      {/* Generated Proposal */}
      <section className="card">
        <h2 className="section-title">Generated Proposal</h2>

        {proposal.project_summary && (
          <p className="project-summary">{proposal.project_summary}</p>
        )}

        {proposal.scope_json && proposal.scope_json.length > 0 && (
          <div className="table-scroll">
            <table className="detail-table">
              <thead>
                <tr>
                  <th>Requested Work</th>
                  <th>Pricing Item</th>
                  <th>Qty</th>
                  <th>Unit</th>
                  <th>Unit Price</th>
                  <th>Line Total</th>
                </tr>
              </thead>
              <tbody>
                {proposal.scope_json.map((item, idx) => {
                  const priced = proposal.pricing_json?.[idx];
                  return (
                    <tr key={idx}>
                      <td>{item.requested_work}</td>
                      <td>
                        {priced?.catalog_item_name ??
                          item.catalog_item_name ??
                          "Unmatched"}
                        {!priced?.is_priced && (
                          <span
                            className="uncertain-tag"
                            title="Quantity or price requires confirmation"
                          >
                            TBD
                          </span>
                        )}
                      </td>
                      <td>{formatQuantity(priced?.quantity ?? item.quantity)}</td>
                      <td>{priced?.unit ?? ""}</td>
                      <td>{formatCurrency(priced?.unit_price ?? null)}</td>
                      <td>{formatCurrency(priced?.line_total ?? null)}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}

        {proposal.estimated_total !== null &&
          proposal.estimated_total !== undefined && (
            <div className="total-row">
              <strong>Estimated Investment — Priced Items</strong>
              <strong>{formatCurrency(proposal.estimated_total)}</strong>
            </div>
          )}

        {tbdItems.length > 0 && (
          <p className="hint">
            Additional TBD items are not included in this total and will be priced
            after quantities are confirmed.
          </p>
        )}

        {proposal.generated_proposal && (
          <div className="proposal-draft">
            <ProposalMarkdown content={proposal.generated_proposal} />
          </div>
        )}
      </section>

      {/* Assumptions / Clarifying Questions / Risks */}
      {(proposal.assumptions_json?.length ?? 0) +
        (proposal.clarifying_questions_json?.length ?? 0) +
        (proposal.risk_flags_json?.length ?? 0) >
        0 && (
        <div className="review-sections">
          {(proposal.assumptions_json?.length ?? 0) > 0 && (
            <section className="card">
              <h2 className="section-title">Assumptions</h2>
              <ul>
                {proposal.assumptions_json!.map((item, idx) => (
                  <li key={idx}>{item}</li>
                ))}
              </ul>
            </section>
          )}

          {(proposal.clarifying_questions_json?.length ?? 0) > 0 && (
            <section className="card">
              <h2 className="section-title">Clarifying Questions</h2>
              <ul>
                {proposal.clarifying_questions_json!.map((item, idx) => (
                  <li key={idx}>{item}</li>
                ))}
              </ul>
            </section>
          )}

          {(proposal.risk_flags_json?.length ?? 0) > 0 && (
            <section className="card">
              <h2 className="section-title">Risk Flags</h2>
              <ul>
                {proposal.risk_flags_json!.map((item, idx) => (
                  <li key={idx}>{item}</li>
                ))}
              </ul>
            </section>
          )}
        </div>
      )}

      {/* Delivery */}
      {proposal.status === "SENT" && (
        <section className="card">
          <h2 className="section-title">Delivery</h2>
          <dl className="delivery-grid">
            <div>
              <dt>Status</dt>
              <dd>Sent</dd>
            </div>
            <div>
              <dt>Sent</dt>
              <dd>{proposal.sent_at ? formatDateTime(proposal.sent_at) : "—"}</dd>
            </div>
          </dl>
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
            Send Proposal Email
          </button>
        )}

        {proposal.status === "SENT" && proposal.sent_at && (
          <p className="sent-message">
            ✓ Proposal Sent on {formatDateTime(proposal.sent_at)}.
          </p>
        )}

        {proposal.status === "SENT" && !proposal.sent_at && (
          <p className="sent-message">✓ Proposal Sent.</p>
        )}
      </section>
    </div>
  );
}
