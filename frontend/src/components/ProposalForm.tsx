import { useState } from "react";
import type { FormEvent } from "react";
import { Sparkles, User, Mail, MapPin, FileText, Info } from "lucide-react";
import Button from "./Button";
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
      <div className="form-layout">
        <div className="form-field">
          <label htmlFor="clientName">
            <User size={15} style={{ verticalAlign: "-2px", marginRight: 6 }} />
            Client Name
          </label>
          <input
            id="clientName"
            type="text"
            value={clientName}
            onChange={(e) => setClientName(e.target.value)}
            required
            autoComplete="name"
            placeholder="e.g. John Smith"
          />
        </div>

        <div className="form-field">
          <label htmlFor="clientEmail">
            <Mail size={15} style={{ verticalAlign: "-2px", marginRight: 6 }} />
            Client Email
          </label>
          <input
            id="clientEmail"
            type="email"
            value={clientEmail}
            onChange={(e) => setClientEmail(e.target.value)}
            required
            autoComplete="email"
            placeholder="e.g. john@example.com"
          />
          <span className="form-helper">The proposal email will be sent here.</span>
        </div>

        <div className="form-field form-field--full">
          <label htmlFor="projectAddress">
            <MapPin size={15} style={{ verticalAlign: "-2px", marginRight: 6 }} />
            Project Address
          </label>
          <input
            id="projectAddress"
            type="text"
            value={projectAddress}
            onChange={(e) => setProjectAddress(e.target.value)}
            required
            placeholder="e.g. 123 Oak St, Phoenix AZ 85001"
          />
        </div>

        <div className="form-field form-field--full form-field--primary">
          <label htmlFor="siteWalkNotes">
            <FileText size={15} style={{ verticalAlign: "-2px", marginRight: 6 }} />
            Site Walk Notes
          </label>
          <textarea
            id="siteWalkNotes"
            value={siteWalkNotes}
            onChange={(e) => setSiteWalkNotes(e.target.value)}
            required
            rows={12}
            placeholder={
              "Paste Marcus's unstructured site-walk notes here.\n\nExample:\nBackyard needs a paver patio about 500 sq ft. Side yard has dead grass, wants artificial turf. Small fire pit near the patio, add a pergola for shade. Water feature along the back fence. Remove the old cracked concrete first..."
            }
          />
          <span className="form-helper">
            <Info size={13} style={{ verticalAlign: "-2px", marginRight: 4 }} />
            The AI extracts scope, pricing, and assumptions from these notes.
          </span>
        </div>
      </div>

      {error && (
        <div className="form-error" role="alert">
          {error}
        </div>
      )}

      <div className="form-actions">
        <Button
          type="submit"
          size="lg"
          loading={submitting}
          disabled={submitting}
          icon={<Sparkles size={19} />}
        >
          {submitting ? "Creating Proposal…" : "Generate Proposal"}
        </Button>
      </div>
    </form>
  );
}
