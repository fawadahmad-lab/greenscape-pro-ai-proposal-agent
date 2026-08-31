"""External proposal delivery service (Resend email).

Resend is used as the external email integration for this assessment. The
application sends an approved proposal to the client's email after human
approval. All email-sending logic stays isolated in this service; FastAPI
route handlers never call the Resend SDK directly.
"""

import html
import logging
from decimal import Decimal

import resend

from app.core.config import get_settings
from app.models.proposal import Proposal

logger = logging.getLogger(__name__)

settings = get_settings()


class NotificationError(Exception):
    """Raised when the proposal email cannot be delivered."""

    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


def _fmt_money(value: Decimal | float | None) -> str:
    if value is None:
        return "—"
    return f"${float(value):,.2f}"


def _tbd_or_money(value: Decimal | float | None) -> str:
    """Render a monetary value as TBD when unknown, else a formatted amount."""
    if value is None:
        return "TBD"
    return f"${float(value):,.2f}"


def _tbd_or_num(value) -> str:
    """Render a numeric value as TBD when unknown, else the plain number. Never
    prints a literal 'None'."""
    if value is None:
        return "TBD"
    return str(value)


_SERVICE_STATES = {
    "Arizona": "AZ",
    "AZ": "AZ",
    "Phoenix": "Phoenix",
    "Scottsdale": "Phoenix",
    "Tempe": "Phoenix",
    "Mesa": "Phoenix",
    "Chandler": "Phoenix",
    "Gilbert": "Phoenix",
    "Peoria": "Phoenix",
    "Surprise": "Phoenix",
    "Avondale": "Phoenix",
}


def _is_in_service_area(address: str | None) -> bool:
    """Return True if the address looks like it is within the Phoenix metro area."""
    if not address:
        return True
    lowered = address.lower()
    return any(anchor.lower() in lowered for anchor in _SERVICE_STATES)


def _escape(value: str | None) -> str:
    return html.escape(value or "")


_PLACEHOLDER_PATTERNS = [
    r"\[Your Company Name\]",
    r"\[Your Name\]",
    r"\[Contact Information\]",
    r"\[Your Location\]",
    r"\[(?:Your|Company|Client)[^\]]*\]",
]


