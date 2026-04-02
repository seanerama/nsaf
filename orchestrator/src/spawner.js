import { spawn } from 'child_process';
import { createWriteStream, readFileSync } from 'fs';
import { join } from 'path';
import pino from 'pino';
import { projectUpdate } from './db.js';

const log = pino({ name: 'nsaf.spawner' });

const activeSessions = new Map();

export function getActiveSessions() {
  return activeSessions;
}

export function spawnSession(project, claudeCommandTemplate) {
  const slug = project.slug;
  const dir = project.project_dir;

  // Read the vision document for context
  let visionContext = '';
  try {
    const visionPath = join(dir, 'sdd-output', 'vision-document.md');
    visionContext = readFileSync(visionPath, 'utf-8');
  } catch { /* no vision doc */ }

  const prompt = `You are building a web app autonomously with NO human interaction. Read sdd-output/vision-document.md for the full spec. Do NOT ask any questions — make all decisions yourself based on the vision document and preferences. Build the complete app end-to-end.

Here is the vision document:

${visionContext}

Now run: /sdd:start --from architect`;

  // Build args directly instead of string splitting to preserve quoted prompt
  const bin = claudeCommandTemplate.split(/\s+/)[0];
  const args = ['-p', prompt, '--dangerously-skip-permissions'];

  const command = `${bin} -p "${prompt}" --dangerously-skip-permissions`;
  log.info({ slug, command, cwd: dir }, 'Spawning Claude Code session');

  const logPath = join(dir, 'build.log');
  const logStream = createWriteStream(logPath, { flags: 'a' });

  const child = spawn(bin, args, {
    cwd: dir,
    stdio: ['ignore', 'pipe', 'pipe'],
    env: { ...process.env },
  });

  child.stdout.pipe(logStream);
  child.stderr.pipe(logStream);

  // Update project status
  projectUpdate(slug, {
    status: 'building',
    started_at: new Date().toISOString(),
    last_state_change: new Date().toISOString(),
  });

  activeSessions.set(slug, { child, project });

  child.on('exit', (code, signal) => {
    logStream.end();
    activeSessions.delete(slug);

    log.info({ slug, code, signal }, 'Claude Code session exited');

    if (code === 0) {
      // Session completed — poller will detect final state
      projectUpdate(slug, { last_state_change: new Date().toISOString() });
    } else {
      // Non-zero exit — mark for stall detection
      log.warn({ slug, code }, 'Session exited with error');
    }
  });

  child.on('error', (err) => {
    logStream.end();
    activeSessions.delete(slug);
    log.error({ slug, error: err.message }, 'Failed to spawn session');
  });

  return child;
}

export function getSessionCount() {
  return activeSessions.size;
}
