"""Proposal ORM model with status enum and JSON audit fields."""

import enum
from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, Enum, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class ProposalStatus(str, enum.Enum):
    """Lifecycle states of a proposal."""

    DRAFT = "DRAFT"
    GENERATING = "GENERATING"
    NEEDS_REVIEW = "NEEDS_REVIEW"
    APPROVED = "APPROVED"
    SENT = "SENT"
    FAILED = "FAILED"


class Proposal(Base):
    """A residential landscape/hardscape proposal."""

    __tablename__ = "proposals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    client_name: Mapped[str] = mapped_column(String(200))
    client_email: Mapped[str] = mapped_column(String(200))
    project_address: Mapped[str] = mapped_column(String(300))
    site_walk_notes: Mapped[str] = mapped_column(Text)

    status: Mapped[ProposalStatus] = mapped_column(
        Enum(ProposalStatus, name="proposal_status"),
        default=ProposalStatus.DRAFT,
        index=True,
    )

    project_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    scope_json: Mapped[list | None] = mapped_column(JSON, nullable=True)
    pricing_json: Mapped[list | None] = mapped_column(JSON, nullable=True)
    estimated_total: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    assumptions_json: Mapped[list | None] = mapped_column(JSON, nullable=True)
    clarifying_questions_json: Mapped[list | None] = mapped_column(JSON, nullable=True)
    risk_flags_json: Mapped[list | None] = mapped_column(JSON, nullable=True)
    generated_proposal: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )
    approved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    sent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