def _scrub_placeholders(text: str | None) -> str:
    """Remove leftover placeholder brackets (e.g. [Your Company Name]) so they
    never reach the client. Unknown fields are omitted rather than shown."""
    import re

    cleaned = (text or "")
    for pattern in _PLACEHOLDER_PATTERNS:
        cleaned = re.sub(pattern, "", cleaned)
    # Collapse any leftover empty brackets and blank lines.
    cleaned = re.sub(r"\[\s*\]", "", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    cleaned = re.sub(r"[ \t]{2,}", " ", cleaned)
    return cleaned.strip()


def _phrase(items: list[str] | None) -> str:
    if not items:
        return "<p><em>None noted.</em></p>"
    return "<ul>" + "".join(f"<li>{_escape(i)}</li>" for i in items) + "</ul>"


def _build_html(proposal: Proposal) -> str:
    """Build a concise, email-safe proposal email from structured data only.

    The full detailed Markdown proposal is NOT included here; it is rendered
    only in the web application's Proposal Detail page. This email is a clean,
    semantically structured HTML summary with inline styles for compatibility
    across major email clients.
    """
    summary = _escape(proposal.project_summary) or "Your project is outlined below."

    # --- Scope of Work table ------------------------------------------------
    priced = proposal.pricing_json or []
    if priced:
        rows = "".join(
            "<tr>"
            f"<td>{_escape(str(item.get('requested_work', '')))}</td>"
            f"<td>{_escape(str(item.get('catalog_item_name', '')))}</td>"
            f"<td>{_escape(_tbd_or_num(item.get('quantity')))}</td>"
            f"<td>{_escape(str(item.get('unit', '')))}</td>"
            f"<td>{_tbd_or_money(_as_money(item.get('unit_price')))}</td>"
            f"<td>{_tbd_or_money(_as_money(item.get('line_total')))}</td>"
            "</tr>"
            for item in priced
        )
        scope_html = (
            "<table border='0' cellpadding='8' cellspacing='0' "
            "style='width:100%;border-collapse:collapse;border:1px solid #ddd'>"
            "<thead><tr style='background:#f0f2f5'>"
            "<th style='text-align:left'>Requested Work</th>"
            "<th style='text-align:left'>Item</th>"
            "<th style='text-align:left'>Qty</th>"
            "<th style='text-align:left'>Unit</th>"
            "<th style='text-align:left'>Unit Price</th>"
            "<th style='text-align:left'>Line Total</th>"
            "</tr></thead>"
            f"<tbody>{rows}</tbody></table>"
        )
        tbd_items = [
            str(item.get("requested_work", ""))
            for item in priced
            if _as_money(item.get("line_total")) is None
        ]
    else:
        scope_html = "<p><em>Scope details will be confirmed in the final proposal.</em></p>"
        tbd_items = []

    # --- Items Pending Pricing (distinct section) ---------------------------
    if tbd_items:
        pending_html = (
            "<ul>"
            + "".join(f"<li>{_escape(i)}</li>" for i in tbd_items)
            + "</ul>"
        )
    else:
        pending_html = ""

    # --- Estimated Investment — Priced Items --------------------------------
    if proposal.estimated_total is not None:
        investment_html = (
            "<p style='font-size:1.25rem;font-weight:bold'>"
            f"{_fmt_money(proposal.estimated_total)}</p>"
            "<p style='color:#6b7280;font-size:0.85rem'>Additional TBD items are "
            "not included in this total and will be priced after quantities are "
            "confirmed.</p>"
        )
    else:
        investment_html = (
            "<p style='color:#6b7280'>Pricing pending final quantities; an "
            "estimate will be provided once items are confirmed.</p>"
        )

    # --- Geographic assumption: flag out-of-area, never alter the address ----
    additional_assumptions = []
    if not _is_in_service_area(proposal.project_address):
        additional_assumptions.append(
            "The project address appears to be outside Greenscape Pro's "
            "Phoenix, Arizona service area. Service availability, travel, and "
            "permitting should be confirmed before proceeding."
        )

    assumptions = list(proposal.assumptions_json or []) + additional_assumptions
    assumptions_html = (_phrase(assumptions) if assumptions else "")

    questions = (
        _phrase(proposal.clarifying_questions_json)
        if proposal.clarifying_questions_json
        else ""
    )

    return f"""
<div style="font-family:Arial,Helvetica,sans-serif;color:#1f2937;max-width:640px;margin:0 auto">
  <h2 style="color:#1b6b4e">Greenscape Pro</h2>
  <p>Hello {_escape(proposal.client_name)},</p>
  <p>Thank you for the opportunity to design your outdoor space. We are pleased to
     share the following proposal for your project at
     <strong>{_escape(proposal.project_address)}</strong>.</p>

  <h3 style="color:#1b6b4e">Project Summary</h3>
  <p>{summary}</p>

  <h3 style="color:#1b6b4e">Scope of Work</h3>
  {scope_html}

  {("<h3 style='color:#1b6b4e'>Items Pending Pricing</h3>\n  " + pending_html) if pending_html else ""}

  <h3 style="color:#1b6b4e">Estimated Investment — Priced Items</h3>
  {investment_html}

  {("<h3 style='color:#1b6b4e'>Assumptions / Items Requiring Confirmation</h3>\n  " + assumptions_html) if assumptions_html else ""}

  {("<h3 style='color:#1b6b4e'>Clarifying Questions</h3>\n  " + questions) if questions else ""}

  <h3 style="color:#1b6b4e">Next Steps</h3>
  <p>Review the summary above and let us know any questions or adjustments. Once
     we confirm the details, we will schedule a start date for the project.</p>

  <p style="color:#6b7280;font-size:0.85rem">This is a draft estimate pending your
     review and is not a binding quote.</p>

  <p>We look forward to bringing your vision to life.</p>
  <p>
    <strong>Greenscape Pro</strong><br/>
    Premium Residential Landscape &amp; Hardscape Design-Build<br/>
    Phoenix, Arizona
  </p>
</div>
"""


def _as_money(value) -> Decimal | float | None:
    try:
        if value is None:
            return None
        return Decimal(str(value))
    except (TypeError, ValueError):
        return None


def send_proposal_email(proposal: Proposal) -> None:
    """Send an approved proposal to the client's email via Resend.

    Raises:
        NotificationError: if the email cannot be sent (config, invalid
            recipient, Resend error, or network error).
    """
    if not settings.resend_api_key:
        raise NotificationError(
            "RESEND_API_KEY is not configured. The proposal was not sent. "
            "Configure the key and retry sending."
        )
    if not settings.from_email:
        raise NotificationError(
            "FROM_EMAIL is not configured. The proposal was not sent. "
            "Configure the sender and retry sending."
        )

    recipient = (proposal.client_email or "").strip()
    if not recipient or "@" not in recipient:
        raise NotificationError(
            "The client does not have a valid email address. The proposal was not "
            "sent. Update the client email and retry."
        )

    subject = "Your Greenscape Pro Project Proposal"
    html_body = _build_html(proposal)

    try:
        resend.api_key = settings.resend_api_key
        response = resend.Emails.send(
            {
                "from": settings.from_email,
                "to": [recipient],
                "subject": subject,
                "html": html_body,
            }
        )
    except Exception as exc:
        # Log a sanitized message server-side; never log the API key or headers.
        logger.error(
            "Resend email send failed for proposal id=%s: %s",
            proposal.id,
            type(exc).__name__,
        )
        raise NotificationError(
            "The proposal email could not be sent due to an external service "
            "error. The proposal was not marked as SENT. Please retry."
        ) from exc

    logger.info("Proposal email sent to %s for proposal id=%s", recipient, proposal.id)
    return response
