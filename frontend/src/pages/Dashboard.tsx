import { useEffect, useState } from "react";
import { Plus, AlertTriangle } from "lucide-react";
import ProposalList from "../components/ProposalList";
import { SkeletonCard } from "../components/Loading";
import Button from "../components/Button";
import { listProposals } from "../api/proposals";
import type { ProposalListItem } from "../types/proposal";

export default function Dashboard() {
  const [proposals, setProposals] = useState<ProposalListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    listProposals()
      .then(setProposals)
      .catch((err) =>
        setError(err instanceof Error ? err.message : "Failed to load proposals.")
      )
      .finally(() => setLoading(false));
  }, []);

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-header-h1">Proposals</h1>
          <p className="page-header-sub">
            Create, generate, and manage proposals for your landscape projects.
          </p>
        </div>
        <div className="page-header-actions">
          <Button as="link" to="/proposals/new" icon={<Plus size={18} />}>
            New Proposal
          </Button>
        </div>
      </div>

      {loading && <SkeletonCard count={3} />}

      {!loading && error && (
        <div className="error-state" role="alert">
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <AlertTriangle size={18} aria-hidden="true" />
            <strong>Couldn't load proposals.</strong>
          </div>
          {error}
        </div>
      )}

      {!loading && !error && <ProposalList proposals={proposals} />}
    </div>
  );
}
