import { existsSync, readFileSync, writeFileSync } from 'fs';
import { join } from 'path';
import pino from 'pino';

const log = pino({ name: 'nsaf.dockerize' });

/**
 * Generate a Dockerfile for a project based on its structure.
 * Returns the path to the generated Dockerfile, or null if it already exists.
 */
export function generateDockerfile(projectDir) {
  const dockerfilePath = join(projectDir, 'Dockerfile');

  if (existsSync(dockerfilePath)) {
    log.info({ projectDir }, 'Dockerfile already exists');
    return dockerfilePath;
  }

  const structure = detectStructure(projectDir);
  const dockerfile = buildDockerfile(structure);

  if (!dockerfile) {
    log.warn({ projectDir, structure: structure.type }, 'Could not generate Dockerfile');
    return null;
  }

  writeFileSync(dockerfilePath, dockerfile);
  log.info({ projectDir, type: structure.type }, 'Dockerfile generated');

  // Also patch server for production if needed
  if (structure.needsStaticServing) {
    patchServerForProduction(projectDir, structure);
  }

  return dockerfilePath;
}

function detectStructure(dir) {
  const result = {
    type: 'unknown',
    hasClient: false,
    hasServer: false,
    hasFrontend: false,
    hasBackend: false,
    hasRootPackage: false,
    serverEntry: null,
    clientDir: null,
    serverDir: null,
    port: 3000,
    needsStaticServing: false,
  };

  // Check for root package.json
  const rootPkg = join(dir, 'package.json');
  if (existsSync(rootPkg)) {
    result.hasRootPackage = true;
    try {
      const pkg = JSON.parse(readFileSync(rootPkg, 'utf-8'));
      const scripts = pkg.scripts || {};
      if (scripts.start) {
        result.type = 'simple-node';
        return result;
      }
    } catch { /* continue detection */ }
  }

  // Check for client/server or frontend/backend split
  for (const [clientName, serverName] of [['client', 'server'], ['frontend', 'backend']]) {
    const clientDir = join(dir, clientName);
    const serverDir = join(dir, serverName);

    if (existsSync(join(clientDir, 'package.json')) && existsSync(join(serverDir, 'package.json'))) {
      result.type = 'fullstack-split';
      result.clientDir = clientName;
      result.serverDir = serverName;
      result.hasClient = true;
      result.hasServer = true;

      // Find server entry point
      for (const entry of ['index.js', 'src/index.js', 'app.js', 'src/app.js']) {
        if (existsSync(join(serverDir, entry))) {
          result.serverEntry = entry;
          break;
        }
      }

      // Check if server already serves static files
      try {
        const serverCode = readFileSync(join(serverDir, result.serverEntry || 'index.js'), 'utf-8');
        result.needsStaticServing = !serverCode.includes('express.static') && !serverCode.includes('sendFile');
      } catch {
        result.needsStaticServing = true;
      }

      return result;
    }
  }

  // Check for server-only (with index.js)
  for (const entry of ['server/index.js', 'server/src/index.js', 'src/index.js', 'index.js']) {
    if (existsSync(join(dir, entry))) {
      result.type = 'server-only';
      result.serverEntry = entry;
      return result;
    }
  }

  // Check for static site (has index.html or build output)
  if (existsSync(join(dir, 'index.html')) || existsSync(join(dir, 'dist', 'index.html'))) {
    result.type = 'static';
    return result;
  }

  return result;
}

function buildDockerfile(structure) {
  switch (structure.type) {
    case 'fullstack-split':
      return buildFullstackDockerfile(structure);
    case 'simple-node':
      return buildSimpleNodeDockerfile(structure);
    case 'server-only':
      return buildServerOnlyDockerfile(structure);
    case 'static':
      return buildStaticDockerfile(structure);
    default:
      return buildFallbackDockerfile(structure);
  }
}

function buildFullstackDockerfile(s) {
  return `FROM node:20-alpine

WORKDIR /app

# Install root dependencies (if any)
COPY package*.json ./
RUN npm install --ignore-scripts 2>/dev/null || true

# Install server dependencies
COPY ${s.serverDir}/package*.json ./${s.serverDir}/
RUN cd ${s.serverDir} && npm install

# Install client dependencies and build
COPY ${s.clientDir}/package*.json ./${s.clientDir}/
RUN cd ${s.clientDir} && npm install
COPY ${s.clientDir}/ ./${s.clientDir}/
RUN cd ${s.clientDir} && npm run build

# Copy server code
COPY ${s.serverDir}/ ./${s.serverDir}/

# Copy any root config files
COPY *.js *.json *.env.example ./ 2>/dev/null || true

ENV NODE_ENV=production
ENV PORT=3000
EXPOSE 3000

CMD ["node", "${s.serverDir}/${s.serverEntry || 'index.js'}"]
`;
}

function buildSimpleNodeDockerfile(s) {
  return `FROM node:20-alpine

WORKDIR /app

COPY package*.json ./
RUN npm install

COPY . .
RUN npm run build 2>/dev/null || true

ENV NODE_ENV=production
ENV PORT=3000
EXPOSE 3000

CMD ["npm", "start"]
`;
}

function buildServerOnlyDockerfile(s) {
  return `FROM node:20-alpine

WORKDIR /app

COPY package*.json ./
RUN npm install

COPY . .

ENV NODE_ENV=production
ENV PORT=3000
EXPOSE 3000

CMD ["node", "${s.serverEntry}"]
`;
}

function buildStaticDockerfile(s) {
  return `FROM node:20-alpine AS build

WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
RUN npm run build 2>/dev/null || true

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY --from=build /app/index.html /usr/share/nginx/html/ 2>/dev/null || true
EXPOSE 3000
CMD ["nginx", "-g", "daemon off;", "-c", "/dev/stdin"]
`;
}

function buildFallbackDockerfile(s) {
  return `FROM node:20-alpine

WORKDIR /app

COPY package*.json ./
RUN npm install 2>/dev/null || true

COPY . .
RUN npm run build 2>/dev/null || true

ENV NODE_ENV=production
ENV PORT=3000
EXPOSE 3000

CMD ["npm", "start"]
`;
}

function patchServerForProduction(projectDir, structure) {
  const serverFile = join(projectDir, structure.serverDir, structure.serverEntry || 'index.js');

  if (!existsSync(serverFile)) return;

  let content = readFileSync(serverFile, 'utf-8');

  // Fix CORS — replace hardcoded localhost origins with wildcard
  content = content.replace(
    /cors\(\{[^}]*origin:\s*\[[^\]]*\][^}]*\}\)/g,
    "cors({ origin: process.env.CORS_ORIGIN || '*' })"
  );

  // Add static file serving before error handler if not present
  if (!content.includes('express.static') && content.includes('errorHandler')) {
    const clientDist = `../../${structure.clientDir}/dist`;
    const staticBlock = `
// Serve static frontend in production
import { dirname } from 'path';
const __serve_dir = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '${clientDist}');
app.use(express.static(__serve_dir));
app.get('*', (req, res, next) => {
  if (req.path.startsWith('/api')) return next();
  res.sendFile(path.join(__serve_dir, 'index.html'));
});

`;
    content = content.replace(
      /app\.use\(errorHandler\)/,
      staticBlock + 'app.use(errorHandler)'
    );
  }

  // Fix hardcoded port
  content = content.replace(
    /const PORT = .*?(\d{4})/,
    'const PORT = process.env.PORT || 3000'
  );

  writeFileSync(serverFile, content);
  log.info({ serverFile }, 'Patched server for production');
}
