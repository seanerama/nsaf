#!/bin/bash
# NSAF Setup Script — Idempotent first-time setup for Ubuntu server
set -euo pipefail

NSAF_DIR="${NSAF_DIR:-/opt/nsaf}"

echo "=== NSAF Setup ==="
echo "Install directory: $NSAF_DIR"

# Check prerequisites
echo ""
echo "--- Checking prerequisites ---"

check_cmd() {
    if command -v "$1" &>/dev/null; then
        echo "  ✓ $1 found"
    else
        echo "  ✗ $1 NOT found — please install it"
        return 1
    fi
}

check_cmd node
check_cmd python3
check_cmd git
check_cmd psql
check_cmd claude || echo "  ⚠ Claude Code CLI not found — install and authenticate before running builds"

# Check .env
echo ""
echo "--- Checking configuration ---"
if [ ! -f "$NSAF_DIR/.env" ]; then
    echo "  ✗ .env not found — copying from .env.example"
    cp "$NSAF_DIR/.env.example" "$NSAF_DIR/.env"
    echo "  → Please edit $NSAF_DIR/.env and fill in all required values"
    echo "  → Then re-run this script"
    exit 1
else
    echo "  ✓ .env exists"
fi

# Source .env for config values
set -a
source "$NSAF_DIR/.env"
set +a

# Create Python venv
echo ""
echo "--- Setting up Python virtual environment ---"
if [ ! -d "$NSAF_DIR/venv" ]; then
    python3 -m venv "$NSAF_DIR/venv"
    echo "  ✓ Created venv"
else
    echo "  ✓ venv already exists"
fi

# Install Python dependencies
echo "  Installing Python packages..."
"$NSAF_DIR/venv/bin/pip" install -q -r "$NSAF_DIR/flask-app/requirements.txt"
"$NSAF_DIR/venv/bin/pip" install -q -r "$NSAF_DIR/idea-generator/requirements.txt"
echo "  ✓ Python packages installed"

# Install Node.js dependencies
echo ""
echo "--- Installing Node.js dependencies ---"
cd "$NSAF_DIR/orchestrator" && npm install --production
echo "  ✓ Node packages installed"

# Initialize SQLite database
echo ""
echo "--- Initializing database ---"
cd "$NSAF_DIR"
node orchestrator/src/index.js --init-db
echo "  ✓ SQLite database initialized"

# Create projects directory
PROJECTS_DIR="${NSAF_PROJECTS_DIR:-$NSAF_DIR/projects}"
echo ""
echo "--- Creating projects directory ---"
mkdir -p "$PROJECTS_DIR"
echo "  ✓ $PROJECTS_DIR"

# Install systemd services
echo ""
echo "--- Installing systemd services ---"
CURRENT_USER=$(whoami)
sed "s|NSAF_USER|$CURRENT_USER|g; s|NSAF_DIR|$NSAF_DIR|g" \
    "$NSAF_DIR/systemd/nsaf-orchestrator.service" | sudo tee /etc/systemd/system/nsaf-orchestrator.service > /dev/null
sed "s|NSAF_USER|$CURRENT_USER|g; s|NSAF_DIR|$NSAF_DIR|g" \
    "$NSAF_DIR/systemd/nsaf-flask.service" | sudo tee /etc/systemd/system/nsaf-flask.service > /dev/null
sudo systemctl daemon-reload
sudo systemctl enable nsaf-orchestrator nsaf-flask
echo "  ✓ Services installed and enabled (user: $CURRENT_USER, dir: $NSAF_DIR)"

# Set up cron
echo ""
echo "--- Setting up cron job ---"
CRON_CMD="0 7 * * * cd $NSAF_DIR && $NSAF_DIR/venv/bin/python idea-generator/generate.py >> /var/log/nsaf-ideas.log 2>&1"
if crontab -l 2>/dev/null | grep -q "nsaf"; then
    echo "  ✓ Cron job already exists"
else
    (crontab -l 2>/dev/null || true; echo "$CRON_CMD") | crontab -
    echo "  ✓ Cron job added (runs daily at 7:00 AM)"
fi

# Register Webex webhook
echo ""
echo "--- Webex webhook ---"
if [ -n "${WEBEX_BOT_TOKEN:-}" ] && [ -n "${NSAF_FLASK_HOST:-}" ]; then
    bash "$NSAF_DIR/scripts/register-webhook.sh" || echo "  ⚠ Webhook registration failed — run manually later"
else
    echo "  ⚠ Skipping webhook registration — set WEBEX_BOT_TOKEN and NSAF_FLASK_HOST first"
fi

echo ""
echo "=== Setup Complete ==="
echo ""
echo "Next steps:"
echo "  1. Edit $NSAF_DIR/.env if you haven't already"
echo "  2. Start services: sudo systemctl start nsaf-orchestrator nsaf-flask"
echo "  3. Check status: sudo systemctl status nsaf-orchestrator nsaf-flask"
echo "  4. Test idea generation: cd $NSAF_DIR && venv/bin/python idea-generator/generate.py --dry-run"
echo "  5. View logs: journalctl -u nsaf-orchestrator -f"
