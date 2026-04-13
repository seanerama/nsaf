import { spawn } from 'child_process';
import { createWriteStream, readFileSync, writeFileSync, existsSync, readdirSync } from 'fs';
import { join } from 'path';
import pino from 'pino';
import { projectUpdate, projectGet } from './db.js';
import { launchApp } from './app-launcher.js';

let _detectedTools = null;
function getDetectedTools() {
  if (_detectedTools !== null) return _detectedTools;
  try {
    const toolsPath = join(process.cwd(), 'detected-tools.json');
    _detectedTools = JSON.parse(readFileSync(toolsPath, 'utf-8'));
  } catch {
    _detectedTools = { tools: [], categories: {} };
  }
  return _detectedTools;
}

const log = pino({ name: 'nsaf.spawner' });

const activeSessions = new Map();

export function getActiveSessions() {
  return activeSessions;
}

export function spawnSession(project, claudeCommandTemplate) {
  const slug = project.slug;
  const dir = project.project_dir;

  const projectType = project.project_type || 'app';
  let prompt;

  if (projectType === 'studyws') {
    // StudyWS content generation
    let swsConfig = '';
    try {
      swsConfig = readFileSync(join(dir, 'studyws-config.json'), 'utf-8');
    } catch { /* no config */ }

    const config = swsConfig ? JSON.parse(swsConfig) : {};
    const topic = config.topic || project.slug;
    const chapters = config.chapters || 10;
    const level = config.level || 'intermediate';
    const notes = config.notes || '';
    const sourceUrl = config.source_url || '';

    let sourceInstructions = '';
    if (sourceUrl) {
      sourceInstructions = `
IMPORTANT — Source Material:
Before running the pipeline, fetch and read this document: ${sourceUrl}
Use it as the primary source for structuring the chapters and content.
The topic name and chapter outline should be derived from this document's content.
If it's a PDF, use WebFetch or download it to read its contents.
After reading the source, use its structure to inform the /sws:start topic and /sws:scope outline.
`;
    }

    // Copy animation strategy into project dir as CLAUDE.md so sub-agents inherit it
    try {
      const nsafDir = process.env.NSAF_DIR || process.cwd();
      const animStrategy = readFileSync(join(nsafDir, 'config', 'animation-strategy.md'), 'utf-8');
      const claudeMd = `# Project Instructions

## Study Guide Animation Requirements

When generating HTML study guides, you MUST include inline SVG/CSS animations for key concepts. Do NOT use placeholder hooks or static Mermaid diagrams alone.

${animStrategy}

## Theme

- Dark background (#0d1117), blue accents (#58a6ff)
- Self-contained HTML — no external CDN dependencies except Mermaid
- Every guide should have 2-3 animated diagrams per chapter
`;
      writeFileSync(join(dir, 'CLAUDE.md'), claudeMd);
      log.info({ slug }, 'Wrote CLAUDE.md with animation strategy');
    } catch (err) {
      log.warn({ slug, error: err.message }, 'Could not write animation strategy');
    }

    // Detect existing output to resume from where we left off
    let resumeFrom = null;
    const outputBase = join(dir, 'output');
    if (existsSync(outputBase)) {
      const subdirs = readdirSync(outputBase, { withFileTypes: true }).filter(d => d.isDirectory());
      if (subdirs.length > 0) {
        const outDir = join(outputBase, subdirs[0].name);
        const hasResearch = existsSync(join(outDir, 'research')) && readdirSync(join(outDir, 'research')).length > 0;
        const hasChapters = existsSync(join(outDir, 'chapters')) && readdirSync(join(outDir, 'chapters')).length > 0;
        const hasTextbook = existsSync(join(outDir, 'textbook.md'));
        const hasGuides = existsSync(join(outDir, 'guides')) && readdirSync(join(outDir, 'guides')).length > 0;
        const hasSlides = existsSync(join(outDir, 'slides.md'));
        const hasPodcast = existsSync(join(outDir, 'podcast-prompt.md'));

        if (hasPodcast) {
          resumeFrom = null; // Fully complete
        } else if (hasSlides) {
          resumeFrom = 'podcast';
        } else if (hasGuides) {
          resumeFrom = 'slides';
        } else if (hasTextbook || hasChapters) {
          resumeFrom = 'guide';
        } else if (hasResearch) {
          resumeFrom = 'write';
        }

        if (resumeFrom) {
          log.info({ slug, resumeFrom, outDir }, 'Detected partial output — will resume');
        }
      }
    }

    let pipelineInstructions;
    if (resumeFrom) {
      const stageMap = {
        'write': '/sws:write — then let it auto-chain through diagrams → guide → slides → podcast',
        'guide': '/sws:guide — then let it auto-chain through slides → podcast',
        'slides': '/sws:slides — then let it auto-chain to podcast',
        'podcast': '/sws:podcast',
      };
      pipelineInstructions = `RESUME: This project was partially built. Chapters and earlier stages already exist.
Do NOT re-run /sws:start or /sws:scope or /sws:research. They are done.
Start from: ${stageMap[resumeFrom]}
Each stage spawns sub-agents for parallel work. Let them complete. Do NOT stop between stages.`;
    } else {
      pipelineInstructions = `Run /sws:start with topic "${topic}", level "${level}", chapters ${chapters}.

The pipeline auto-chains: start → scope → research → write → diagrams → guide → slides → podcast.
Each stage spawns sub-agents for parallel work. Let them complete. Do NOT stop between stages.`;
    }

    prompt = `Generate a complete learning package. NO human interaction — make all decisions autonomously.
Read CLAUDE.md in this directory for animation requirements — study guides MUST include inline SVG animations.
${sourceInstructions}
${pipelineInstructions}`;

  } else {
    // Standard app build
    let visionContext = '';
    try {
      const visionPath = join(dir, 'sdd-output', 'vision-document.md');
      visionContext = readFileSync(visionPath, 'utf-8');
    } catch { /* no vision doc */ }

    const tools = getDetectedTools();
    let toolNote = '';
    if (tools.tools.length > 0) {
      const artTools = tools.categories.art_generation || [];
      const deployTools = tools.categories.deployment || [];
      const lines = ['AVAILABLE MCP TOOLS — use these where the vision document instructs:'];
      if (artTools.length > 0) lines.push(`- Art generation: ${artTools.join(', ')} (mcp__<name>__* tool calls)`);
      if (deployTools.length > 0) lines.push(`- Deployment: ${deployTools.join(', ')}`);
      toolNote = lines.join('\n') + '\n\n';
    }

    prompt = `You are building a web app autonomously with NO human interaction. Read sdd-output/vision-document.md for the full spec. Do NOT ask any questions — make all decisions yourself based on the vision document and preferences. Build the complete app end-to-end.

${toolNote}Here is the vision document:

${visionContext}

Now run: /sdd:start --from architect`;
  }

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

    // Re-read project from DB to get current state
    const currentProject = projectGet(slug) || project;
    const currentType = currentProject.project_type || 'app';

    if (currentType === 'studyws') {
      // StudyWS completion: check for textbook.md in any output subdirectory
      let completed = false;
      try {
        const ex = existsSync;
        const outputDir = join(dir, 'output');
        if (ex(outputDir)) {
          const subdirs = readdirSync(outputDir, { withFileTypes: true }).filter(d => d.isDirectory());
          for (const sub of subdirs) {
            if (ex(join(outputDir, sub.name, 'textbook.md'))) {
              completed = true;
              break;
            }
          }
        }
        // Also check build log
        try {
          const buildLog = readFileSync(join(dir, 'build.log'), 'utf-8');
          if (buildLog.includes('pipeline') && buildLog.includes('complete')) completed = true;
        } catch {}
      } catch {}

      if (completed || code === 0) {
        // Find the output directory for the URL
        let outputPath = dir;
        try {
          const ex = existsSync;
          const outputDir = join(dir, 'output');
          if (ex(outputDir)) {
            const subdirs = readdirSync(outputDir, { withFileTypes: true }).filter(d => d.isDirectory());
            if (subdirs.length > 0) outputPath = join(outputDir, subdirs[0].name);
          }
        } catch {}

        projectUpdate(slug, {
          status: 'deployed-local',
          deployed_url: outputPath,
          completed_at: new Date().toISOString(),
          last_state_change: new Date().toISOString(),
          sdd_phase: 'complete',
          sdd_progress: 100,
        });
        log.info({ slug, outputPath }, 'StudyWS content generation complete');
      } else {
        log.warn({ slug, code }, 'StudyWS session exited with error');
      }

    } else {
      // Standard app completion check
      let completed = false;
      try {
        const statePath = join(dir, 'sdd-output', 'STATE.md');
        const stateContent = readFileSync(statePath, 'utf-8');
        if (stateContent.includes('Project Deployer') &&
            (stateContent.includes('[x] Project Deployer') ||
             stateContent.match(/completed_roles:.*Project Deployer/))) {
          completed = true;
        }
        const buildLog = readFileSync(join(dir, 'build.log'), 'utf-8');
        if (buildLog.includes('Workflow Complete') || buildLog.includes('workflow complete')) {
          completed = true;
        }
      } catch { /* can't read files */ }

      const portStart = currentProject.port_start;

      if (completed || code === 0) {
        const launched = launchApp(dir, portStart);
        const deployedUrl = launched ? launched.url : `http://localhost:${portStart}`;

        projectUpdate(slug, {
          status: 'deployed-local',
          deployed_url: deployedUrl,
          completed_at: new Date().toISOString(),
          last_state_change: new Date().toISOString(),
        });
        log.info({ slug, deployedUrl, strategy: launched?.strategy, completed }, 'Build finished and app launched');
      } else {
        log.warn({ slug, code }, 'Session exited with error');
      }
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
