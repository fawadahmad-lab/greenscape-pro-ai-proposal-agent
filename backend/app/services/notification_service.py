"""External notification service (Slack incoming webhook)."""

import logging
from datetime import datetime, timezone

import httpx

from app.core.config import get_settings
from app.models.proposal import Proposal

logger = logging.getLogger(__name__)

settings = get_settings()


class NotificationError(Exception):
    """Raised when an external notification cannot be delivered."""


def send_slack_notification(proposal: Proposal) -> None:
    """Post a concise approval/sent notification to the Slack webhook.

    Raises:
        NotificationError: if no webhook is configured or the request fails.
    """
    if not settings.slack_webhook_url:
        raise NotificationError(
            "SLACK_WEBHOOK_URL is not configured. The proposal was not marked as "
            "SENT. Configure the webhook and retry sending."
        )

    timestamp = datetime.now(timezone.utc).isoformat()
    payload = {
        "text": (
            "Greenscape Pro Proposal Approved\n"
            f"Client: {proposal.client_name}\n"
            f"Proposal ID: {proposal.id}\n"
            f"Estimated Total: ${proposal.estimated_total or 0:,.2f}\n"
            f"Status: Sent\n"
            f"Timestamp: {timestamp}"
        )
    }

    try:
        response = httpx.post(
            settings.slack_webhook_url,
            json=payload,
            timeout=10.0,
        )
    except httpx.HTTPError as exc:
        logger.error("Slack webhook HTTP error: %s", exc)
        raise NotificationError(
            "Slack notification failed due to a network error. "
            "The proposal was not marked as SENT. Please retry."
        ) from exc

    if response.status_code != 200:
        logger.error(
            "Slack webhook returned HTTP %s: %s", response.status_code, response.text
        )
        raise NotificationError(
            f"Slack notification failed (HTTP {response.status_code}). "
            "The proposal was not marked as SENT. Please retry."
        )

    logger.info("Slack notification sent for proposal id=%s", proposal.id)
