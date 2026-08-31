"""Tests for deterministic pricing calculations."""

from app.models.pricing_item import PricingItem
from app.services.pricing_service import (
    build_pricing_breakdown,
    compute_line_total,
    match_catalog_item,
)
from app.schemas.proposal import ScopeExtraction, ScopeItem


def _catalog():
    return [
        PricingItem(
            name="Paver Patio Installation",
            category="Hardscape",
            unit="square foot",
            unit_price=18.00,
        ),
        PricingItem(
            name="Artificial Turf Installation",
            category="Turf",
            unit="square foot",
            unit_price=9.50,
        ),
        PricingItem(
            name="Pergola",
            category="Structures",
            unit="each",
            unit_price=6800.00,
        ),
    ]


def test_line_total_simple():
    assert compute_line_total(18.0, 500) == 9000.0


def test_line_total_missing_quantity_is_tbd():
    # Unknown quantity -> TBD, not $0.00.
    assert compute_line_total(18.0, None) is None
    # Unknown unit price -> TBD, not $0.00.
    assert compute_line_total(None, 500) is None


def test_match_catalog_item_exact():
    item = match_catalog_item("anything", "Paver Patio Installation", _catalog())
    assert item is not None
    assert item.name == "Paver Patio Installation"


def test_match_catalog_item_case_insensitive():
    item = match_catalog_item("anything", "paver patio installation", _catalog())
    assert item is not None


def test_match_catalog_item_no_match_returns_none():
    item = match_catalog_item("anything", "Unknown Item", _catalog())
    assert item is None


def test_breakdown_sums_line_totals_deterministically():
    scope = ScopeExtraction(
        project_summary="Patio + turf",
        scope_items=[
            ScopeItem(
                requested_work="Add paver patio",
                catalog_item_name="Paver Patio Installation",
                quantity=500,
                confidence=0.9,
            ),
            ScopeItem(
                requested_work="Add turf",
                catalog_item_name="Artificial Turf Installation",
                quantity=300,
                confidence=0.85,
            ),
        ],
    )
    breakdown = build_pricing_breakdown(scope, _catalog())
    # 500 * 18 + 300 * 9.50 = 9000 + 2850 = 11850
    assert breakdown.estimated_total == 11850.0
    assert len(breakdown.line_items) == 2
    assert all(item.is_priced for item in breakdown.line_items)


def test_breakdown_marks_uncertain_quantity():
    scope = ScopeExtraction(
        project_summary="Pergola",
        scope_items=[
            ScopeItem(
                requested_work="Add a pergola",
                catalog_item_name="Pergola",
                quantity=None,
                confidence=0.3,
            ),
        ],
    )
    breakdown = build_pricing_breakdown(scope, _catalog())
    item = breakdown.line_items[0]
    assert item.quantity is None
    assert item.quantity_uncertain is True
    assert item.is_priced is False
    # TBD quantity -> line total and unit price are unknown, not $0.00.
    assert item.line_total is None
    assert item.unit_price is None
    # All items TBD -> estimated_total is null.
    assert breakdown.estimated_total is None


def test_breakdown_unmatched_item_flagged_not_priced():
    scope = ScopeExtraction(
        project_summary="Special item",
        scope_items=[
            ScopeItem(
                requested_work="Build a custom cantilever",
                catalog_item_name="Cantilever Umbrella",
                quantity=1,
                confidence=0.9,
            ),
        ],
    )
    breakdown = build_pricing_breakdown(scope, _catalog())
    item = breakdown.line_items[0]
    assert item.catalog_item_name == "Unmatched"
    assert item.is_priced is False
    assert item.line_total is None
    assert breakdown.estimated_total is None


def test_breakdown_mixed_priced_and_tbd_total_is_priced_only():
    scope = ScopeExtraction(
        project_summary="Patio + lighting",
        scope_items=[
            ScopeItem(
                requested_work="Add paver patio",
                catalog_item_name="Paver Patio Installation",
                quantity=700,
                confidence=0.95,
            ),
            ScopeItem(
                requested_work="Add lighting",
                catalog_item_name="Lighting",
                quantity=None,
                confidence=0.2,
            ),
        ],
    )
    breakdown = build_pricing_breakdown(scope, _catalog())
    priced = [i for i in breakdown.line_items if i.is_priced]
    tbd = [i for i in breakdown.line_items if not i.is_priced]
    # Only the priced patio (700 * 18 = 12600) contributes to the total.
    assert breakdown.estimated_total == 12600.0
    assert len(priced) == 1
    assert len(tbd) == 1
    assert tbd[0].line_total is None
    assert tbd[0].unit_price is None
