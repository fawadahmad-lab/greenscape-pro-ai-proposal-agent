import { BrowserRouter, Routes, Route, Link } from "react-router-dom";
import { Sprout, Plus } from "lucide-react";
import Dashboard from "./pages/Dashboard";
import NewProposal from "./pages/NewProposal";
import ProposalDetail from "./pages/ProposalDetail";

export default function App() {
  return (
    <BrowserRouter>
      <div className="app-shell">
        <header className="app-header">
          <div className="app-header-inner">
            <Link to="/" className="brand" aria-label="Greenscape Pro home">
              <span className="brand-mark" aria-hidden="true">
                <Sprout size={20} strokeWidth={2.2} />
              </span>
              <span>
                <span className="brand-name">Greenscape Pro</span>
                <span className="brand-tag">Proposal Copilot</span>
              </span>
            </Link>
            <div className="header-actions">
              <Link to="/proposals/new" className="btn btn-ghost-light btn-icon-sm">
                <Plus size={18} aria-hidden="true" />
                <span className="btn-label">New Proposal</span>
              </Link>
            </div>
          </div>
        </header>
        <main className="app-main">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/proposals/new" element={<NewProposal />} />
            <Route path="/proposals/:id" element={<ProposalDetail />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}
