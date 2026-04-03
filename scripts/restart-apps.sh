#!/bin/bash
# Restart any deployed apps that aren't running.
# Also detect completed builds stuck in "building" status.
# Run via cron every 2 minutes.
set -euo pipefail

NSAF_DIR="${NSAF_DIR:-$(cd "$(dirname "$0")/.." && pwd)}"
cd "$NSAF_DIR"

DB="${NSAF_DB_PATH:-$NSAF_DIR/nsaf.db}"

# --- Phase 1: Fix builds stuck in "building" that actually completed ---
sqlite3 "$DB" "SELECT slug, port_start, project_dir FROM projects WHERE status = 'building';" | while IFS='|' read -r slug port dir; do
  [ -z "$slug" ] && continue
  state="$dir/sdd-output/STATE.md"
  [ -f "$state" ] || continue

  # Check if deployer role is done
  if grep -q "\[x\] Project Deployer" "$state" 2>/dev/null || grep -q '"Project Deployer"' "$state" 2>/dev/null; then
    # Check no claude process is running for this project
    if ! pgrep -f "claude.*$dir" > /dev/null 2>&1; then
      echo "$(date -Iseconds) Fixing stuck build: $slug (completed but still marked building)"
      sqlite3 "$DB" "UPDATE projects SET status = 'deployed-local', sdd_phase = 'complete', sdd_progress = 100, deployed_url = 'http://localhost:${port}', completed_at = datetime('now') WHERE slug = '$slug';"
    fi
  fi
done

sqlite3 "$DB" "SELECT slug, port_start FROM projects WHERE status = 'deployed-local' AND port_start IS NOT NULL ORDER BY port_start;" | while IFS='|' read -r slug port; do
  # Check if port is listening
  if ss -tlnp 2>/dev/null | grep -q ":${port} "; then
    continue
  fi

  dir="$NSAF_DIR/projects/$slug"
  [ -d "$dir" ] || continue

  echo "$(date -Iseconds) Restarting $slug on port $port"

  be_port=$((port + 1))

  # Find and start backend
  for be_dir in "$dir/server" "$dir/backend"; do
    if [ -f "$be_dir/index.js" ]; then
      cd "$be_dir"
      PORT=$be_port HOST=0.0.0.0 nohup node index.js > "/tmp/${slug}-server.log" 2>&1 &
      cd "$NSAF_DIR"
      break
    elif [ -f "$be_dir/src/index.js" ]; then
      cd "$be_dir"
      PORT=$be_port HOST=0.0.0.0 nohup node src/index.js > "/tmp/${slug}-server.log" 2>&1 &
      cd "$NSAF_DIR"
      break
    fi
  done

  # Find and start frontend
  for fe_dir in "$dir/client" "$dir/frontend"; do
    if [ -d "$fe_dir" ] && [ -f "$fe_dir/package.json" ]; then
      cd "$fe_dir"
      nohup npx vite --host 0.0.0.0 --port "$port" > "/tmp/${slug}-client.log" 2>&1 &
      cd "$NSAF_DIR"
      break
    fi
  done

  # Fallback: server-only app on the main port
  if ! ss -tlnp 2>/dev/null | grep -q ":${port} "; then
    for entry in "$dir/server/index.js" "$dir/server/src/index.js" "$dir/index.js"; do
      if [ -f "$entry" ]; then
        dir_of=$(dirname "$entry")
        cd "$dir_of"
        PORT=$port HOST=0.0.0.0 nohup node "$(basename "$entry")" > "/tmp/${slug}.log" 2>&1 &
        cd "$NSAF_DIR"
        break
      fi
    done
  fi
done
