"""Tests for AI output parsing and Pydantic validation."""

from app.services.ai_service import _parse_scope
from app.schemas.proposal import ScopeExtraction


def test_parse_valid_json():
    raw = (
        '{"project_summary": "Patio", '
        '"scope_items": [{"requested_work": "Paver patio", '
        '"catalog_item_name": "Paver Patio Installation", "quantity": 500, '
        '"confidence": 0.9, "notes": ""}], '
        '"assumptions": [], "clarifying_questions": [], "risk_flags": []}'
    )
    scope = _parse_scope(raw)
    assert scope is not None
    assert isinstance(scope, ScopeExtraction)
    assert scope.project_summary == "Patio"
    assert scope.scope_items[0].quantity == 500


def test_parse_json_within_markdown_fence():
    raw = (
        '```json\n'
        '{"project_summary": "P", "scope_items": [], '
        '"assumptions": ["a"], "clarifying_questions": [], "risk_flags": []}\n'
        '```'
    )
    scope = _parse_scope(raw)
    assert scope is not None
    assert scope.assumptions == ["a"]


def test_parse_json_with_prose_preamble_and_trailer():
    # The model occasionally prepends/append prose around the JSON.
    raw = (
        'Here is the scope for this project:\n'
        '{"project_summary": "Patio", "scope_items": [], '
        '"assumptions": ["a"], "clarifying_questions": [], "risk_flags": []}\n'
        'Please review and let me know if you need changes.'
    )
    scope = _parse_scope(raw)
    assert scope is not None
    assert scope.project_summary == "Patio"


def test_parse_json_with_triple_backtick_preamble():
    raw = (
        '```\n'
        'Here is the JSON:\n'
        '{"project_summary": "P", "scope_items": [], '
        '"assumptions": [], "clarifying_questions": [], "risk_flags": []}\n'
        '```'
    )
    scope = _parse_scope(raw)
    assert scope is not None
    assert scope.project_summary == "P"


def test_parse_invalid_json_returns_none():
    assert _parse_scope("this is not json") is None


def test_parse_structurally_invalid_returns_none():
    # A field with the wrong type (string where a list is expected) fails
    # Pydantic validation, returning None and triggering a controlled retry.
    raw = (
        '{"project_summary": "P", "assumptions": "not-a-list", '
        '"scope_items": [], "clarifying_questions": [], "risk_flags": []}'
    )
    assert _parse_scope(raw) is None
