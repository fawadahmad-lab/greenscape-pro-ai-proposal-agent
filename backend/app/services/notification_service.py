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


def _escape(value: str | None) -> str:
    return html.escape(value or "")


def _phrase(items: list[str] | None) -> str:
    if not items:
        return "<p><em>None noted.</em></p>"
    return "<ul>" + "".join(f"<li>{_escape(i)}</li>" for i in items) + "</ul>"


def _build_html(proposal: Proposal) -> str:
    """Build a professional proposal email body. No internal details leaked."""
    summary = _escape(proposal.project_summary) or "Your project is outlined below."
    estimated_total = _fmt_money(proposal.estimated_total)

    # Scope of work table based on the deterministic pricing breakdown.
    priced = proposal.pricing_json or []
    if priced:
        rows = "".join(
            "<tr>"
            f"<td>{_escape(str(item.get('requested_work', '')))}</td>"
            f"<td>{_escape(str(item.get('catalog_item_name', '')))}</td>"
            f"<td>{_escape(str(item.get('quantity', 'TBD')))}</td>"
            f"<td>{_escape(str(item.get('unit', '')))}</td>"
            f"<td>{_fmt_money(_as_money(item.get('unit_price')))}</td>"
            f"<td>{_fmt_money(_as_money(item.get('line_total')))}</td>"
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
    else:
        scope_html = "<p><em>Scope details will be confirmed in the final proposal.</em></p>"

    questions = (
        _phrase(proposal.clarifying_questions_json)
        if proposal.clarifying_questions_json
        else "<p><em>None pending.</em></p>"
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

  <h3 style="color:#1b6b4e">Estimated Investment</h3>
  <p style="font-size:1.25rem;font-weight:bold">{estimated_total}</p>

  <h3 style="color:#1b6b4e">Assumptions / Items Requiring Confirmation</h3>
  {_phrase(proposal.assumptions_json)}

  <h3 style="color:#1b6b4e">Clarifying Questions</h3>
  {questions}

  <h3 style="color:#1b6b4e">Proposal Details</h3>
  <div style="white-space:pre-wrap;background:#fafbfc;border:1px solid #e5e7eb;padding:16px;border-radius:8px">
    {_escape(proposal.generated_proposal)}
  </div>

  <h3 style="color:#1b6b4e">Next Steps</h3>
  <p>Review the summary above and let us know any questions or adjustments. Once
     we confirm the details, we will schedule a start date. This is a draft
     estimate pending your review and is not a binding quote.</p>

  <p>We look forward to bringing your vision to life.</p>
  <p>
    <strong>Greenscape Pro</strong><br/>
    Premium Residential Landscape &amp; Hardscape<br/>
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
