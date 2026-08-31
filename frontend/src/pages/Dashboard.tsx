import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import ProposalList from "../components/ProposalList";
import { listProposals } from "../api/proposals";
import type { ProposalListItem } from "../types/proposal";

export default function Dashboard() {
  const [proposals, setProposals] = useState<ProposalListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    listProposals()
      .then(setProposals)
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load proposals."))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div>
      <div className="page-header">
        <h1>Greenscape Pro AI Proposal Copilot</h1>
        <Link to="/proposals/new" className="btn btn-primary">
          New Proposal
        </Link>
      </div>

      {loading && <p>Loading proposals…</p>}
      {error && <div className="form-error">{error}</div>}
      {!loading && !error && <ProposalList proposals={proposals} />}
    </div>
  );
}
