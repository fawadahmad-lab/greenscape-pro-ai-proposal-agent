"""AI service wrapping the Groq API.

Two responsibilities, both using the LLM strictly as an interpreter/drafter:
  1. extract_scope  -> turn unstructured site notes into structured scope JSON
  2. generate_proposal -> draft professional proposal text given finalized data

The LLM never computes prices. All arithmetic happens in pricing_service.
"""

import json
import logging
from typing import Sequence

from pydantic import ValidationError

from groq import Groq

from app.core.config import get_settings
from app.models.pricing_item import PricingItem
from app.schemas.proposal import PricingBreakdown, ScopeExtraction

logger = logging.getLogger(__name__)

settings = get_settings()

MAX_RETRIES = 1


def _client() -> Groq:
    if not settings.groq_api_key:
        raise RuntimeError("GROQ_API_KEY is not configured.")
    return Groq(api_key=settings.groq_api_key)


def _catalog_context(catalog: Sequence[PricingItem]) -> str:
    """Build a compact description of the pricing catalog for the prompt."""
    lines = [
        f"{item.name} — {item.category} — per {item.unit} (sample/demo unit price: ${float(item.unit_price):,.2f})"
        for item in catalog
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Step 1: Scope extraction
# ---------------------------------------------------------------------------


def _extract_scope_once(
    notes: str, catalog_context: str
) -> tuple[ScopeExtraction | None, str]:
    """Call Groq once; return (validated_scope, raw_text)."""
    system_prompt = (
        "You are an expert estimator for a premium residential landscape and "
        "hardscape design-build company in Phoenix, Arizona. You interpret "
        "unstructured site-walk notes and convert them into a structured "
        "project scope.\n\n"
        "Rules:\n"
        "- Do NOT invent project details. If information is missing or ambiguous, "
        "record it as an assumption, clarifying question, or risk flag.\n"
        "- Only set a quantity when it is explicitly stated or can be reasonably "
        "inferred from the notes. Otherwise leave it null and flag uncertainty.\n"
        "- Map each requested work item to the closest catalog item by name.\n"
        "- Respond with STRICT JSON ONLY, no prose, matching this schema:\n"
        '{\n'
        '  "project_summary": "string",\n'
        '  "scope_items": [\n'
        '    {\n'
        '      "requested_work": "string",\n'
        '      "catalog_item_name": "string | null",\n'
        '      "quantity": number | null,\n'
        '      "confidence": number between 0 and 1,\n'
        '      "notes": "string"\n'
        '    }\n'
        '  ],\n'
        '  "assumptions": ["string"],\n'
        '  "clarifying_questions": ["string"],\n'
        '  "risk_flags": ["string"]\n'
        '}\n'
    )

    user_prompt = (
        "Available pricing catalog items:\n"
        f"{catalog_context}\n\n"
        "Site walk notes from Marcus:\n"
        f"{notes}"
    )

    client = _client()
    response = client.chat.completions.create(
        model=settings.groq_model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.2,
    )
    raw = response.choices[0].message.content or ""
    return _parse_scope(raw), raw


def _extract_json_object(text: str) -> dict | None:
    """Best-effort extraction of the first top-level JSON object in arbitrary
    model output (handles markdown fences, code block tags, preamble prose,
    and trailing commentary). Returns None if no valid object is found."""
    source = text.strip()

    # 1) Try the whole string first (fast path for clean output).
    try:
        parsed = json.loads(source)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass

    # 2) Locate the outermost balanced braces and try each candidate span,
    #    choosing the longest one that parses as a JSON object.
    stack: list[int] = []
    spans: list[tuple[int, int]] = []
    for i, ch in enumerate(source):
        if ch == "{":
            stack.append(i)
        elif ch == "}":
            if stack:
                start = stack.pop()
                spans.append((start, i + 1))

    for end, start in sorted(
        ((e - s, s) for s, e in spans), reverse=True
    ):
        start_i = start
        end_i = start + end
        candidate = source[start_i:end_i]
        try:
            parsed = json.loads(candidate)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            continue

    return None


def _parse_scope(raw: str) -> ScopeExtraction | None:
    """Parse raw model output into a validated ScopeExtraction, or None."""
    data = _extract_json_object(raw)
    if data is None:
        logger.warning("AI returned non-JSON output; treating as parse failure.")
        return None
    try:
        return ScopeExtraction.model_validate(data)
    except ValidationError as exc:
        logger.warning("AI output failed Pydantic validation: %s", exc)
        return None


def extract_scope(notes: str, catalog: Sequence[PricingItem]) -> ScopeExtraction:
    """Extract structured scope with one controlled repair/retry."""
    catalog_context = _catalog_context(catalog)

    scope, raw = _extract_scope_once(notes, catalog_context)
    attempt = 0
    while scope is None and attempt < MAX_RETRIES:
        logger.info("Retrying scope extraction (attempt %d).", attempt + 1)
        scope, raw = _extract_scope_once(notes, catalog_context)
        attempt += 1

    if scope is None:
        logger.error("Scope extraction failed after retries. Raw tail: %s", raw[-500:])
        raise ValueError(
            "The AI could not produce a valid structured scope from these notes. "
            "Please review the notes and try again, or run generation again later."
        )
    return scope


# ---------------------------------------------------------------------------
# Step 2: Proposal draft generation
# ---------------------------------------------------------------------------


def generate_proposal_draft(
    client_name: str,
    project_address: str,
    project_summary: str,
    scope: ScopeExtraction,
    breakdown: PricingBreakdown,
) -> str:
    """Generate a professional proposal draft given finalized data."""
    line_items_text = "\n".join(
        f"- {item.requested_work} | {item.catalog_item_name} | "
        f"qty {item.quantity if item.quantity is not None else 'TBD'} {item.unit} | "
        f"${item.line_total:,.2f}"
        for item in breakdown.line_items
    )

    assumptions_text = "\n".join(f"- {a}" for a in scope.assumptions) or "- None noted."
    questions_text = (
        "\n".join(f"- {q}" for q in scope.clarifying_questions) or "- None pending."
    )
    risks_text = "\n".join(f"- {r}" for r in scope.risk_flags) or "- None noted."

    system_prompt = (
        "You are a senior proposal writer for a premium residential landscape and "
        "hardscape design-build company in Phoenix, Arizona. Write a clear, "
        "professional, high-end proposal draft.\n\n"
        "Rules:\n"
        "- Base the proposal ONLY on the provided structured scope and pricing.\n"
        "- Do NOT invent guarantees, permit approvals, or HOA approvals.\n"
        "- Clearly label the result as a DRAFT ESTIMATE pending final human review.\n"
        "- Organize the proposal into these sections: Project Overview, Scope of "
        "Work, Estimated Investment, Assumptions / Items Requiring Confirmation, "
        "and Next Steps.\n"
    )

    user_prompt = (
        f"Client: {client_name}\n"
        f"Project address: {project_address}\n\n"
        f"Project summary: {project_summary}\n\n"
        "Scope of work:\n"
        f"{line_items_text}\n\n"
        f"Estimated total: ${breakdown.estimated_total:,.2f}\n\n"
        "Assumptions:\n"
        f"{assumptions_text}\n\n"
        "Clarifying questions:\n"
        f"{questions_text}\n\n"
        "Risk flags:\n"
        f"{risks_text}\n\n"
        "Write the professional proposal draft now. Format with clear markdown "
        "headings so it renders well."
    )

    client = _client()
    response = client.chat.completions.create(
        model=settings.groq_model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.4,
    )
    draft = response.choices[0].message.content or ""
    if not draft.strip():
        logger.error("Proposal draft generation returned empty content.")
        raise ValueError("The AI returned an empty proposal draft. Please try again.")
    return draft
