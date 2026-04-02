#!/usr/bin/env python3
"""NSAF Flask App — Idea selection, QA review, and Webex bot."""

import logging
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv

load_dotenv()

from flask import Flask

from shared.db import get_db

log = logging.getLogger("nsaf.flask")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")

app = Flask(__name__)


def init_app():
    """Initialize database connection and register routes."""
    get_db()

    from routes.select import select_bp
    from routes.review import review_bp
    from routes.webex import webex_bp

    app.register_blueprint(select_bp)
    app.register_blueprint(review_bp)
    app.register_blueprint(webex_bp)


def setup_ngrok_and_webhook(port):
    """Start ngrok tunnel and register Webex webhook."""
    ngrok_token = os.environ.get("NGROK_AUTHTOKEN")
    webex_token = os.environ.get("WEBEX_BOT_TOKEN")

    if not ngrok_token:
        log.warning("NGROK_AUTHTOKEN not set — skipping ngrok/webhook setup")
        return None

    if not webex_token:
        log.warning("WEBEX_BOT_TOKEN not set — skipping webhook registration")
        return None

    try:
        from pyngrok import conf, ngrok

        if ngrok_token:
            conf.get_default().auth_token = ngrok_token

        tunnel = ngrok.connect(port, "http")
        public_url = tunnel.public_url
        if public_url.startswith("http://"):
            public_url = public_url.replace("http://", "https://", 1)

        log.info(f"ngrok tunnel: {public_url}")

        # Register webhook using webexteamssdk
        from webexteamssdk import WebexTeamsAPI

        api = WebexTeamsAPI(access_token=webex_token)

        # Clean up old webhooks
        for wh in api.webhooks.list():
            api.webhooks.delete(wh.id)
            log.info(f"Deleted old webhook: {wh.name}")

        # Register new webhook
        webhook_url = f"{public_url}/webex/webhook"
        api.webhooks.create(
            name="NSAF Bot",
            targetUrl=webhook_url,
            resource="messages",
            event="created",
        )
        log.info(f"Webhook registered: {webhook_url}")

        return public_url

    except Exception as e:
        log.error(f"ngrok/webhook setup failed: {e}")
        return None


init_app()


@app.after_request
def set_security_headers(response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response


@app.errorhandler(404)
def not_found(e):
    return {"error": "Not found"}, 404


@app.errorhandler(500)
def server_error(e):
    return {"error": "Internal server error"}, 500


if __name__ == "__main__":
    host = os.environ.get("NSAF_FLASK_HOST", "0.0.0.0")
    port = int(os.environ.get("NSAF_FLASK_PORT", "5000"))
    debug = os.environ.get("FLASK_DEBUG", "false").lower() == "true"

    # Setup ngrok tunnel and Webex webhook before starting Flask
    setup_ngrok_and_webhook(port)

    app.run(host=host, port=port, debug=debug)
