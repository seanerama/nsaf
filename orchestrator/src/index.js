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
import { initDb, closeDb, projectUpdate, projectsByStatus, queueEnqueue } from './db.js';
import { canDequeue, dequeueNext, getQueueDepth, getActiveCount } from './queue.js';
import { allocatePorts, releasePorts } from './ports.js';
import { createDatabase } from './postgres.js';
import { scaffoldProject } from './scaffolder.js';
import { spawnSession, getActiveSessions } from './spawner.js';
import { pollAllProjects, pollProject } from './poller.js';
import { checkStalls } from './stall.js';
import { handleCompletion } from './completion.js';
import { notifyStall, notifyCompletion } from './notify.js';
import { compileDigest, sendDigest } from './digest.js';
import { checkPromotions } from './promotion.js';

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
  stallTimeout: parseInt(process.env.NSAF_STALL_TIMEOUT_MINUTES || '30', 10),
  pollInterval: parseInt(process.env.NSAF_POLL_INTERVAL_SECONDS || '30', 10) * 1000,
  webexBotToken: process.env.WEBEX_BOT_TOKEN || '',
  webexOwnerId: process.env.WEBEX_OWNER_PERSON_ID || '',
  resendApiKey: process.env.RESEND_API_KEY || '',
  ownerEmail: process.env.NSAF_OWNER_EMAIL || '',
  digestHour: parseInt(process.env.NSAF_DIGEST_HOUR || '21', 10),
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
    const projectType = item.project_type || 'app';
    log.info({ slug, projectType, queueDepth: getQueueDepth(), active: getActiveCount() }, 'Dequeued project');

    try {
      if (projectType === 'studyws' || projectType === 'story') {
        // Content-generation pipelines: no ports, no database, no scaffold
        const { mkdirSync } = await import('fs');
        mkdirSync(item.project_dir, { recursive: true });

        const project = { ...item, project_dir: item.project_dir, project_type: projectType };
        spawnSession(project, config.claudeCommand);
        log.info({ slug, projectType }, 'Content-pipeline session spawned');

      } else {
        // Standard app build
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
      }

    } catch (err) {
      log.error({ slug, error: err.message }, 'Failed to launch project');
      if (projectType === 'studyws' || projectType === 'story') {
        projectUpdate(slug, { status: 'queued' });
      } else {
        releasePorts(item.id);
        projectUpdate(slug, { status: 'queued', port_start: null, port_end: null });
      }
      queueEnqueue(item.id);
    }
  }
}

let lastPollTime = 0;
let digestSentToday = false;

async function monitorProjects() {
  // Poll active projects for state changes
  const polled = pollAllProjects();

  // Check for completions
  const building = projectsByStatus('building');
  for (const project of building) {
    const statePath = `${project.project_dir}/sdd-output/STATE.md`;
    try {
      const result = pollProject(project);
      if (result && result.complete) {
        handleCompletion(project, project.port_start);
        await notifyCompletion(
          { ...project, deployed_url: `http://localhost:${project.port_start}` },
          config.webexBotToken,
          config.webexOwnerId
        );
      }
    } catch { /* already logged by poller */ }
  }

  // Check for stalls
  const stalled = checkStalls(config.stallTimeout);
  for (const project of stalled) {
    await notifyStall(project, config.webexBotToken, config.webexOwnerId);
  }

  // Check for promotions
  checkPromotions(config.claudeCommand);

  // Evening digest
  const hour = new Date().getHours();
  if (hour >= config.digestHour && !digestSentToday) {
    const digest = compileDigest();
    if (digest.totalAttempted > 0) {
      await sendDigest(digest, config.resendApiKey, config.ownerEmail);
    }
    digestSentToday = true;
  }
  if (hour < config.digestHour) {
    digestSentToday = false;
  }
}

function mainLoop() {
  const now = Date.now();

  // Process queue every cycle
  processQueue().catch(err => {
    log.error({ error: err.message }, 'Queue processing error');
  });

  // Poll/monitor at the polling interval
  if (now - lastPollTime >= config.pollInterval) {
    lastPollTime = now;
    monitorProjects().catch(err => {
      log.error({ error: err.message }, 'Monitoring error');
    });
  }

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
