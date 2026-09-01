import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ArrowLeft } from "lucide-react";
import ProposalReview from "../components/ProposalReview";
import StatusBadge from "../components/StatusBadge";
import { SkeletonCard } from "../components/Loading";
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

  if (loading) {
    return (
      <div>
        <p className="back-link">
          <Link to="/">
            <ArrowLeft size={16} aria-hidden="true" /> Back to Dashboard
          </Link>
        </p>
        <SkeletonCard count={2} />
      </div>
    );
  }
  if (error && !proposal)
    return (
      <div>
        <p className="back-link">
          <Link to="/">
            <ArrowLeft size={16} aria-hidden="true" /> Back to Dashboard
          </Link>
        </p>
        <div className="error-state" role="alert">
          {error}
        </div>
      </div>
    );
  if (!proposal)
    return (
      <div>
        <p className="back-link">
          <Link to="/">
            <ArrowLeft size={16} aria-hidden="true" /> Back to Dashboard
          </Link>
        </p>
        <div className="error-state">Proposal not found.</div>
      </div>
    );

  return (
    <div>
      <p className="back-link">
        <Link to="/">
          <ArrowLeft size={16} aria-hidden="true" /> Back to Dashboard
        </Link>
      </p>

      <div className="page-header">
        <div>
          <h1 className="page-header-h1">Proposal #{proposal.id}</h1>
          <p className="page-header-sub" style={{ marginTop: 6 }}>
            Created {new Date(proposal.created_at).toLocaleDateString("en-US", {
              year: "numeric",
              month: "long",
              day: "numeric",
            })}
          </p>
        </div>
        <div className="page-header-actions">
          <StatusBadge status={proposal.status} />
        </div>
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
