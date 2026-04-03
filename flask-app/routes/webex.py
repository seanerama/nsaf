"""Webex webhook route."""

import logging
import os

from flask import Blueprint, request, jsonify

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from bot.commands import handle_command

log = logging.getLogger(__name__)

webex_bp = Blueprint("webex", __name__)

_api = None


def _get_api():
    """Lazy-init WebexTeamsAPI."""
    global _api
    if _api is None:
        from webexteamssdk import WebexTeamsAPI
        _api = WebexTeamsAPI(access_token=os.environ.get("WEBEX_BOT_TOKEN", ""))
    return _api


def _is_owner(person_id):
    """Check if the message is from the configured owner."""
    owner_id = os.environ.get("WEBEX_OWNER_PERSON_ID")
    if not owner_id:
        log.warning("WEBEX_OWNER_PERSON_ID not configured — rejecting request")
        return False
    return person_id == owner_id


@webex_bp.route("/webex/webhook", methods=["POST"])
def webhook():
    """Handle incoming Webex webhook."""
    data = request.json or {}
    resource = data.get("resource")
    event = data.get("event")

    if resource != "messages" or event != "created":
        return jsonify({"status": "ignored"}), 200

    message_data = data.get("data", {})
    person_id = message_data.get("personId", "")
    message_id = message_data.get("id", "")

    # Ignore messages from the bot itself
    api = _get_api()
    try:
        bot_info = api.people.me()
        if person_id == bot_info.id:
            return jsonify({"status": "ignored"}), 200
    except Exception:
        pass

    # Check owner restriction
    if not _is_owner(person_id):
        log.warning(f"Unauthorized command attempt from {person_id}")
        return jsonify({"status": "unauthorized"}), 200

    # Fetch full message text
    try:
        message = api.messages.get(message_id)
        text = message.text.strip() if message.text else ""
    except Exception as e:
        log.error(f"Failed to fetch message: {e}")
        return jsonify({"error": "Could not fetch message"}), 200

    if not text:
        return jsonify({"status": "empty"}), 200

    # Handle command — returns string or dict with {text, files}
    response = handle_command(text)

    # Reply
    try:
        room_id = message_data.get("roomId", "")
        kwargs = {"roomId": room_id} if room_id else {"toPersonId": person_id}

        if isinstance(response, dict):
            kwargs["markdown"] = response.get("text", "")
            if response.get("files"):
                kwargs["files"] = response["files"]
        else:
            kwargs["markdown"] = response

        api.messages.create(**kwargs)
    except Exception as e:
        log.error(f"Failed to send reply: {e}")

    return jsonify({"status": "ok"}), 200
