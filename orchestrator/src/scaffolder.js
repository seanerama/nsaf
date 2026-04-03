import { mkdirSync, writeFileSync, existsSync, readFileSync } from 'fs';
import { join } from 'path';
import { execSync } from 'child_process';
import pino from 'pino';
import { ideaGet } from './db.js';

let _detectedTools = null;

function getDetectedTools() {
  if (_detectedTools !== null) return _detectedTools;
  try {
    const toolsPath = join(process.env.NSAF_DIR || '.', 'detected-tools.json');
    _detectedTools = JSON.parse(readFileSync(toolsPath, 'utf-8'));
  } catch {
    _detectedTools = { tools: [], categories: {} };
  }
  return _detectedTools;
}

function hasToolCategory(category) {
  const tools = getDetectedTools();
  return (tools.categories[category] || []).length > 0;
}

function hasTool(name) {
  return getDetectedTools().tools.includes(name);
}

const log = pino({ name: 'nsaf.scaffolder' });

export function scaffoldProject(project, ports, dbInfo, preferences) {
  const dir = project.project_dir;

  // Create directory structure
  mkdirSync(join(dir, 'sdd-output'), { recursive: true });

  // Check for rebuild notes from a previous build
  let rebuildNotes = '';
  const rebuildNotesPath = join(dir, 'rebuild-notes.md');
  if (existsSync(rebuildNotesPath)) {
    rebuildNotes = readFileSync(rebuildNotesPath, 'utf-8');
  }

  // Write vision document from idea metadata
  const idea = project.idea_id ? ideaGet(project.idea_id) : null;
  let visionDoc = buildVisionDocument(project, idea, preferences);
  if (rebuildNotes) {
    visionDoc += `\n\n## Rebuild Instructions\n\nThis is a REBUILD. The previous version had issues. Pay special attention to:\n\n${rebuildNotes}\n`;
  }
  writeFileSync(join(dir, 'sdd-output', 'vision-document.md'), visionDoc);

  // Write .env for the generated app
  const envContent = buildEnvFile(project, ports, dbInfo);
  writeFileSync(join(dir, '.env'), envContent);

  // Write .gitignore
  writeFileSync(join(dir, '.gitignore'), 'node_modules/\n.env\nsdd-output/\n');

  // Init git repo
  if (!existsSync(join(dir, '.git'))) {
    execSync('git init', { cwd: dir, stdio: 'pipe' });
    execSync('git add .gitignore', { cwd: dir, stdio: 'pipe' });
    execSync('git commit -m "Initial commit: NSAF scaffolded project"', {
      cwd: dir,
      stdio: 'pipe',
    });
  }

  log.info({ slug: project.slug, dir }, 'Project scaffolded');
  return dir;
}

const GAME_CATEGORIES = new Set([
  'game', 'games', 'educational games', 'learning games', 'math games',
  'reading games', 'science games', 'puzzle games', 'arcade', 'platformer',
  'adventure', 'simulation',
]);

function isGameCategory(category) {
  const lower = (category || '').toLowerCase();
  return GAME_CATEGORIES.has(lower) || lower.includes('game');
}

