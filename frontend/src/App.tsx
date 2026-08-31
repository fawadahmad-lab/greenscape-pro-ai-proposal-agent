import { BrowserRouter, Routes, Route } from "react-router-dom";
import Dashboard from "./pages/Dashboard";
import NewProposal from "./pages/NewProposal";
import ProposalDetail from "./pages/ProposalDetail";

export default function App() {
  return (
    <BrowserRouter>
      <div className="app-shell">
        <header className="app-header">
          <span className="app-title">Greenscape Pro</span>
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
