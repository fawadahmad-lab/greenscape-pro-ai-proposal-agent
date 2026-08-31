# Greenscape Pro AI Proposal Copilot

A focused, production-style full-stack application that turns unstructured
site-walk notes into professional, priced landscaping proposals for a premium
Phoenix residential hardscape and landscape design-build company.

This is an AI Developer take-home assessment delivering one explainable P0
workflow end-to-end: **create proposal → AI scope extraction → deterministic
pricing → AI draft → human approval → send → persist**.

---

## Overview

Greenscape Pro generates custom proposals manually. Marcus walks the site,
takes unstructured notes, interprets them into scope, prices them against a
200+ line-item spreadsheet, and drafts a proposal. The whole flow takes
**6–9 days**, and Greenscape estimates losing **35–40% of qualified
opportunities** to faster competitors.

This application collapses that cycle to minutes while keeping a human in the
loop: the AI interprets and drafts, Python computes deterministic pricing, and
a human must approve before anything is sent.

## Why this P0

Greenscape Pro is **quote-constrained, not lead-constrained**. Paid acquisition
is already working (roughly $25K–$30K/month with healthy Meta performance). The
bottleneck is converting qualified leads into proposals quickly. Therefore this
P0 targets proposal throughput first — before any lead-generation or post-sign
automation — because increasing inbound leads without fixing the conversion
bottleneck would amplify it.

---

## Architecture

```
 Browser (React + Vite)
        ↓  HTTP / JSON
      FastAPI
      /      \
 PostgreSQL     Groq API
 (Supabase)     (LLM: scope extraction + drafting)
      \
       Slack Webhook (send notification)
```

- **Frontend** — React + Vite + TypeScript SPA, plain CSS, no component library.
- **Backend** — FastAPI, SQLAlchemy 2.x, Pydantic v2, httpx.
- **Database** — PostgreSQL (via Supabase in production).
- **LLM** — Groq API directly (model from `GROQ_MODEL` env var).
- **External integration** — Slack incoming webhook for send notifications.

## Key Engineering Decisions

1. **Direct Groq API, not an agent framework.** No LangChain/LangGraph. The
   workflow is two sequential, well-defined LLM calls. Simpler is more reliable
   and far easier to explain.
2. **The LLM interprets; it never does arithmetic.** Groq extracts structured
   scope from notes and drafts prose. All pricing is computed in plain Python
   in `pricing_service.py`.
3. **Python performs deterministic pricing.** `quantity × unit_price`, summed,
   computed by application code so prices are auditable and reproducible.
4. **Pydantic validates AI output.** Raw LLM output is parsed and validated
   against `ScopeExtraction`. If validation fails, there is one controlled
   retry, then the proposal is marked `FAILED` rather than inventing data.
5. **Human approval is required before external action.** The backend is the
   final authority: a proposal can only be sent after it is `APPROVED`.
6. **PostgreSQL provides persistence and auditability.** Status transitions and
   timestamps (approved_at, sent_at) are stored so the full lifecycle is traceable.

---

## API

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/health` | Liveness check |
| `POST` | `/api/proposals` | Create a proposal (`DRAFT`) |
| `GET` | `/api/proposals` | List proposals, newest first |
| `GET` | `/api/proposals/{id}` | Full proposal details |
| `POST` | `/api/proposals/{id}/generate` | AI scope extraction + pricing + draft |
| `POST` | `/api/proposals/{id}/approve` | Human approval (`NEEDS_REVIEW` → `APPROVED`) |
| `POST` | `/api/proposals/{id}/send` | Send via Slack (`APPROVED` → `SENT`) |

### Proposal status lifecycle

```
DRAFT → GENERATING → NEEDS_REVIEW → APPROVED → SENT
   ↑        │
   └────────┴── FAILED (on generation error; retry allowed)
