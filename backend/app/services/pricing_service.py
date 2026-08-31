"""Deterministic pricing service.

Matches AI-extracted scope items to the pricing catalog and computes line
totals and the estimated total in plain Python. The LLM is never asked to
perform arithmetic.
"""

import logging
from typing import Sequence

from sqlalchemy.orm import Session

from app.models.pricing_item import PricingItem
from app.models.proposal import Proposal
from app.schemas.proposal import PricedLineItem, PricingBreakdown, ScopeExtraction

logger = logging.getLogger(__name__)

# Below this confidence threshold a quantity is treated as uncertain and
# the item is flagged rather than silently priced at a fabricated value.
QUANTITY_UNCERTAIN_THRESHOLD = 0.5


def get_active_pricing_items(db: Session) -> Sequence[PricingItem]:
    """Return all active pricing catalog items."""
    return db.query(PricingItem).filter(PricingItem.active.is_(True)).all()


def match_catalog_item(
    scope_work: str, catalog_name: str | None, catalog: Sequence[PricingItem]
) -> PricingItem | None:
    """Match a scope item to a catalog item by name (normalized) or fallback."""
    if not catalog_name:
        return None

    normalized = catalog_name.strip().lower()
    # Exact name match first.
    for item in catalog:
        if item.name.strip().lower() == normalized:
            return item
    # Substring match (catalog name contained in requested name or vice versa).
    for item in catalog:
        item_name = item.name.strip().lower()
        if normalized in item_name or item_name in normalized:
            return item
    return None


def compute_line_total(
    unit_price: float | None, quantity: float | None
) -> float | None:
    """Return quantity * unit_price, or None if either is unknown (TBD)."""
    if unit_price is None or quantity is None:
        return None
    return round(quantity * unit_price, 2)


def build_pricing_breakdown(
    scope: ScopeExtraction, catalog: Sequence[PricingItem]
) -> PricingBreakdown:
    """Convert validated AI scope into deterministic pricing.

    A line item is "priced" (Quantum contributes to the total) only when both a
    numeric quantity and a known unit price are present. Otherwise it is a TBD
    item: it stays visible with unit_price/line_total of None (rendered as TBD)
    and is excluded from estimated_total. estimated_total is null when no item
    is priced.
    """
    line_items: list[PricedLineItem] = []
    for scope_item in scope.scope_items:
        matched = match_catalog_item(
            scope_item.requested_work, scope_item.catalog_item_name, catalog
        )
        if matched is None:
            line_items.append(
                PricedLineItem(
                    requested_work=scope_item.requested_work,
                    catalog_item_name="Unmatched",
                    category="Unmatched",
                    unit="",
                    unit_price=None,
                    quantity=scope_item.quantity,
                    line_total=None,
                    confidence=scope_item.confidence,
                    quantity_uncertain=True,
                    is_priced=False,
                    notes="No matching catalog item found. Requires manual pricing.",
                )
            )
            continue

        quantity = scope_item.quantity
        unit_price = float(matched.unit_price)
        line_total = compute_line_total(unit_price, quantity)
        is_priced = line_total is not None
        quantity_uncertain = (
            quantity is None or scope_item.confidence < QUANTITY_UNCERTAIN_THRESHOLD
        )

        line_items.append(
            PricedLineItem(
                requested_work=scope_item.requested_work,
                catalog_item_name=matched.name,
                category=matched.category,
                unit=matched.unit,
                unit_price=unit_price if is_priced else None,
                quantity=quantity,
                line_total=line_total,
                confidence=scope_item.confidence,
                quantity_uncertain=quantity_uncertain or not is_priced,
                is_priced=is_priced,
                notes=scope_item.notes,
            )
        )

    priced = [item.line_total for item in line_items if item.is_priced]
    estimated_total = round(sum(priced), 2) if priced else None
    return PricingBreakdown(line_items=line_items, estimated_total=estimated_total)


def apply_pricing_to_proposal(
    db: Session,
    proposal: Proposal,
    scope: ScopeExtraction,
    breakdown: PricingBreakdown,
) -> None:
    """Persist computed pricing onto the proposal record."""
    proposal.estimated_total = breakdown.estimated_total
    proposal.pricing_json = [item.model_dump() for item in breakdown.line_items]
    db.commit()
