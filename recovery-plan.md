# NSAF Recovery Plan & Operations Runbook

## Service Overview

| Service | Type | Managed By |
|---------|------|------------|
| nsaf-orchestrator | systemd | Node.js process |
| nsaf-flask | systemd | Python/Flask process |
| Idea generator | cron | Python script (daily 7 AM) |
| PostgreSQL | system service | Per-app databases |
| SQLite (nsaf.db) | file | Shared state store |

## Health Checks

### Automated Checks (add to cron)

```bash
# Add to crontab — runs every 5 minutes
*/5 * * * * /opt/nsaf/scripts/healthcheck.sh >> /var/log/nsaf-health.log 2>&1
```

### healthcheck.sh

```bash
#!/bin/bash
# NSAF Health Check
TIMESTAMP=$(date -Iseconds)
ERRORS=0

# Check orchestrator
if ! systemctl is-active --quiet nsaf-orchestrator; then
    echo "$TIMESTAMP ERROR: nsaf-orchestrator is not running"
    ERRORS=$((ERRORS + 1))
fi

# Check Flask app
if ! curl -sf http://localhost:${NSAF_FLASK_PORT:-5000}/select > /dev/null 2>&1; then
    echo "$TIMESTAMP ERROR: Flask app not responding on /select"
    ERRORS=$((ERRORS + 1))
fi

# Check PostgreSQL
if ! pg_isready -q; then
    echo "$TIMESTAMP ERROR: PostgreSQL is not ready"
    ERRORS=$((ERRORS + 1))
fi

# Check disk space (warn at 80%)
DISK_PCT=$(df /opt/nsaf --output=pcent | tail -1 | tr -d ' %')
if [ "$DISK_PCT" -gt 80 ]; then
    echo "$TIMESTAMP WARN: Disk usage at ${DISK_PCT}%"
fi

# Check SQLite integrity
if ! sqlite3 /opt/nsaf/nsaf.db "PRAGMA integrity_check;" | grep -q "ok"; then
    echo "$TIMESTAMP ERROR: SQLite integrity check failed"
    ERRORS=$((ERRORS + 1))
fi

if [ "$ERRORS" -eq 0 ]; then
    echo "$TIMESTAMP OK: All checks passed"
fi
```

## Backup Strategy

### What to Back Up

| Item | Location | Frequency | Method |
|------|----------|-----------|--------|
| SQLite database | nsaf.db | Every 6 hours | File copy (while WAL checkpointed) |
| Preferences | preferences.md | On change | Git |
| Environment config | .env | On change | Encrypted copy |
| Project directories | projects/ | Daily | rsync to backup volume |

### Backup Script

```bash
#!/bin/bash
# /opt/nsaf/scripts/backup.sh — run via cron every 6 hours
BACKUP_DIR="/opt/nsaf-backups/$(date +%Y-%m-%d)"
mkdir -p "$BACKUP_DIR"

# Checkpoint WAL before copying SQLite
sqlite3 /opt/nsaf/nsaf.db "PRAGMA wal_checkpoint(TRUNCATE);"
cp /opt/nsaf/nsaf.db "$BACKUP_DIR/nsaf.db"

# Backup preferences
cp /opt/nsaf/preferences.md "$BACKUP_DIR/"

# Backup .env (encrypted)
gpg --symmetric --cipher-algo AES256 -o "$BACKUP_DIR/env.gpg" /opt/nsaf/.env

# Retain 7 days of backups
find /opt/nsaf-backups -maxdepth 1 -type d -mtime +7 -exec rm -rf {} \;

echo "$(date -Iseconds) Backup complete: $BACKUP_DIR"
```

Cron entry:
```
0 */6 * * * /opt/nsaf/scripts/backup.sh >> /var/log/nsaf-backup.log 2>&1
```

## Disaster Recovery

### Scenario 1: Orchestrator Crash

**Symptoms**: No new projects dequeued, active builds orphaned.

**Recovery**:
```bash
# Check status
sudo systemctl status nsaf-orchestrator
journalctl -u nsaf-orchestrator --since "1 hour ago"

# Restart (systemd auto-restarts, but manual if needed)
sudo systemctl restart nsaf-orchestrator

# The orchestrator re-reads SQLite on startup.
# Orphaned "building" projects will be detected as stalled
# after NSAF_STALL_TIMEOUT_MINUTES and can be restarted via Webex.
```

### Scenario 2: Flask App Down

**Symptoms**: Selection UI unreachable, Webex bot unresponsive.

**Recovery**:
```bash
sudo systemctl restart nsaf-flask
curl http://localhost:5000/select  # Verify it's back
```

