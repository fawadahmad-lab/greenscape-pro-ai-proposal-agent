"""Seed the pricing catalog with representative demo line items.

NOTE: These are SAMPLE/DEMO pricing values for the assessment. They do NOT
represent Greenscape Pro's actual prices. The client's real catalog is a
200+ line-item spreadsheet that was not provided for this take-home.
"""

from sqlalchemy.orm import Session

from app.models.pricing_item import PricingItem

# name, category, description, unit, unit_price
DEMO_PRICING_ITEMS: list[tuple[str, str, str, str, float]] = [
    (
        "Artificial Turf Installation",
        "Turf",
        "Installed artificial grass over prepared base.",
        "square foot",
        9.50,
    ),
    (
        "Paver Patio Installation",
        "Hardscape",
        "Interlocking concrete paver patio over compacted base.",
        "square foot",
        18.00,
    ),
    (
        "Travertine Patio Installation",
        "Hardscape",
        "Premium travertine tile patio installation.",
        "square foot",
        28.00,
    ),
    (
        "Pergola",
        "Structures",
        "Freestanding or attached aluminum/wood pergola with shade option.",
        "each",
        6800.00,
    ),
    (
        "Fire Pit",
        "Hardscape",
        "Custom gas or wood-burning fire pit with seating ring.",
        "each",
        4200.00,
    ),
    (
        "Outdoor Kitchen",
        "Structures",
        "Custom outdoor kitchen with grill, countertop, and storage.",
        "each",
        24000.00,
    ),
    (
        "Water Feature",
        "Water",
        "Custom decorative water feature including pump and recirculation.",
        "each",
        8500.00,
    ),
    (
        "Retaining Wall",
        "Hardscape",
        "Segmental retaining wall with drainage backfill.",
        "square foot",
        42.00,
    ),
    (
        "Irrigation Zone",
        "Irrigation",
        "New irrigation zone with heads, valves, and controller connection.",
        "each",
        380.00,
    ),
    (
        "Landscape Lighting Fixture",
        "Lighting",
        "Installed landscape lighting fixture with transformer tap.",
        "each",
        165.00,
    ),
    (
        "Demolition",
        "Site Prep",
        "Removal and disposal of existing hardscape or turf.",
        "square foot",
        3.50,
    ),
    (
        "Grading",
        "Site Prep",
        "Site grading and soil preparation for new construction.",
        "square foot",
        2.75,
    ),
    (
        "Plant Installation",
        "Planting",
        "Installation of shrub, tree, or perennial including soil.",
        "each",
        95.00,
    ),
    (
        "Gravel Installation",
        "Hardscape",
        "Decomposed granite or washed gravel over landscape fabric.",
        "square foot",
        7.00,
    ),
    (
        "Drainage Solution",
        "Drainage",
        "French drain or catch basin drainage solution.",
        "each",
        1400.00,
    ),
    (
        "Synthetic Putting Green",
        "Turf",
        "Installed synthetic putting green with fringe.",
        "square foot",
        24.00,
    ),
    (
        "Pool Deck",
        "Hardscape",
        "Cooling deck or pavers around pool area.",
        "square foot",
        22.00,
    ),
    (
        "Pergola with Lighting",
        "Structures",
        "Pergola with integrated LED lighting package.",
        "each",
        7600.00,
    ),
    (
        "Wood Privacy Fence",
        "Structures",
        "Custom cedar privacy fence installed.",
        "linear foot",
        55.00,
    ),
    (
        "Design Consultation",
        "Design",
        "On-site design consultation and layout plan.",
        "each",
        500.00,
    ),
]


def seed_pricing_catalog(db: Session) -> int:
    """Insert demo pricing items if the catalog is empty. Returns count added."""
    existing = db.query(PricingItem).count()
    if existing > 0:
        return 0

    added = 0
    for name, category, description, unit, unit_price in DEMO_PRICING_ITEMS:
        db.add(
            PricingItem(
                name=name,
                category=category,
                description=description,
                unit=unit,
                unit_price=unit_price,
                active=True,
            )
        )
        added += 1
    db.commit()
    return added
