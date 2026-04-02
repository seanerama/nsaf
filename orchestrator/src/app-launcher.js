import { spawn } from 'child_process';
import { existsSync, readFileSync } from 'fs';
import { join } from 'path';
import pino from 'pino';

const log = pino({ name: 'nsaf.launcher' });

/**
 * Detect how to start an app and launch it on 0.0.0.0.
 * Returns the actual URL the app is running on, or null on failure.
 */
export function launchApp(projectDir, portStart) {
  const strategies = [
    tryStartScript,
    tryBackendFrontendSplit,
    tryServerIndex,
    tryNpmStart,
  ];

  for (const strategy of strategies) {
    const result = strategy(projectDir, portStart);
    if (result) {
      log.info({ projectDir, strategy: result.strategy, url: result.url }, 'App launched');
      return result;
    }
  }

  log.warn({ projectDir }, 'Could not determine how to start the app');
  return null;
}

function tryStartScript(projectDir, portStart) {
  const startSh = join(projectDir, 'start.sh');
  if (!existsSync(startSh)) return null;

  const child = spawn('bash', [startSh], {
    cwd: projectDir,
    stdio: ['ignore', 'pipe', 'pipe'],
    detached: true,
    env: { ...process.env, PORT: String(portStart), HOST: '0.0.0.0' },
  });
  child.unref();

  return { strategy: 'start.sh', url: `http://localhost:${portStart}`, pid: child.pid };
}

function tryBackendFrontendSplit(projectDir, portStart) {
  const backendDir = join(projectDir, 'backend');
  const serverDir = join(projectDir, 'server');
  const clientDir = join(projectDir, 'client');
  const frontendDir = join(projectDir, 'frontend');

  const be = existsSync(join(backendDir, 'package.json')) ? backendDir :
             existsSync(join(serverDir, 'package.json')) ? serverDir : null;
  const fe = existsSync(join(clientDir, 'package.json')) ? clientDir :
             existsSync(join(frontendDir, 'package.json')) ? frontendDir : null;

  if (!be && !fe) return null;

  const backendPort = portStart + 1;
  let url = `http://localhost:${portStart}`;

  // Start backend
  if (be) {
    const beChild = spawn('node', ['index.js'], {
      cwd: be,
      stdio: 'ignore',
      detached: true,
      env: { ...process.env, PORT: String(backendPort), HOST: '0.0.0.0' },
    });
    beChild.unref();
    log.info({ dir: be, port: backendPort }, 'Backend started');

    // If no frontend, backend IS the app
    if (!fe) {
      url = `http://localhost:${backendPort}`;
    }
  }

  // Start frontend (Vite dev server on 0.0.0.0)
  if (fe) {
    const feChild = spawn('npx', ['vite', '--host', '0.0.0.0', '--port', String(portStart)], {
      cwd: fe,
      stdio: 'ignore',
      detached: true,
      env: { ...process.env },
    });
    feChild.unref();
    log.info({ dir: fe, port: portStart }, 'Frontend started');
  }

  return { strategy: 'backend+frontend', url };
}

function tryServerIndex(projectDir, portStart) {
  const candidates = [
    join(projectDir, 'server', 'index.js'),
    join(projectDir, 'server', 'src', 'index.js'),
    join(projectDir, 'src', 'index.js'),
    join(projectDir, 'index.js'),
  ];

  const serverFile = candidates.find(f => existsSync(f));
  if (!serverFile) return null;

  // Check if there's also a client dir to serve
  const clientDir = join(projectDir, 'client');
  const hasClient = existsSync(join(clientDir, 'package.json'));

  // Start server
  const child = spawn('node', [serverFile], {
    cwd: projectDir,
    stdio: 'ignore',
    detached: true,
    env: { ...process.env, PORT: String(portStart), HOST: '0.0.0.0' },
  });
  child.unref();

  // If there's a separate client, start Vite too
  if (hasClient) {
    const fePort = portStart;
    const bePort = portStart + 1;

    // Restart server on backend port
    child.kill();
    const beChild = spawn('node', [serverFile], {
      cwd: projectDir,
      stdio: 'ignore',
      detached: true,
      env: { ...process.env, PORT: String(bePort), HOST: '0.0.0.0' },
    });
    beChild.unref();

    const feChild = spawn('npx', ['vite', '--host', '0.0.0.0', '--port', String(fePort)], {
      cwd: clientDir,
      stdio: 'ignore',
      detached: true,
      env: { ...process.env },
    });
    feChild.unref();

    return { strategy: 'server+client', url: `http://localhost:${fePort}` };
  }

  return { strategy: 'server-only', url: `http://localhost:${portStart}` };
}

function tryNpmStart(projectDir, portStart) {
  const pkg = join(projectDir, 'package.json');
  if (!existsSync(pkg)) return null;

  try {
    const pkgJson = JSON.parse(readFileSync(pkg, 'utf-8'));
    if (!pkgJson.scripts || !pkgJson.scripts.start) return null;
  } catch {
    return null;
  }

  const child = spawn('npm', ['start'], {
    cwd: projectDir,
    stdio: 'ignore',
    detached: true,
    env: { ...process.env, PORT: String(portStart), HOST: '0.0.0.0' },
  });
  child.unref();

  return { strategy: 'npm-start', url: `http://localhost:${portStart}` };
}