```

---

## Repository Structure

```
greenscape-ai-proposal-copilot/
├── backend/
│   ├── app/
│   │   ├── api/proposals.py        # CRUD + generate/approve/send routes
│   │   ├── core/                   # config, database
│   │   ├── models/                 # Proposal, PricingItem ORM models
│   │   ├── schemas/proposal.py      # Pydantic schemas incl. AI ScopeExtraction
│   │   ├── services/               # ai_service, pricing_service, notification_service
│   │   ├── seed/pricing_catalog.py # 20 demo pricing items
│   │   ├── main.py                 # FastAPI app, CORS, health, startup seeding
│   │   └── dependencies.py
│   ├── tests/                      # workflow, pricing, AI-parsing tests
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── api/, components/, pages/, types/
│   │   ├── App.tsx, main.tsx, index.css, vite-env.d.ts
│   ├── package.json, vite.config.ts, tsconfig*.json, index.html
│   └── .env.example
├── strategy.md                     # AI opportunity ranking + rationale
└── README.md
```

---

## Setup

Prerequisites: Python 3.12+, Node 18+, and PostgreSQL (or a Supabase project).

### Environment Variables

Backend (`backend/.env`):

| Variable | Description |
|----------|-------------|
| `DATABASE_URL` | SQLAlchemy PostgreSQL connection string (Supabase in prod) |
| `GROQ_API_KEY` | Groq API key for LLM calls |
| `GROQ_MODEL` | Groq model name to use (e.g. `llama-3.3-70b-versatile`) |
| `SLACK_WEBHOOK_URL` | Slack incoming-webhook URL for send notifications |
| `CORS_ORIGINS` | Comma-separated allowed origins (no wildcard in production) |

Frontend (`frontend/.env`):

| Variable | Description |
|----------|-------------|
| `VITE_API_BASE_URL` | Deployed backend base URL. Leave unset in dev to use the Vite proxy. |

### Running Locally

Backend:

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # then fill in real values
python -m uvicorn app.main:app --reload --port 8000
```

The app creates tables and seeds the demo pricing catalog automatically on startup.

Frontend:

```bash
cd frontend
npm install
npm run dev                 # http://localhost:5173
```

The Vite dev server proxies `/api` to `http://localhost:8000`, so no
`VITE_API_BASE_URL` is needed locally.

### Tests

```bash
cd backend
source venv/bin/activate
python -m pytest tests/ -q
```

---

## Deployment

Backend and frontend deploy independently.

**Backend** — run the FastAPI app behind any ASGI-friendly host (e.g. a
managed service or container). Set all environment variables. Configure CORS to
the deployed frontend origin. Use Supabase PostgreSQL for `DATABASE_URL`.

**Frontend** — build with `npm run build` and serve `dist/` from any static
host. Set `VITE_API_BASE_URL` to the deployed backend at build time (or use a
reverse proxy that routes `/api` to the backend on the same origin).

Never commit `.env` files; they are git-ignored.

---

## Assumptions

- Greenscape Pro's actual 200+ line-item pricing spreadsheet was **not
  provided** for this assessment. This implementation uses a representative
  **seeded demo pricing catalog** (20 clearly-labeled SAMPLE/DEMO items) so the
  deterministic pricing engine can be exercised end-to-end.
- The **Slack webhook** is the representative external integration for this
  assessment. In production, the send notification would integrate with
  **GoHighLevel**, which the client stated is the primary system of record.

## Trade-offs

For the 24-hour assessment, this application prioritizes a **narrow,
correct end-to-end workflow** over production breadth. It intentionally does
**not** include authentication, multi-user permissions, background job queues,
complex third-party integrations (GoHighLevel/Stripe/CompanyCam/Jobber), file
upload, OCR, or a full pricing-spreadsheet ingestion pipeline. These are
documented follow-ups rather than scope creep here.

## Explicitly Out of Scope (per assessment)

No authentication, multi-user permissions, real GoHighLevel/Stripe/CompanyCam/
Jobber integrations, file upload, OCR, agent orchestration, background workers,
WebSockets, LangChain/LangGraph, vector DBs, RAG, chatbot, or multiple agents.
A human must always approve before anything is sent.

---

## Strategy

See **[strategy.md](./strategy.md)** for the ranked AI opportunity analysis and
the reasoning behind prioritizing the proposal copilot.
