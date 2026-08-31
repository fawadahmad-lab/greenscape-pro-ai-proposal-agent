import { useState } from "react";
import type { FormEvent } from "react";
import type { ProposalCreate } from "../types/proposal";

interface ProposalFormProps {
  onSubmit: (payload: ProposalCreate) => Promise<void>;
  submitting: boolean;
  error?: string | null;
}

export default function ProposalForm({
  onSubmit,
  submitting,
  error,
}: ProposalFormProps) {
  const [clientName, setClientName] = useState("");
  const [clientEmail, setClientEmail] = useState("");
  const [projectAddress, setProjectAddress] = useState("");
  const [siteWalkNotes, setSiteWalkNotes] = useState("");

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    await onSubmit({
      client_name: clientName,
      client_email: clientEmail,
      project_address: projectAddress,
      site_walk_notes: siteWalkNotes,
    });
  }

  return (
    <form className="proposal-form" onSubmit={handleSubmit}>
      <div className="form-field">
        <label htmlFor="clientName">Client Name</label>
        <input
          id="clientName"
          type="text"
          value={clientName}
          onChange={(e) => setClientName(e.target.value)}
          required
          placeholder="e.g. John Smith"
        />
      </div>

      <div className="form-field">
        <label htmlFor="clientEmail">Client Email</label>
        <input
          id="clientEmail"
          type="email"
          value={clientEmail}
          onChange={(e) => setClientEmail(e.target.value)}
          required
          placeholder="e.g. john@example.com"
        />
      </div>

      <div className="form-field">
        <label htmlFor="projectAddress">Project Address</label>
        <input
          id="projectAddress"
          type="text"
          value={projectAddress}
          onChange={(e) => setProjectAddress(e.target.value)}
          required
          placeholder="e.g. 123 Oak St, Phoenix AZ"
        />
      </div>

      <div className="form-field">
        <label htmlFor="siteWalkNotes">Site Walk Notes</label>
        <textarea
          id="siteWalkNotes"
          value={siteWalkNotes}
          onChange={(e) => setSiteWalkNotes(e.target.value)}
          required
          rows={10}
          placeholder={
            "Paste Marcus's unstructured site-walk notes here.\n\nExample:\nBackyard needs a paver patio about 500 sq ft. Side yard has dead grass, wants artificial turf. Small fire pit near the patio, add a pergola for shade. Water feature along the back fence. Remove the old cracked concrete first..."
          }
        />
      </div>

      {error && <div className="form-error">{error}</div>}

      <button type="submit" className="btn btn-primary" disabled={submitting}>
        {submitting ? "Creating..." : "Create Proposal"}
      </button>
    </form>
  );
}
