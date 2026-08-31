import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
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
      <p>
        <Link to="/">← Back to Dashboard</Link>
      </p>
      <h1>New Proposal</h1>
      <ProposalForm onSubmit={handleSubmit} submitting={submitting} error={error} />
    </div>
  );
}