### Scenario 3: SQLite Corruption

**Symptoms**: Both services failing with database errors.

**Recovery**:
```bash
# Stop both services
sudo systemctl stop nsaf-orchestrator nsaf-flask

# Check integrity
sqlite3 /opt/nsaf/nsaf.db "PRAGMA integrity_check;"

# If corrupted, restore from backup
cp /opt/nsaf-backups/latest/nsaf.db /opt/nsaf/nsaf.db

# Restart
sudo systemctl start nsaf-orchestrator nsaf-flask
```

### Scenario 4: PostgreSQL Down

**Symptoms**: New project scaffolding fails (DB provisioning step). Existing locally-deployed apps using Postgres will also fail.

**Recovery**:
```bash
sudo systemctl restart postgresql
pg_isready  # Verify

# The orchestrator will retry DB provisioning on the next queue cycle.
# No manual intervention needed for the NSAF process itself.
```

### Scenario 5: Disk Full

**Symptoms**: Builds fail, SQLite writes fail, logs stop.

**Recovery**:
```bash
# Check disk usage
df -h /opt/nsaf

# Clean up scrapped projects
# (Use Webex "skip" to scrap, then clean dirs)
ls /opt/nsaf/projects/

# Remove old build logs
find /opt/nsaf/projects/ -name "build.log" -mtime +7 -delete

# Remove old backups
find /opt/nsaf-backups -maxdepth 1 -type d -mtime +3 -exec rm -rf {} \;

# Prune old ideas from SQLite (optional)
sqlite3 /opt/nsaf/nsaf.db "DELETE FROM ideas WHERE date < date('now', '-30 days');"
```

### Scenario 6: Full Server Rebuild

```bash
# 1. Install prerequisites (Node.js, Python, PostgreSQL, Claude Code)
# 2. Clone repo
git clone <repo-url> /opt/nsaf

# 3. Restore .env
gpg --decrypt /path/to/env.gpg > /opt/nsaf/.env

# 4. Restore SQLite
cp /path/to/backup/nsaf.db /opt/nsaf/nsaf.db

# 5. Run setup
cd /opt/nsaf && bash scripts/setup.sh

# 6. Start services
sudo systemctl start nsaf-orchestrator nsaf-flask

# 7. Restore project directories (if needed)
rsync -av /path/to/backup/projects/ /opt/nsaf/projects/
```

## Alert Thresholds

| Metric | Threshold | Channel | Action |
|--------|-----------|---------|--------|
| Service down | Any service not running | Webex | Auto-restart via systemd; manual check if repeated |
| Build stalled | No progress for 30 min | Webex | Restart or skip via bot command |
| Disk usage | > 80% | Webex | Clean up scrapped projects and old logs |
| Queue depth | > 20 projects | Webex (info) | Informational only — builds will process in order |
| Daily builds failed | > 50% failure rate | Evening digest | Review logs, check Claude Code auth |

## Maintenance Windows

- **Daily**: Idea generation at 7 AM, digest at 9 PM (automated)
- **Weekly**: Review scrapped projects, clean up stale directories
- **Monthly**: Update dependencies (`npm update`, `pip install --upgrade`), review security report items

## Log Locations

| Log | Location | Retention |
|-----|----------|-----------|
| Orchestrator | `journalctl -u nsaf-orchestrator` | systemd default (managed by journald) |
| Flask app | `journalctl -u nsaf-flask` | systemd default |
| Idea generation | `/var/log/nsaf-ideas.log` | Rotate weekly |
| Health checks | `/var/log/nsaf-health.log` | Rotate weekly |
| Backups | `/var/log/nsaf-backup.log` | Rotate weekly |
| Per-project builds | `projects/<slug>/build.log` | Cleaned on scrap |

## Operational Commands Quick Reference

```bash
# Service management
sudo systemctl status nsaf-orchestrator nsaf-flask
sudo systemctl restart nsaf-orchestrator
journalctl -u nsaf-orchestrator -f  # Follow live logs

# Database inspection
sqlite3 /opt/nsaf/nsaf.db "SELECT slug, status FROM projects ORDER BY created_at DESC LIMIT 10;"
sqlite3 /opt/nsaf/nsaf.db "SELECT COUNT(*) FROM queue;"
sqlite3 /opt/nsaf/nsaf.db "SELECT key, value FROM config;"

# Manual idea generation
cd /opt/nsaf && source venv/bin/activate
python idea-generator/generate.py --dry-run

# Port allocation check
sqlite3 /opt/nsaf/nsaf.db "SELECT p.slug, po.port_start, po.port_end FROM ports po JOIN projects p ON po.project_id = p.id;"
```