function getVisualDesignSection(category) {
  const hasPixelLab = hasTool('pixellab');
  const hasLeonardo = hasTool('leonardo-ai');
  const hasRender = hasTool('render');
  const hasAnyArt = hasPixelLab || hasLeonardo;
  const isGame = isGameCategory(category);

  let sections = [];

  if (isGame) {
    sections.push(`## Visual Design Requirements

This is a GAME — it MUST be visually rich, animated, and engaging. No basic grids or placeholder graphics.`);

    if (hasAnyArt) {
      sections.push(`\n### Art Assets (REQUIRED)\nYou have access to MCP tools for generating art. USE THEM:`);

      if (hasPixelLab) {
        sections.push(`
- **PixelLab MCP** — Use for pixel art sprites, characters, tiles, and game objects:
  - \`mcp__pixellab__create_character\` — Create character sprites with multiple directional views
  - \`mcp__pixellab__animate_character\` — Animate characters (walk, idle, attack, etc.)
  - \`mcp__pixellab__create_isometric_tile\` — Create isometric tiles for game maps
  - \`mcp__pixellab__create_topdown_tileset\` — Create top-down tilesets
  - \`mcp__pixellab__create_sidescroller_tileset\` — Create platformer tilesets
  - \`mcp__pixellab__create_map_object\` — Create objects like trees, buildings, items`);
      }

      if (hasLeonardo) {
        sections.push(`
- **Leonardo AI MCP** — Use for illustrations, backgrounds, icons, and UI art:
  - \`mcp__leonardo-ai__high_definition_generalist\` — General purpose high-quality images
  - \`mcp__leonardo-ai__hyperrealistic\` — Photorealistic images
  - \`mcp__leonardo-ai__accurate_text_rendering\` — Images with readable text`);
      }
    }

    sections.push(`
### Animation (REQUIRED)
- Use CSS animations, Framer Motion, or canvas-based animation
- Characters and game objects should move, react, and animate
- Transitions between screens should be smooth
- Idle animations, hover effects, particle effects where appropriate

### Visual Standards
- NO placeholder rectangles, colored divs, or emoji-as-sprites${hasAnyArt ? '\n- Every game object should have a real generated sprite or illustration' : ''}
- Backgrounds should be illustrated or styled, not solid colors
- UI should feel like a polished game, not a web form
- Color palette should be vibrant and age-appropriate`);

  } else {
    // Non-game apps
    sections.push(`## Visual Design Requirements

Build a polished, professional-looking UI. Not a basic unstyled form.`);

    if (hasLeonardo) {
      sections.push(`
### MCP Art Tools (OPTIONAL)
You have access to image generation MCP tools. Use them where they add value:

- **Leonardo AI MCP** — Use for hero images, illustrations, icons, or branding:
  - \`mcp__leonardo-ai__high_definition_generalist\` — General purpose images
  - \`mcp__leonardo-ai__accurate_text_rendering\` — Images with readable text`);
    }

    sections.push(`
### UI Standards
- Clean, modern design with consistent spacing and typography
- Smooth transitions and micro-animations (Framer Motion or CSS)
- Responsive layout — works on mobile and desktop
- Professional color palette appropriate to the domain
- Real content and imagery, not Lorem Ipsum placeholders`);
  }

  // Deployment tools
  if (hasRender) {
    sections.push(`
### Deployment Tools Available
- **Render MCP** — \`mcp__render__*\` tools available for cloud deployment when promoted`);
  }

  return sections.join('\n');
}

function buildVisionDocument(project, idea, preferences) {
  const name = idea ? idea.name : project.slug;
  const description = idea ? idea.description : 'Auto-generated project';
  const category = idea ? idea.category : 'general';
  const complexity = idea ? idea.complexity : 'medium';

  let stack = {};
  if (idea && idea.suggested_stack) {
    try {
      stack = typeof idea.suggested_stack === 'string'
        ? JSON.parse(idea.suggested_stack)
        : idea.suggested_stack;
    } catch { /* use empty */ }
  }

  const stackStr = Object.entries(stack)
    .map(([k, v]) => `- **${k}**: ${v}`)
    .join('\n');

  return `# Vision Document: ${name}

## The Idea

${description}

## Problem Statement

This app addresses a need in the ${category} space. It was selected from NSAF's daily idea generation.

## Target Users

General users interested in ${category} applications.

## Success Criteria

- App is functional and deployed locally
- Core features work end-to-end
- Visually polished with custom artwork and animations
- Passes automated and manual QA checks

## Core Concepts

Category: ${category}
Complexity: ${complexity}

## Tech Stack

${stackStr || '- Use defaults from preferences'}

${getVisualDesignSection(category)}

## Scope (MVP)

Build a complete, working web application with:
- Frontend with responsive, polished UI
- Backend API
- Database for persistent storage
- Core feature set as described above

## Constraints

- Must be deployable locally on a single server
- Must use PostgreSQL for the database (connection string provided in .env)
- Port range allocated: ${preferences?.portStart || 'TBD'}-${preferences?.portEnd || 'TBD'}
`;
}

function buildEnvFile(project, ports, dbInfo) {
  const lines = [
    `# Generated by NSAF for project: ${project.slug}`,
    `PROJECT_NAME=${project.slug}`,
    `PORT=${ports.portStart}`,
    `PORT_RANGE_START=${ports.portStart}`,
    `PORT_RANGE_END=${ports.portEnd}`,
  ];

  if (dbInfo) {
    lines.push(`DATABASE_URL=${dbInfo.connectionString}`);
    lines.push(`DB_NAME=${dbInfo.dbName}`);
  }

  return lines.join('\n') + '\n';
}
