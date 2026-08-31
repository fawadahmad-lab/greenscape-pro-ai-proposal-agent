"""Tests for proposal CRUD and status transition guardrails."""

from datetime import datetime, timezone

from app.models.proposal import Proposal, ProposalStatus
from app.services import ai_service
from app.services.notification_service import NotificationError
from app.schemas.proposal import ScopeExtraction, PricingBreakdown, PricedLineItem


def _draft_proposal(db, **overrides):
    defaults = {
        "client_name": "Test Client",
        "client_email": "test@example.com",
        "project_address": "1 Main St",
        "site_walk_notes": "Some notes.",
        "status": ProposalStatus.DRAFT,
    }
    defaults.update(overrides)
    p = Proposal(**defaults)
    db.add(p)
    db.commit()
    db.refresh(p)
    return p


def test_create_proposal_returns_draft(client):
    resp = client.post(
        "/api/proposals",
        json={
            "client_name": "Jane Doe",
            "client_email": "jane@example.com",
            "project_address": "2 Oak Ave",
            "site_walk_notes": "Backyard paver patio.",
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] == "DRAFT"
    assert data["client_name"] == "Jane Doe"


def test_create_proposal_validates_email(client):
    resp = client.post(
        "/api/proposals",
        json={
            "client_name": "Jane",
            "client_email": "not-an-email",
            "project_address": "x",
            "site_walk_notes": "y",
        },
    )
    assert resp.status_code == 422


def test_list_proposals_ordered_newest_first(client):
    client.post("/api/proposals", json={
        "client_name": "A", "client_email": "a@e.com",
        "project_address": "x", "site_walk_notes": "p1",
    })
    client.post("/api/proposals", json={
        "client_name": "B", "client_email": "b@e.com",
        "project_address": "y", "site_walk_notes": "p2",
    })
    resp = client.get("/api/proposals")
    names = [p["client_name"] for p in resp.json()]
    assert names == ["B", "A"]


def test_cannot_generate_from_needs_review(client, db_session):
    p = _draft_proposal(
        db_session, status=ProposalStatus.NEEDS_REVIEW
    )
    resp = client.post(f"/api/proposals/{p.id}/generate")
    assert resp.status_code == 409


def test_cannot_approve_unless_needs_review(client, db_session):
    p = _draft_proposal(db_session)
    resp = client.post(f"/api/proposals/{p.id}/approve")
    assert resp.status_code == 409
    # Status unchanged.
    db_session.refresh(p)
    assert p.status == ProposalStatus.DRAFT


def test_cannot_send_unless_approved(client, db_session):
    for status in (
        ProposalStatus.DRAFT,
        ProposalStatus.GENERATING,
        ProposalStatus.NEEDS_REVIEW,
        ProposalStatus.FAILED,
    ):
        p = _draft_proposal(db_session, status=status)
        resp = client.post(f"/api/proposals/{p.id}/send")
        assert resp.status_code == 409, status


def test_approve_from_needs_review_sets_timestamp(client, db_session):
    p = _draft_proposal(db_session, status=ProposalStatus.NEEDS_REVIEW)
    resp = client.post(f"/api/proposals/{p.id}/approve")
    assert resp.status_code == 200
    db_session.refresh(p)
    assert p.status == ProposalStatus.APPROVED
    assert p.approved_at is not None


def test_send_fails_when_resend_not_configured(client, db_session):
    p = _draft_proposal(
        db_session,
        status=ProposalStatus.APPROVED,
        approved_at=datetime.now(timezone.utc),
        estimated_total=1000,
    )
    # Simulate the "missing Resend config" error path.
    import app.services.notification_service as ns
    original_send = ns.settings.resend_api_key
    # Also ensure from_email is not None so the test isolates the API key check.
    original_from = ns.settings.from_email
    ns.settings.from_email = "Greenscape Pro <test@example.com>"
    ns.settings.resend_api_key = None
    try:
        resp = client.post(f"/api/proposals/{p.id}/send")
    finally:
        ns.settings.resend_api_key = original_send
        ns.settings.from_email = original_from
    assert resp.status_code == 502
    db_session.refresh(p)
    # NOT marked SENT; preserved as APPROVED for retry.
    assert p.status == ProposalStatus.APPROVED
    assert p.sent_at is None


def test_send_fails_when_from_email_missing(client, db_session):
    p = _draft_proposal(
        db_session,
        status=ProposalStatus.APPROVED,
        approved_at=datetime.now(timezone.utc),
        estimated_total=1000,
    )
    import app.services.notification_service as ns
    original_key = ns.settings.resend_api_key
    original_from = ns.settings.from_email
    ns.settings.resend_api_key = "re_test"
    ns.settings.from_email = None
    try:
        resp = client.post(f"/api/proposals/{p.id}/send")
    finally:
        ns.settings.resend_api_key = original_key
        ns.settings.from_email = original_from
    assert resp.status_code == 502
    db_session.refresh(p)
    assert p.status == ProposalStatus.APPROVED
    assert p.sent_at is None


def test_send_success_sets_sent_and_timestamp(client, db_session, monkeypatch):
    p = _draft_proposal(
        db_session,
        status=ProposalStatus.APPROVED,
        approved_at=datetime.now(timezone.utc),
        estimated_total=25000,
        client_email="fawadqureshi136@gmail.com",
    )
    import app.services.notification_service as ns
    original_key = ns.settings.resend_api_key
    original_from = ns.settings.from_email
    ns.settings.resend_api_key = "re_test"
    ns.settings.from_email = "Greenscape Pro <test@example.com>"
    try:
        # Mock the actual Resend API call so no real email is sent in tests.
        monkeypatch.setattr(
            "resend.Emails.send", lambda params: {"id": "mock-email-id"}
        )
        resp = client.post(f"/api/proposals/{p.id}/send")
    finally:
        ns.settings.resend_api_key = original_key
        ns.settings.from_email = original_from
    assert resp.status_code == 200
    db_session.refresh(p)
    assert p.status == ProposalStatus.SENT
    assert p.sent_at is not None


def test_generate_workflow_succeeds_and_sets_needs_review(seeded_client, seeded_db, monkeypatch):
    p = _draft_proposal(seeded_db)

    scope = ScopeExtraction(
        project_summary="Test patio project.",
        scope_items=[],
        assumptions=["Assumption"],
        clarifying_questions=["Question"],
        risk_flags=["Risk"],
    )
    monkeypatch.setattr(ai_service, "extract_scope", lambda notes, catalog: scope)
    monkeypatch.setattr(
        ai_service,
        "generate_proposal_draft",
        lambda **kw: "# Draft Proposal\n\nOverview.",
    )

    resp = seeded_client.post(f"/api/proposals/{p.id}/generate")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "NEEDS_REVIEW"
    assert data["project_summary"] == "Test patio project."
    assert data["generated_proposal"] == "# Draft Proposal\n\nOverview."
    assert data["estimated_total"] is not None


def test_generate_failure_marks_failed(seeded_client, seeded_db, monkeypatch):
    p = _draft_proposal(seeded_db)

    def boom(notes, catalog):
        raise ValueError("bad extraction")

    monkeypatch.setattr(ai_service, "extract_scope", boom)

    resp = seeded_client.post(f"/api/proposals/{p.id}/generate")
    assert resp.status_code == 500
    seeded_db.refresh(p)
    assert p.status == ProposalStatus.FAILED
    # Error response must NOT leak internal details / stack traces.
    body = resp.json()
    assert "traceback" not in str(body).lower()
    assert "groq_api_key" not in str(body).lower()
