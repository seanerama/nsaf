import { spawn } from 'child_process';
import { createWriteStream, readFileSync } from 'fs';
import { join } from 'path';
import pino from 'pino';
import { projectUpdate, projectGet } from './db.js';
import { launchApp } from './app-launcher.js';

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

IMPORTANT — You have MCP tools available for generating art assets:
- PixelLab MCP tools (mcp__pixellab__*) for pixel art sprites, characters, tiles, animations
- Leonardo AI MCP tools (mcp__leonardo-ai__*) for illustrations, backgrounds, icons
USE THESE TOOLS to generate real visual assets. Do NOT use placeholder graphics or emoji.

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

  // Strip API keys so Claude Code uses the subscription, not the API
  const cleanEnv = { ...process.env };
  delete cleanEnv.ANTHROPIC_API_KEY;
  delete cleanEnv.OPENAI_API_KEY;
  delete cleanEnv.GOOGLE_API_KEY;

  const child = spawn(bin, args, {
    cwd: dir,
    stdio: ['ignore', 'pipe', 'pipe'],
    env: cleanEnv,
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

    // Check if the build actually completed by looking for deployer artifacts
    let completed = false;
    try {
      const statePath = join(dir, 'sdd-output', 'STATE.md');
      const stateContent = readFileSync(statePath, 'utf-8');
      if (stateContent.includes('Project Deployer') &&
          (stateContent.includes('[x] Project Deployer') ||
           stateContent.match(/completed_roles:.*Project Deployer/))) {
        completed = true;
      }
      // Also check build log for completion markers
      const buildLog = readFileSync(join(dir, 'build.log'), 'utf-8');
      if (buildLog.includes('Workflow Complete') || buildLog.includes('workflow complete')) {
        completed = true;
      }
    } catch { /* can't read files */ }

    // Re-read project from DB to get current port_start (set after dequeue)
    const currentProject = projectGet(slug) || project;
    const portStart = currentProject.port_start;

    if (completed || code === 0) {
      // Auto-launch the app
      const launched = launchApp(dir, portStart);
      const deployedUrl = launched ? launched.url : `http://localhost:${portStart}`;

      projectUpdate(slug, {
        status: 'deployed-local',
        deployed_url: deployedUrl,
        completed_at: new Date().toISOString(),
        last_state_change: new Date().toISOString(),
      });
      log.info({ slug, deployedUrl, strategy: launched?.strategy, completed }, 'Build finished and app launched');
      log.warn({ slug }, 'Session exited clean but completion not confirmed');
    } else {
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
