"""Outbound Webex notification helpers for Flask-initiated messages."""

import logging
import os

import requests

log = logging.getLogger(__name__)


def _send_webex_message(text):
    """Send a message to the NSAF owner via Webex."""
    token = os.environ.get("WEBEX_BOT_TOKEN")
    person_id = os.environ.get("WEBEX_OWNER_PERSON_ID")

    if not token or not person_id:
        log.error("Missing WEBEX_BOT_TOKEN or WEBEX_OWNER_PERSON_ID")
        return False

    try:
        response = requests.post(
            "https://webexapis.com/v1/messages",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            json={
                "toPersonId": person_id,
                "markdown": text,
            },
            timeout=10,
        )
        response.raise_for_status()
        return True
    except Exception as e:
        log.error(f"Failed to send Webex message: {e}")
        return False


def notify_stall(project):
    """Send stall alert for a project."""
    text = (
        f"**⚠️ Build Stalled: `{project['slug']}`**\n\n"
        f"Phase: {project.get('sdd_phase', 'unknown')}\n"
        f"Stuck at: {project.get('sdd_active_role', 'unknown')}\n\n"
        f"Commands:\n"
        f"- `restart {project['slug']}` — re-queue the project\n"
        f"- `skip {project['slug']}` — scrap it"
    )
    return _send_webex_message(text)


def notify_completion(project):
    """Send completion notification for a project."""
    url = project.get("deployed_url", "unknown")
    text = (
        f"**✅ Build Complete: `{project['slug']}`**\n\n"
        f"Local URL: {url}\n\n"
        f"Commands:\n"
        f"- `promote {project['slug']}` — deploy to Render\n"
        f"- `skip {project['slug']}` — scrap it\n\n"
        f"Review: /review/{project['slug']}"
    )
    return _send_webex_message(text)


def notify_promotion(project):
    """Send promotion success notification."""
    render_url = project.get("render_url", "pending")
    text = (
        f"**🚀 Deployed to Render: `{project['slug']}`**\n\n"
        f"Render URL: {render_url}"
    )
    return _send_webex_message(text)
