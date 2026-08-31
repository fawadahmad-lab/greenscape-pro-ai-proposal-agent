import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import ProposalReview from "../components/ProposalReview";
import StatusBadge from "../components/StatusBadge";
import { getProposal, generateProposal, approveProposal, sendProposal } from "../api/proposals";
import type { Proposal } from "../types/proposal";

export default function ProposalDetail() {
  const { id } = useParams<{ id: string }>();
  const proposalId = Number(id);

  const [proposal, setProposal] = useState<Proposal | null>(null);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function refresh() {
    const data = await getProposal(proposalId);
    setProposal(data);
  }

  useEffect(() => {
    getProposal(proposalId)
      .then(setProposal)
      .catch((err) =>
        setError(err instanceof Error ? err.message : "Failed to load proposal.")
      )
      .finally(() => setLoading(false));
  }, [proposalId]);

  // Poll while the proposal is being generated so the status updates in place.
  useEffect(() => {
    if (!proposal || proposal.status !== "GENERATING") return;
    const timer = setInterval(async () => {
      try {
        await refresh();
      } catch {
        clearInterval(timer);
      }
    }, 3000);
    return () => clearInterval(timer);
  }, [proposal?.status]);

  async function runAction(action: () => Promise<Proposal>) {
    setActionLoading(true);
    setError(null);
    try {
      const updated = await action();
      setProposal(updated);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Action failed.");
    } finally {
      setActionLoading(false);
    }
  }

  if (loading) return <p>Loading proposal…</p>;
  if (error && !proposal) return <div className="form-error">{error}</div>;
  if (!proposal) return <p>Proposal not found.</p>;

  return (
    <div>
      <p>
        <Link to="/">← Back to Dashboard</Link>
      </p>
      <div className="page-header">
        <h1>
          Proposal #{proposal.id}{" "}
          <span
            style={{
              display: "inline-flex",
              verticalAlign: "middle",
              marginLeft: 8,
            }}
          >
            <StatusBadge status={proposal.status} />
          </span>
        </h1>
      </div>
      <ProposalReview
        proposal={proposal}
        disabled={actionLoading}
        onGenerate={() => runAction(() => generateProposal(proposal.id))}
        onApprove={() => runAction(() => approveProposal(proposal.id))}
        onSend={() => runAction(() => sendProposal(proposal.id))}
        error={error}
      />
    </div>
  );
}
