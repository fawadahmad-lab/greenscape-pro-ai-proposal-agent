"""Tests for the proposal email builder (placeholder scrubbing and TBD handling)."""

from app.services.notification_service import (
    _build_html,
    _is_in_service_area,
    _scrub_placeholders,
)
from app.models.proposal import Proposal, ProposalStatus


def _proposal(**overrides):
    defaults = {
        "client_name": "Jane Doe",
        "client_email": "jane@example.com",
        "project_address": "4120 W Northview Ave, Phoenix AZ",
        "project_summary": "Backyard patio.",
        "status": ProposalStatus.APPROVED,
        "scope_json": [],
        "pricing_json": [],
        "estimated_total": None,
        "assumptions_json": [],
        "clarifying_questions_json": [],
        "risk_flags_json": [],
        "generated_proposal": "Draft.",
        "site_walk_notes": "notes",
    }
    defaults.update(overrides)
    return Proposal(**defaults)


def test_scrub_placeholders_removes_brackets():
    text = (
        "Company: [Your Company Name]\n"
        "Name: [Your Name]\n"
        "Contact: [Contact Information]\n"
        "Some real content."
    )
    scrubbed = _scrub_placeholders(text)
    assert "[Your Company Name]" not in scrubbed
    assert "[Your Name]" not in scrubbed
    assert "[Contact Information]" not in scrubbed
    assert "Some real content." in scrubbed


def test_scrub_placeholders_none_returns_empty():
    assert _scrub_placeholders(None) == ""


def test_build_html_flags_out_of_area_address():
    proposal = _proposal(project_address="Street #23, Ali Road, Islamabad, Pakistan")
    html = _build_html(proposal)
    assert "service area" in html
    # The client address must remain unchanged (no invented Phoenix address).
    assert "Islamabad, Pakistan" in html
    assert "Phoenix yard" not in html


def test_is_in_service_area():
    assert _is_in_service_area("4120 W Northview Ave, Phoenix AZ")
    assert _is_in_service_area("7425 E Shea Blvd, Scottsdale, Arizona")
    assert not _is_in_service_area("Street #23, Ali Road, Islamabad, Pakistan")
    # Missing address is not flagged.
    assert _is_in_service_area(None)


def test_build_html_null_total_does_not_show_zero():
    proposal = _proposal(
        estimated_total=None,
        pricing_json=[
            {
                "requested_work": "Lighting",
                "catalog_item_name": "Unmatched",
                "quantity": None,
                "unit": "",
                "unit_price": None,
                "line_total": None,
            }
        ],
    )
    html = _build_html(proposal)
    assert "$0.00" not in html
    assert "pending" in html.lower()
    assert "TBD" in html
    # Unknown quantity must render TBD, never a literal "None".
    assert ">None<" not in html
    assert "None</td>" not in html
    # Option B: the full generated Markdown must NOT be embedded in the email.
    assert "Proposal Details" not in html
    assert "generated_proposal" not in html


def test_build_html_excludes_full_markdown_proposal():
    proposal = _proposal(
        generated_proposal="# DRAFT ESTIMATE\n\n## Scope\n\nSome markdown body."
    )
    html = _build_html(proposal)
    # The generated Markdown must not appear in the email at all.
    assert "Proposal Details" not in html
    assert "# DRAFT ESTIMATE" not in html
    assert "## Scope" not in html


def test_build_html_items_pending_pricing_section():
    proposal = _proposal(
        estimated_total=12600.0,
        pricing_json=[
            {
                "requested_work": "Add paver patio",
                "catalog_item_name": "Paver Patio Installation",
                "quantity": 700,
                "unit": "sf",
                "unit_price": 18.0,
                "line_total": 12600.0,
            },
            {
                "requested_work": "Add lighting",
                "catalog_item_name": "Unmatched",
                "quantity": None,
                "unit": "",
                "unit_price": None,
                "line_total": None,
            },
        ],
    )
    html = _build_html(proposal)
    # Distinct "Items Pending Pricing" section, and the TBD item is named.
    assert "Items Pending Pricing" in html
    assert "<li>Add lighting</li>" in html
    # The priced-only total is shown as the numeric estimate.
    assert "$12,600.00" in html
    assert "not included in this total" in html
    # No literal "None" anywhere in the rendered output.
    assert "None" not in html


def test_build_html_omits_empty_sections():
    proposal = _proposal(
        assumptions_json=[],
        clarifying_questions_json=[],
        estimated_total=100.0,
        pricing_json=[
            {
                "requested_work": "Small job",
                "catalog_item_name": "Item",
                "quantity": 1,
                "unit": "each",
                "unit_price": 100.0,
                "line_total": 100.0,
            }
        ],
    )
    html = _build_html(proposal)
    # Empty assumptions/questions sections are omitted entirely (no "None").
    assert "Assumptions" not in html
    assert "Clarifying Questions" not in html
    assert "None" not in html
