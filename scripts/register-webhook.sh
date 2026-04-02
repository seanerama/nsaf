#!/bin/bash
# Register Webex webhook for NSAF bot
set -euo pipefail

# Source .env
NSAF_DIR="${NSAF_DIR:-/opt/nsaf}"
if [ -f "$NSAF_DIR/.env" ]; then
    set -a
    source "$NSAF_DIR/.env"
    set +a
fi

FLASK_HOST="${NSAF_FLASK_HOST:-localhost}"
FLASK_PORT="${NSAF_FLASK_PORT:-5000}"
TARGET_URL="http://${FLASK_HOST}:${FLASK_PORT}/webex/webhook"

if [ -z "${WEBEX_BOT_TOKEN:-}" ]; then
    echo "Error: WEBEX_BOT_TOKEN not set"
    exit 1
fi

echo "Registering Webex webhook..."
echo "Target URL: $TARGET_URL"

# Check for existing webhook
EXISTING=$(curl -s -H "Authorization: Bearer $WEBEX_BOT_TOKEN" \
    "https://webexapis.com/v1/webhooks" | python3 -c "
import sys, json
data = json.load(sys.stdin)
for item in data.get('items', []):
    if 'nsaf' in item.get('name', '').lower():
        print(item['id'])
        break
" 2>/dev/null || true)

if [ -n "$EXISTING" ]; then
    echo "Updating existing webhook: $EXISTING"
    curl -s -X PUT "https://webexapis.com/v1/webhooks/$EXISTING" \
        -H "Authorization: Bearer $WEBEX_BOT_TOKEN" \
        -H "Content-Type: application/json" \
        -d "{
            \"name\": \"NSAF Bot\",
            \"targetUrl\": \"$TARGET_URL\",
            \"secret\": \"${WEBEX_WEBHOOK_SECRET:-}\"
        }" | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'  ✓ Updated: {d.get(\"id\", \"unknown\")}')"
else
    echo "Creating new webhook..."
    curl -s -X POST "https://webexapis.com/v1/webhooks" \
        -H "Authorization: Bearer $WEBEX_BOT_TOKEN" \
        -H "Content-Type: application/json" \
        -d "{
            \"name\": \"NSAF Bot\",
            \"targetUrl\": \"$TARGET_URL\",
            \"resource\": \"messages\",
            \"event\": \"created\",
            \"secret\": \"${WEBEX_WEBHOOK_SECRET:-}\"
        }" | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'  ✓ Created: {d.get(\"id\", \"unknown\")}')"
fi
