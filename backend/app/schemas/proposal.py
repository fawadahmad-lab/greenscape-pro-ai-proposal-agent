"""Pydantic schemas for proposal API requests, responses, and AI output."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.proposal import ProposalStatus


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------


class ProposalCreate(BaseModel):
    """Payload for creating a new proposal."""

    client_name: str = Field(min_length=1, max_length=200)
    client_email: EmailStr
    project_address: str = Field(min_length=1, max_length=300)
    site_walk_notes: str = Field(min_length=1)


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------


class PricingItemOut(BaseModel):
    """Serialized pricing catalog item."""

    id: int
    name: str
    category: str
    description: str
    unit: str
    unit_price: float
    active: bool

    model_config = ConfigDict(from_attributes=True)


class ProposalListOut(BaseModel):
    """Lightweight proposal entry for the dashboard list."""

    id: int
    client_name: str
    status: ProposalStatus
    estimated_total: float | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ProposalOut(BaseModel):
    """Full proposal detail response."""

    id: int
    client_name: str
    client_email: str
    project_address: str
    site_walk_notes: str
    status: ProposalStatus
    project_summary: str | None
    scope_json: list[Any] | None
    pricing_json: list[Any] | None
    estimated_total: float | None
    assumptions_json: list[str] | None
    clarifying_questions_json: list[str] | None
    risk_flags_json: list[str] | None
    generated_proposal: str | None
    created_at: datetime
    updated_at: datetime
    approved_at: datetime | None
    sent_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# AI scope extraction schemas
# ---------------------------------------------------------------------------


class ScopeItem(BaseModel):
    """A single requested scope item extracted from site notes."""

    requested_work: str
    catalog_item_name: str | None = None
    quantity: float | None = Field(default=None, gt=0)
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    notes: str = ""


class ScopeExtraction(BaseModel):
    """Structured output expected from the Groq scope-extraction step."""

    project_summary: str = ""
    scope_items: list[ScopeItem] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    clarifying_questions: list[str] = Field(default_factory=list)
    risk_flags: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Internal structured pricing output
# ---------------------------------------------------------------------------


class PricedLineItem(BaseModel):
    """A scope item matched to a catalog item with a deterministic price."""

    requested_work: str
    catalog_item_name: str
    category: str
    unit: str
    unit_price: float | None
    quantity: float | None
    line_total: float | None
    confidence: float
    quantity_uncertain: bool = False
    is_priced: bool = True
    notes: str = ""


class PricingBreakdown(BaseModel):
    """Deterministically calculated pricing breakdown.

    estimated_total is the sum of priced line items only. It is null when no
    line item has a known quantity and unit price (all TBD). TBD items are
    kept visible and are never shown as $0.00.
    """

    line_items: list[PricedLineItem]
    estimated_total: float | None
