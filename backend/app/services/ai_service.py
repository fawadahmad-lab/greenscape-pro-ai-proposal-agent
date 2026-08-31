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

from groq import Groq, GroqError

from app.core.config import get_settings
from app.models.pricing_item import PricingItem
from app.schemas.proposal import PricingBreakdown, ScopeExtraction

logger = logging.getLogger(__name__)

settings = get_settings()


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
    notes: str, catalog_context: str, retry: bool = False
) -> tuple[ScopeExtraction | None, str]:
    """Call Groq once; return (validated_scope, raw_text)."""
    base_rules = (
        "Rules:\n"
        "- Do NOT invent project details. If information is missing or ambiguous, "
        "record it as an assumption, clarifying question, or risk flag.\n"
        "- Only set a quantity when it is explicitly stated or can be reasonably "
        "inferred from the notes. Otherwise leave it null and flag uncertainty.\n"
        "- Map each requested work item to the closest catalog item by name.\n"
    )
    if retry:
        # Stronger explicit instruction used for the single controlled retry.
        base_rules += (
            "- CRITICAL: The site-walk notes describe real, concrete work. You MUST "
            "map every distinct task into its own entry in scope_items. Never return "
            "an empty scope_items array when the notes describe specific work, and "
            "never omit a requested task from the notes.\n"
        )
    system_prompt = (
        "You are an expert estimator for a premium residential landscape and "
        "hardscape design-build company in Phoenix, Arizona. You interpret "
        "unstructured site-walk notes and convert them into a structured "
        "project scope.\n\n"
        f"{base_rules}"
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
    try:
        return _chat_scope_completion(
            client, system_prompt, user_prompt, {"type": "json_object"}
        )
    except GroqError:
        # JSON mode can intermittently fail validation on some models. Fall
        # back to a plain completion within the same attempt so a transient
        # JSON-mode failure does not waste an attempt.
        logger.warning("JSON mode failed; falling back to plain completion.")
        return _chat_scope_completion(client, system_prompt, user_prompt, None)


def _chat_scope_completion(
    client, system_prompt: str, user_prompt: str, response_format
) -> tuple[ScopeExtraction | None, str]:
    """Run one scope chat completion; return (validated_scope, raw_text)."""
    kwargs: dict = {
        "model": settings.groq_model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.2,
    }
    if response_format is not None:
        kwargs["response_format"] = response_format
    response = client.chat.completions.create(**kwargs)
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
    """Extract structured scope with deterministic validation and one retry.

    The retry is only triggered for empty/malformed/clearly-inconsistent output.
    Valid output that contains TBD quantities or prices is accepted as-is (it is
    a legitimate result and must NOT be retried).
    """
    catalog_context = _catalog_context(catalog)
    max_attempts = max(1, settings.groq_extract_max_attempts)

    for attempt in range(1, max_attempts + 1):
        scope = None
        raw = ""
        try:
            scope, raw = _extract_scope_once(
                notes, catalog_context, retry=attempt > 1
            )
        except GroqError as exc:
            logger.warning(
                "Scope extraction attempt %d/%d raised Groq API error: %s",
                attempt,
                max_attempts,
                exc,
            )
            continue
        reason = _scope_reason(scope, raw)
        if reason is None:
            return scope
        logger.warning(
            "Scope extraction attempt %d/%d failed: %s",
            attempt,
            max_attempts,
            reason,
        )

    logger.error("Scope extraction failed after %d attempts.", max_attempts)
    raise ValueError(
        "The AI could not produce a valid structured scope from these notes. "
        "Please review the notes and try again, or run generation again later."
    )


def _scope_reason(scope: ScopeExtraction | None, raw: str) -> str | None:
    """Return a human-readable failure reason, or None if the scope is usable."""
    if scope is None:
        return "no valid JSON scope returned" if not raw.strip() else "malformed output"
    if len(scope.scope_items) == 0:
        return "scope contained no scope items"
    if not (scope.project_summary or "").strip():
        return "scope contained no project summary"
    return None


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
        f"{'$' + format(item.line_total, ',.2f') if item.line_total is not None else 'TBD'}"
        for item in breakdown.line_items
    )

    assumptions_text = "\n".join(f"- {a}" for a in scope.assumptions) or "- None noted."
    questions_text = (
        "\n".join(f"- {q}" for q in scope.clarifying_questions) or "- None pending."
    )
    risks_text = "\n".join(f"- {r}" for r in scope.risk_flags) or "- None noted."

    system_prompt = (
        "You are a senior proposal writer for Greenscape Pro, a premium "
        "residential landscape and hardscape design-build company in Phoenix, "
        "Arizona. Write a clear, professional, high-end proposal draft.\n\n"
        "Rules:\n"
        "- The company is Greenscape Pro - Premium Residential Landscape & "
        "Hardscape Design-Build, Phoenix, Arizona. Use this exact identity; do "
        "NOT place core line items too high in the document.\n"
        "- Base the proposal ONLY on the provided structured scope and pricing.\n"
        "- Do NOT invent guarantees, permit approvals, or HOA approvals.\n"
        "- Clearly label the result as a DRAFT ESTIMATE pending final human review.\n"
        "- Organize the proposal into these sections: Project Overview, Scope of "
        "Work, Estimated Investment, Assumptions / Items Requiring Confirmation, "
        "and Next Steps.\n"
        "- NEVER use placeholder brackets such as [Your Company Name], [Your "
        "Name], [Contact Information], or [Your Location]. Use only the company "
        "identity above. If an employee/contact name is unknown, omit it rather "
        "than leaving a placeholder.\n"
    )

    estimated_text = (
        f"${breakdown.estimated_total:,.2f}"
        if breakdown.estimated_total is not None
        else "TBD (all items pending pricing)"
    )

    user_prompt = (
        f"Client: {client_name}\n"
        f"Project address: {project_address}\n\n"
        f"Project summary: {project_summary}\n\n"
        "Scope of work:\n"
        f"{line_items_text}\n\n"
        f"Estimated investment (priced items only): {estimated_text}\n\n"
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
