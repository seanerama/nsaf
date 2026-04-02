import { spawn } from 'child_process';
import { createWriteStream } from 'fs';
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

  const prompt = '/sdd:start --from architect';
  const command = claudeCommandTemplate
    .replace('{prompt}', prompt);

  // Parse command into parts
  const parts = command.split(/\s+/);
  const bin = parts[0];
  const args = parts.slice(1);

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
