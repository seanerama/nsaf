"""Webex webhook route."""

import hashlib
import hmac
import logging
import os

import requests
from flask import Blueprint, request, jsonify

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from bot.commands import handle_command

log = logging.getLogger(__name__)

webex_bp = Blueprint("webex", __name__)


def _verify_signature(body, signature):
    """Verify Webex webhook signature. Rejects if secret is not configured."""
    secret = os.environ.get("WEBEX_WEBHOOK_SECRET")
    if not secret:
        log.warning("WEBEX_WEBHOOK_SECRET not configured — rejecting request")
        return False
    expected = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


def _is_owner(person_id):
    """Check if the message is from the configured owner. Rejects if not configured."""
    owner_id = os.environ.get("WEBEX_OWNER_PERSON_ID")
    if not owner_id:
        log.warning("WEBEX_OWNER_PERSON_ID not configured — rejecting request")
        return False
    return person_id == owner_id


def _get_message_text(message_id):
    """Fetch the full message text from Webex API."""
    token = os.environ.get("WEBEX_BOT_TOKEN", "")
    try:
        resp = requests.get(
            f"https://webexapis.com/v1/messages/{message_id}",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json().get("text", "").strip()
    except Exception as e:
        log.error(f"Failed to fetch message: {e}")
        return None


def _reply(person_id, text):
    """Send a reply via Webex."""
    token = os.environ.get("WEBEX_BOT_TOKEN", "")
    try:
        requests.post(
            "https://webexapis.com/v1/messages",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            json={"toPersonId": person_id, "markdown": text},
            timeout=10,
        )
    except Exception as e:
        log.error(f"Failed to send reply: {e}")


@webex_bp.route("/webex/webhook", methods=["POST"])
def webhook():
    """Handle incoming Webex webhook."""
    # Verify signature
    signature = request.headers.get("X-Spark-Signature", "")
    if not _verify_signature(request.data, signature):
        return jsonify({"error": "Invalid signature"}), 403

    data = request.json or {}
    resource = data.get("resource")
    event = data.get("event")

    if resource != "messages" or event != "created":
        return jsonify({"status": "ignored"}), 200

    message_data = data.get("data", {})
    person_id = message_data.get("personId", "")
    message_id = message_data.get("id", "")

    # Check owner restriction
    if not _is_owner(person_id):
        log.warning(f"Unauthorized command attempt from {person_id}")
        return jsonify({"error": "Unauthorized"}), 403

    # Fetch message text
    text = _get_message_text(message_id)
    if not text:
        return jsonify({"error": "Could not fetch message"}), 500

    # Handle command
    response = handle_command(text)
    _reply(person_id, response)

    return jsonify({"status": "ok"}), 200
