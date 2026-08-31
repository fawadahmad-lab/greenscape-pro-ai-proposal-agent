"""Proposal API routes: CRUD, AI generation, approval, and sending."""

import logging
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.proposal import Proposal, ProposalStatus
from app.schemas.proposal import (
    ProposalCreate,
    ProposalListOut,
    ProposalOut,
)
from app.services import ai_service, pricing_service
from app.services.notification_service import NotificationError, send_proposal_email

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/proposals", tags=["proposals"])


def _get_proposal_or_404(db: Session, proposal_id: int) -> Proposal:
    proposal = db.get(Proposal, proposal_id)
    if proposal is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Proposal not found."
        )
    return proposal


@router.post("", response_model=ProposalOut, status_code=status.HTTP_201_CREATED)
def create_proposal(payload: ProposalCreate, db: Session = Depends(get_db)) -> Proposal:
    """Create a proposal in DRAFT status."""
    proposal = Proposal(
        client_name=payload.client_name.strip(),
        client_email=payload.client_email,
        project_address=payload.project_address.strip(),
        site_walk_notes=payload.site_walk_notes.strip(),
        status=ProposalStatus.DRAFT,
    )
    db.add(proposal)
    db.commit()
    db.refresh(proposal)
    logger.info("Created proposal id=%s for %s", proposal.id, proposal.client_name)
    return proposal


@router.get("", response_model=list[ProposalListOut])
def list_proposals(db: Session = Depends(get_db)) -> list[Proposal]:
    """Return proposals ordered newest first."""
    return (
        db.query(Proposal)
        .order_by(Proposal.created_at.desc())
        .all()
    )


@router.get("/{proposal_id}", response_model=ProposalOut)
def get_proposal(proposal_id: int, db: Session = Depends(get_db)) -> Proposal:
    """Return full proposal details."""
    return _get_proposal_or_404(db, proposal_id)


@router.post("/{proposal_id}/generate", response_model=ProposalOut)
def generate_proposal(
    proposal_id: int, db: Session = Depends(get_db)
) -> Proposal:
    """Core workflow: AI scope extraction -> deterministic pricing -> draft."""
    proposal = _get_proposal_or_404(db, proposal_id)

    # State guard: only DRAFT or FAILED (retry) may generate.
    if proposal.status not in (ProposalStatus.DRAFT, ProposalStatus.FAILED):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot generate a proposal in status {proposal.status.value}. "
            "Only DRAFT or FAILED proposals can be generated.",
        )

    # Mark GENERATING first so a failure never leaves it stuck.
    proposal.status = ProposalStatus.GENERATING
    db.commit()

    try:
        catalog = pricing_service.get_active_pricing_items(db)
        if not catalog:
            raise RuntimeError("Pricing catalog is empty; no pricing available.")

        # Step 1: AI scope extraction (validated with Pydantic).
        scope = ai_service.extract_scope(proposal.site_walk_notes, catalog)

        # Defensive guard: never silently persist an empty scope. This should
        # be unreachable because extract_scope rejects empty scopes, but it
        # keeps the data flow correct even if future changes weaken that.
        if not scope.scope_items:
            raise ValueError(
                "The AI did not identify any concrete work from these notes. "
                "Please review the notes and try again."
            )

        # Step 2: Deterministic pricing.
        breakdown = pricing_service.build_pricing_breakdown(scope, catalog)

        # Step 3: AI proposal draft generation.
        draft = ai_service.generate_proposal_draft(
            client_name=proposal.client_name,
            project_address=proposal.project_address,
            project_summary=scope.project_summary,
            scope=scope,
            breakdown=breakdown,
        )

        # Persist everything.
        proposal.status = ProposalStatus.NEEDS_REVIEW
        proposal.project_summary = scope.project_summary
        proposal.scope_json = [item.model_dump() for item in scope.scope_items]
        proposal.pricing_json = [item.model_dump() for item in breakdown.line_items]
        proposal.estimated_total = (
            Decimal(str(breakdown.estimated_total))
            if breakdown.estimated_total is not None
            else None
        )
        proposal.assumptions_json = scope.assumptions
        proposal.clarifying_questions_json = scope.clarifying_questions
        proposal.risk_flags_json = scope.risk_flags
        proposal.generated_proposal = draft
        db.commit()
        db.refresh(proposal)

        logger.info(
            "Generated proposal id=%s estimated_total=%s status=%s",
            proposal.id,
            proposal.estimated_total,
            proposal.status,
        )
        return proposal

    except Exception as exc:
        db.rollback()
        # Ensure we never leave the proposal permanently stuck in GENERATING.
        proposal.status = ProposalStatus.FAILED
        db.commit()
        db.refresh(proposal)
        logger.exception(
            "Proposal generation failed for id=%s: %s", proposal_id, exc
        )
        # Do not leak secrets or stack traces.
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=(
                "Proposal generation failed. The proposal has been marked FAILED "
                "and can be retried. "
                + ("The AI could not interpret the notes. " if isinstance(exc, ValueError) else "")
            ),
        ) from exc


@router.post("/{proposal_id}/approve", response_model=ProposalOut)
def approve_proposal(proposal_id: int, db: Session = Depends(get_db)) -> Proposal:
    """Human approval endpoint. Requires NEEDS_REVIEW state."""
    proposal = _get_proposal_or_404(db, proposal_id)

    if proposal.status != ProposalStatus.NEEDS_REVIEW:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Cannot approve a proposal in status {proposal.status.value}. "
                "Only NEEDS_REVIEW proposals can be approved."
            ),
        )

    from datetime import datetime, timezone

    proposal.status = ProposalStatus.APPROVED
    proposal.approved_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(proposal)
    logger.info("Approved proposal id=%s", proposal.id)
    return proposal


@router.post("/{proposal_id}/send", response_model=ProposalOut)
def send_proposal(proposal_id: int, db: Session = Depends(get_db)) -> Proposal:
    """Send an approved proposal via Resend email. Requires APPROVED state."""
    proposal = _get_proposal_or_404(db, proposal_id)

    # The backend is the final authority on allowed transitions. Reject any
    # state other than APPROVED, including SENT (no re-sending).
    if proposal.status != ProposalStatus.APPROVED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Cannot send a proposal in status {proposal.status.value}. "
                "Only APPROVED proposals can be sent."
            ),
        )

    try:
        send_proposal_email(proposal)
    except NotificationError as exc:
        # Do not mark SENT on failure. Preserve APPROVED so it can be retried.
        db.rollback()
        logger.error("Send failed for proposal id=%s: %s", proposal_id, exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc

    from datetime import datetime, timezone

    proposal.status = ProposalStatus.SENT
    proposal.sent_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(proposal)
    logger.info("Sent proposal id=%s via email", proposal.id)
    return proposal
