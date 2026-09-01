import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { ArrowLeft } from "lucide-react";
import ProposalForm from "../components/ProposalForm";
import { createProposal } from "../api/proposals";
import type { ProposalCreate } from "../types/proposal";

export default function NewProposal() {
  const navigate = useNavigate();
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(payload: ProposalCreate) {
    setSubmitting(true);
    setError(null);
    try {
      const proposal = await createProposal(payload);
      navigate(`/proposals/${proposal.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create proposal.");
      setSubmitting(false);
    }
  }

  return (
    <div>
      <p className="back-link">
        <Link to="/">
          <ArrowLeft size={16} aria-hidden="true" /> Back to Dashboard
        </Link>
      </p>

      <div className="page-header">
        <div>
          <h1 className="page-header-h1">New Proposal</h1>
          <p className="page-header-sub">
            Enter the client and project details, then let Greenscape Pro draft the
            proposal from your site-walk notes.
          </p>
        </div>
      </div>

      <ProposalForm onSubmit={handleSubmit} submitting={submitting} error={error} />
    </div>
  );
}
