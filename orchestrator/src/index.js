#!/usr/bin/env node
/**
 * NSAF Orchestrator — Main entry point.
 *
 * Usage:
 *   node src/index.js             Start the orchestrator
 *   node src/index.js --init-db   Initialize/migrate the database only
 */

import 'dotenv/config';
import pino from 'pino';
import { initDb, closeDb, projectUpdate, projectsByStatus } from './db.js';
import { canDequeue, dequeueNext, getQueueDepth, getActiveCount } from './queue.js';
import { allocatePorts, releasePorts } from './ports.js';
import { createDatabase } from './postgres.js';
import { scaffoldProject } from './scaffolder.js';
import { spawnSession, getActiveSessions } from './spawner.js';

const log = pino({ name: 'nsaf.orchestrator' });

const config = {
  dbPath: process.env.NSAF_DB_PATH || './nsaf.db',
  concurrency: parseInt(process.env.NSAF_CONCURRENCY || '2', 10),
  portRangeStart: parseInt(process.env.NSAF_PORT_RANGE_START || '5020', 10),
  portRangeEnd: parseInt(process.env.NSAF_PORT_RANGE_END || '5999', 10),
  queuePollInterval: parseInt(process.env.NSAF_QUEUE_POLL_INTERVAL_SECONDS || '10', 10) * 1000,
  projectsDir: process.env.NSAF_PROJECTS_DIR || './projects',
  pgHost: process.env.POSTGRES_HOST || 'localhost',
  pgPort: process.env.POSTGRES_PORT || '5432',
  pgUser: process.env.POSTGRES_USER || 'nsaf_admin',
  pgPassword: process.env.POSTGRES_PASSWORD || '',
  claudeCommand: process.env.NSAF_CLAUDE_COMMAND || 'claude -p "{prompt}" --dangerously-skip-permissions',
};

let running = true;
let loopTimer = null;

function init() {
  log.info('Initializing database');
  initDb(config.dbPath);
  log.info({ dbPath: config.dbPath }, 'Database initialized');
}

async function processQueue() {
  if (!running) return;

  while (canDequeue(config.concurrency)) {
    const item = dequeueNext();
    if (!item) break;

    const slug = item.slug;
    log.info({ slug, queueDepth: getQueueDepth(), active: getActiveCount() }, 'Dequeued project');

    try {
      // Allocate ports
      const ports = allocatePorts(item.id, config.portRangeStart, config.portRangeEnd);
      projectUpdate(slug, { port_start: ports.portStart, port_end: ports.portEnd });
      log.info({ slug, ports }, 'Ports allocated');

      // Provision database
      let dbInfo = null;
      try {
        dbInfo = createDatabase(slug, config.pgHost, config.pgPort, config.pgUser, config.pgPassword);
        projectUpdate(slug, { db_name: dbInfo.dbName });
        log.info({ slug, dbName: dbInfo.dbName }, 'Database provisioned');
      } catch (err) {
        log.warn({ slug, error: err.message }, 'Database provisioning failed — continuing without DB');
      }

      // Scaffold project
      const project = { ...item, project_dir: item.project_dir };
      scaffoldProject(project, ports, dbInfo, {
        portStart: ports.portStart,
        portEnd: ports.portEnd,
      });

      // Spawn Claude Code session
      spawnSession(project, config.claudeCommand);

    } catch (err) {
      log.error({ slug, error: err.message }, 'Failed to launch project');
      projectUpdate(slug, { status: 'queued' }); // Re-queue on failure
    }
  }
}

function mainLoop() {
  processQueue().catch(err => {
    log.error({ error: err.message }, 'Queue processing error');
  });

  if (running) {
    loopTimer = setTimeout(mainLoop, config.queuePollInterval);
  }
}

function shutdown() {
  log.info('Shutting down gracefully');
  running = false;

  if (loopTimer) {
    clearTimeout(loopTimer);
  }

  // Don't kill child processes — they'll continue running
  // Record shutdown state for recovery on restart
  const sessions = getActiveSessions();
  for (const [slug] of sessions) {
    log.info({ slug }, 'Leaving active session running');
  }

  closeDb();
  log.info('Orchestrator stopped');
  process.exit(0);
}

// Main
if (process.argv.includes('--init-db')) {
  init();
  log.info('Database initialized successfully');
  closeDb();
  process.exit(0);
}

init();

// Recovery: check for projects that were "building" when we last stopped
const staleBuilding = projectsByStatus('building');
for (const p of staleBuilding) {
  const sessions = getActiveSessions();
  if (!sessions.has(p.slug)) {
    log.warn({ slug: p.slug }, 'Found orphaned building project — will be detected as stalled');
  }
}

log.info({
  concurrency: config.concurrency,
  portRange: `${config.portRangeStart}-${config.portRangeEnd}`,
  pollInterval: `${config.queuePollInterval / 1000}s`,
}, 'Orchestrator starting');

process.on('SIGTERM', shutdown);
process.on('SIGINT', shutdown);

mainLoop();
