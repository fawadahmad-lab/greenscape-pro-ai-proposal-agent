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


def compute_line_total(item: PricingItem, quantity: float | None) -> float:
    """Return quantity * unit_price. If quantity is missing, line_total is 0."""
    if quantity is None:
        return 0.0
    return round(quantity * float(item.unit_price), 2)


def build_pricing_breakdown(
    scope: ScopeExtraction, catalog: Sequence[PricingItem]
) -> PricingBreakdown:
    """Convert validated AI scope into deterministic pricing."""
    line_items: list[PricedLineItem] = []
    for scope_item in scope.scope_items:
        matched = match_catalog_item(
            scope_item.requested_work, scope_item.catalog_item_name, catalog
        )
        if matched is None:
            logger.warning(
                "No catalog match for scope item: %s", scope_item.requested_work
            )
            line_items.append(
                PricedLineItem(
                    requested_work=scope_item.requested_work,
                    catalog_item_name="Unmatched",
                    category="Unmatched",
                    unit="",
                    unit_price=0.0,
                    quantity=scope_item.quantity,
                    line_total=0.0,
                    confidence=scope_item.confidence,
                    quantity_uncertain=True,
                    notes="No matching catalog item found. Requires manual pricing.",
                )
            )
            continue

        quantity = scope_item.quantity
        quantity_uncertain = quantity is None or scope_item.confidence < QUANTITY_UNCERTAIN_THRESHOLD

        line_items.append(
            PricedLineItem(
                requested_work=scope_item.requested_work,
                catalog_item_name=matched.name,
                category=matched.category,
                unit=matched.unit,
                unit_price=float(matched.unit_price),
                quantity=quantity,
                line_total=compute_line_total(matched, quantity),
                confidence=scope_item.confidence,
                quantity_uncertain=quantity_uncertain,
                notes=scope_item.notes,
            )
        )

    estimated_total = round(sum(item.line_total for item in line_items), 2)
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
