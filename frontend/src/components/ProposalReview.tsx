import { useState } from "react";
import {
  User,
  MapPin,
  FileText,
  Camera,
  Sparkles,
  Send,
  Check,
  AlertTriangle,
  ShieldAlert,
  HelpCircle,
  Truck,
  BadgeCheck,
} from "lucide-react";
import StatusBadge from "./StatusBadge";
import ProposalMarkdown from "./ProposalMarkdown";
import ConfirmDialog from "./ConfirmDialog";
import Button from "./Button";
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
  const [confirmOpen, setConfirmOpen] = useState(false);
  const pricedItems = proposal.pricing_json ?? [];
  const tbdItems = pricedItems.filter((item) => !item.is_priced);
  const hasScope = (proposal.scope_json?.length ?? 0) > 0;

  return (
    <div className="proposal-detail">
      {/* Client Information */}
      <section className="card">
        <div className="section-head">
          <span className="section-icon">
            <User size={18} />
          </span>
          <h2>Client Information</h2>
        </div>
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
            <dt>Project Address</dt>
            <dd>
              <MapPin
                size={14}
                style={{ verticalAlign: "-2px", marginRight: 4 }}
                aria-hidden="true"
              />
              {proposal.project_address}
            </dd>
          </div>
          <div>
            <dt>Status</dt>
            <dd style={{ paddingTop: 2 }}>
              <StatusBadge status={proposal.status} />
            </dd>
          </div>
        </dl>
      </section>

      {/* Site Walk Notes */}
      <section className="card">
        <div className="section-head">
          <span className="section-icon">
            <Camera size={18} />
          </span>
          <h2>Original Site Walk Notes</h2>
        </div>
        <div className="notes pre-wrap">{proposal.site_walk_notes}</div>
      </section>

      {/* Generated Proposal */}
      <section className="card">
        <div className="section-head">
          <span className="section-icon">
            <FileText size={18} />
          </span>
          <h2>AI Generated Proposal</h2>
        </div>

        {proposal.project_summary && (
          <p className="project-summary">{proposal.project_summary}</p>
        )}

        {hasScope && (
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
                {proposal.scope_json!.map((item, idx) => {
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
                      <td style={{ whiteSpace: "nowrap" }}>
                        {formatQuantity(priced?.quantity ?? item.quantity)}
                      </td>
                      <td>{priced?.unit ?? ""}</td>
                      <td style={{ whiteSpace: "nowrap" }}>
                        {formatCurrency(priced?.unit_price ?? null)}
                      </td>
                      <td style={{ whiteSpace: "nowrap", fontWeight: 600 }}>
                        {formatCurrency(priced?.line_total ?? null)}
                      </td>
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
              <span className="total-label">Estimated Investment — Priced Items</span>
              <span className="total-value">
                {formatCurrency(proposal.estimated_total)}
              </span>
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
            <div className="section-title">Proposal Content</div>
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
              <div className="section-head">
                <span className="section-icon">
                  <ShieldAlert size={18} />
                </span>
                <h2>Assumptions</h2>
              </div>
              <ul>
                {proposal.assumptions_json!.map((item, idx) => (
                  <li key={idx}>{item}</li>
                ))}
              </ul>
            </section>
          )}

          {(proposal.clarifying_questions_json?.length ?? 0) > 0 && (
            <section className="card">
              <div className="section-head">
                <span className="section-icon">
                  <HelpCircle size={18} />
                </span>
                <h2>Clarifying Questions</h2>
              </div>
              <ul>
                {proposal.clarifying_questions_json!.map((item, idx) => (
                  <li key={idx}>{item}</li>
                ))}
              </ul>
            </section>
          )}

          {(proposal.risk_flags_json?.length ?? 0) > 0 && (
            <section className="card">
              <div className="section-head">
                <span className="section-icon">
                  <AlertTriangle size={18} />
                </span>
                <h2>Risk Flags</h2>
              </div>
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
          <div className="section-head">
            <span className="section-icon">
              <Truck size={18} />
            </span>
            <h2>Delivery</h2>
          </div>
          <dl className="delivery-grid">
            <div>
              <dt>Status</dt>
              <dd>Sent</dd>
            </div>
            <div>
              <dt>Sent At</dt>
              <dd>{proposal.sent_at ? formatDateTime(proposal.sent_at) : "—"}</dd>
            </div>
          </dl>
        </section>
      )}

      {error && (
        <div className="error-state" role="alert">
          {error}
        </div>
      )}

      {/* Actions */}
      <section className="card action-bar">
        {proposal.status === "DRAFT" && (
          <Button
            variant="primary"
            size="lg"
            loading={disabled}
            disabled={disabled || !canGenerate(proposal.status)}
            onClick={onGenerate}
            icon={<Sparkles size={19} />}
          >
            Generate Proposal with AI
          </Button>
        )}

        {proposal.status === "GENERATING" && (
          <p className="generating-message">
            <span className="btn-spinner" aria-hidden="true" /> Generating proposal
            with AI… this can take a short while.
          </p>
        )}

        {proposal.status === "FAILED" && (
          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            <p className="error-message">
              Generation failed. The proposal was not left stuck; you can review the
              notes and retry generation.
            </p>
            <div>
              <Button
                variant="primary"
                onClick={onGenerate}
                loading={disabled}
                disabled={disabled}
                icon={<Sparkles size={18} />}
              >
                Retry Generation
              </Button>
            </div>
          </div>
        )}

        {proposal.status === "NEEDS_REVIEW" && (
          <Button
            variant="success"
            size="lg"
            onClick={onApprove}
            loading={disabled}
            disabled={disabled || !canApprove(proposal.status)}
            icon={<BadgeCheck size={19} />}
          >
            Approve Proposal
          </Button>
        )}

        {proposal.status === "APPROVED" && (
          <Button
            variant="primary"
            size="lg"
            onClick={() => setConfirmOpen(true)}
            loading={disabled}
            disabled={disabled || !canSend(proposal.status)}
            icon={<Send size={18} />}
          >
            Send Proposal Email
          </Button>
        )}

        {proposal.status === "SENT" && (
          <p className="sent-message">
            <Check size={18} aria-hidden="true" />
            Proposal Sent on{" "}
            {proposal.sent_at ? formatDateTime(proposal.sent_at) : "the scheduled date"}.
          </p>
        )}
      </section>

      {/* Send confirmation dialog */}
      <ConfirmDialog
        open={confirmOpen}
        title="Send Proposal?"
        confirmLabel="Send Proposal"
        busy={disabled}
        tone="primary"
        onConfirm={() => {
          onSend();
          setConfirmOpen(false);
        }}
        onClose={() => setConfirmOpen(false)}
      >
        <p>
          This will email the proposal to{" "}
          <strong>
            {proposal.client_name} ({proposal.client_email})
          </strong>{" "}
          for Proposal <strong>#{proposal.id}</strong>.
        </p>
        <p style={{ marginBottom: 0 }}>
          Once sent, the proposal status will update to <strong>Sent</strong>.
        </p>
      </ConfirmDialog>
    </div>
  );
}
