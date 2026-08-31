# Greenscape Pro Proposal Copilot — Backend

FastAPI + SQLAlchemy 2.x + PostgreSQL (Supabase-compatible) + Groq API.

## Setup

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in DATABASE_URL, GROQ_API_KEY, etc.
python -m uvicorn app.main:app --reload --port 8000
```

On startup the app creates tables and seeds 20 demo pricing items.

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `DATABASE_URL` | Yes | PostgreSQL connection string |
| `GROQ_API_KEY` | Yes (for AI) | Groq API key |
| `GROQ_MODEL` | No | Default `llama-3.3-70b-versatile` |
| `SLACK_WEBHOOK_URL` | Yes (to send) | Slack incoming webhook |
| `CORS_ORIGINS` | No | Comma-separated origins, default `http://localhost:5173` |

## Tests

```bash
source venv/bin/activate
python -m pytest tests/ -q
```

## How the generate workflow works

1. Validate the proposal is in an allowed state (`DRAFT`/`FAILED`), set `GENERATING`.
2. Load active pricing catalog items.
3. Call Groq to extract structured scope (`ScopeExtraction`) — validated by Pydantic,
   with one controlled retry on failure.
4. Match scope items to catalog items and compute pricing **deterministically** in
   Python. Uncertain quantities are flagged, never fabricated.
5. Call Groq to draft a professional proposal given the finalized scope + pricing.
6. Persist everything and set `NEEDS_REVIEW`.

On any error, the proposal is set to `FAILED` (never left stuck in `GENERATING`),
and a safe error message is returned (no keys, no stack traces).
