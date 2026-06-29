import { spawn } from 'child_process';
import { createWriteStream, readFileSync, writeFileSync, existsSync, readdirSync, statSync } from 'fs';
import { join } from 'path';
import pino from 'pino';
import { projectUpdate, projectGet } from './db.js';
import { launchApp } from './app-launcher.js';
import { notifyBriefCompletion } from './notify.js';

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

// Locate a story's finished video. New builds name it `<title-slug>-final.mp4`;
// older builds used a bare `final.mp4`. Prefer a title-named file, falling back to
// the legacy name. Returns the absolute path, or null if none exists.
function findFinalMp4(storyOut) {
  let files;
  try { files = readdirSync(storyOut); } catch { return null; }
  const matches = files.filter(f => f.endsWith('final.mp4'));
  if (matches.length === 0) return null;
  const titled = matches.find(f => f !== 'final.mp4');
  return join(storyOut, titled || 'final.mp4');
}

// Find the brief run dir produced after a /brief:run started at `startedAt`.
// Returns the directory path if brief.html and summary.md exist, else null.
// `podcast.mp3` is best-effort and NOT required for completion (per plan §Risks).
function findCompletedBrief(briefHome, profile, startedAt) {
  const profileDir = join(briefHome, 'data', 'briefs', profile);
  if (!existsSync(profileDir)) return null;
  const startedMs = Date.parse(startedAt) || 0;
  const slack = 60_000; // allow 1 min skew between Webex-side stamp and FS mtime
  let candidates;
  try {
    candidates = readdirSync(profileDir, { withFileTypes: true })
      .filter(d => d.isDirectory())
      .map(d => {
        const p = join(profileDir, d.name);
        let mtime = 0;
        try { mtime = statSync(p).mtimeMs; } catch {}
        return { path: p, mtime };
      })
      .filter(c => c.mtime >= startedMs - slack)
      .sort((a, b) => b.mtime - a.mtime);
  } catch { return null; }
  for (const c of candidates) {
    if (existsSync(join(c.path, 'brief.html')) && existsSync(join(c.path, 'summary.md'))) {
      return c.path;
    }
  }
  return null;
}

const activeSessions = new Map();

export function getActiveSessions() {
  return activeSessions;
}

export function spawnSession(project, claudeCommandTemplate) {
  const slug = project.slug;
  const dir = project.project_dir;

  const projectType = project.project_type || 'app';
  let prompt;
  // Most project types spawn in their own project dir. `brief` is an exception —
  // it spawns in $NSAF_BRIEF_HOME so the Daily-Brief slash commands and shared
  // `data/` (profiles, history, briefs) are visible to Claude.
  let cwd = dir;

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
    const hasSourceFile = config.has_source_file || false;

    let sourceInstructions = '';
    // Check for local source material file (from Webex attachment)
    const sourceMdPath = join(dir, 'source-material.md');
    const sourcePdfPath = join(dir, 'source-material.pdf');
    if (existsSync(sourceMdPath)) {
      const sourceContent = readFileSync(sourceMdPath, 'utf-8');
      sourceInstructions = `
IMPORTANT — Source Material:
The following document was provided as the primary source for this study material.
Use it as the primary source for structuring the chapters and content.
The topic name and chapter outline should be derived from this document's content.
Use its structure to inform the /sws:start topic and /sws:scope outline.

--- BEGIN SOURCE MATERIAL ---
${sourceContent}
--- END SOURCE MATERIAL ---
`;
      log.info({ slug, bytes: sourceContent.length }, 'Injected source-material.md into prompt');
    } else if (existsSync(sourcePdfPath)) {
      sourceInstructions = `
IMPORTANT — Source Material:
A PDF source document has been saved at: ${sourcePdfPath}
Read this PDF file and use it as the primary source for structuring the chapters and content.
The topic name and chapter outline should be derived from this document's content.
Use its structure to inform the /sws:start topic and /sws:scope outline.
`;
      log.info({ slug }, 'Referenced source-material.pdf in prompt');
    } else if (sourceUrl) {
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

  } else if (projectType === 'story') {
    // Illustrated audio story pipeline
    let storyConfig = {};
    try {
      storyConfig = JSON.parse(readFileSync(join(dir, 'story-config.json'), 'utf-8'));
    } catch { /* no config */ }

    const idea = storyConfig.idea || project.slug;
    const style = storyConfig.style || '';
    const scenes = storyConfig.scenes || '';
    const notes = storyConfig.notes || '';

    // Detect partial output to resume
    const storyOut = join(dir, 'story-output');
    const hasFinal = findFinalMp4(storyOut) !== null;
    const hasConcept = existsSync(join(storyOut, 'concept.md'));
    const hasOutline = existsSync(join(storyOut, 'outline.md'));
    const hasScript = existsSync(join(storyOut, 'script.md'));
    const hasImages = existsSync(join(storyOut, 'images')) &&
      readdirSync(join(storyOut, 'images')).some(f => f.endsWith('.png'));
    const hasAudio = existsSync(join(storyOut, 'audio')) &&
      readdirSync(join(storyOut, 'audio')).some(f => f.endsWith('.mp3'));

    // Detect a fix request (from storyfix Webex command)
    const fixRequestPath = join(storyOut, 'fix-request.md');
    const hasFixRequest = existsSync(fixRequestPath);

    let pipelineInstructions;
    if (hasFixRequest) {
      const fixContent = readFileSync(fixRequestPath, 'utf-8');
      log.info({ slug }, 'Detected fix-request — entering fix mode');
      pipelineInstructions = `FIX MODE — targeted scene regeneration.
Read story-output/fix-request.md for the scene number and correction instruction.
Do NOT re-run /story:start, /story:outline, /story:write, or /story:narrate.

Process:
1. Read the fix-request file. It names a scene number and a correction instruction.
2. Read the original \`### Illustration Prompt\` for that scene from story-output/script.md.
3. Build a refined prompt = original prompt + a clear appended "IMPORTANT CORRECTION: ..." sentence from the instruction.
4. From the project directory, call:
   \`\`\`bash
   rm -rf nanobanana-output
   gemini --yolo -p "/generate '<refined prompt>' --aspect=16:9"
   mv nanobanana-output/*.png story-output/images/scene-<N>.png
   rm -rf nanobanana-output
   \`\`\`
5. Run /story:build to rebuild the final MP4 (story-output/<title>-final.mp4) with the corrected image.
6. Delete story-output/fix-request.md on success.

Fix-request contents for reference:
---
${fixContent}
---`;
    } else if (hasFinal) {
      pipelineInstructions = `This story is already complete — the final MP4 exists. Exit immediately.`;
    } else if (hasConcept || hasOutline || hasScript || hasImages || hasAudio) {
      log.info({ slug, hasConcept, hasOutline, hasScript, hasImages, hasAudio }, 'Detected partial story — will resume');
      pipelineInstructions = `RESUME: This story was partially built. Run /story:next to pick up where it left off.
Do NOT re-run earlier stages that are already complete. Complete the pipeline end-to-end to produce the final MP4 in story-output/.
Do NOT stop between stages — each stage must invoke the next automatically.`;
    } else {
      const styleHint = style ? `\nPreferred art style: ${style}` : '';
      const scenesHint = scenes ? `\nTarget scene count: ${scenes}` : '';
      const notesHint = notes ? `\nAdditional notes: ${notes}` : '';
      pipelineInstructions = `Run /story:start ${JSON.stringify(idea)}${styleHint}${scenesHint}${notesHint}

The pipeline auto-chains: start → outline → write → illustrate → narrate → build.
Each stage completes and invokes the next. Do NOT stop between stages.
Produce the final MP4 in story-output/ (the build stage names it <title>-final.mp4).`;
    }

    prompt = `Generate an illustrated audio story autonomously with NO human interaction.
Do NOT ask any questions — make all creative decisions yourself.
${pipelineInstructions}`;

  } else if (projectType === 'brief') {
    // Daily-Brief news catch-up pipeline — runs inside a shared Daily-Brief install.
    const briefHome = process.env.NSAF_BRIEF_HOME;
    if (!briefHome || !existsSync(briefHome)) {
      log.error({ slug, briefHome }, 'NSAF_BRIEF_HOME not set or directory missing — cannot spawn brief');
      projectUpdate(slug, {
        status: 'failed',
        last_state_change: new Date().toISOString(),
      });
      return null;
    }
    let briefCfg = {};
    try {
      briefCfg = JSON.parse(readFileSync(join(dir, 'brief-config.json'), 'utf-8'));
    } catch (err) {
      log.error({ slug, error: err.message }, 'brief-config.json missing or invalid');
      projectUpdate(slug, { status: 'failed', last_state_change: new Date().toISOString() });
      return null;
    }
    const profile = briefCfg.profile || 'general';
    const mode = briefCfg.mode || 'run';
    const invocation = mode === 'topic'
      ? `/brief:topic "${(briefCfg.topic || '').replace(/"/g, '\\"')}" ${profile}`
      : `/brief:run ${profile}`;

    prompt = `Generate a daily brief autonomously with NO human interaction.
Do NOT ask any questions — proceed with defaults for everything.

Step 1: ${invocation}

Step 2: After the brief completes successfully, locate the newest dated
directory under data/briefs/${profile}/ — call it RUN_DIR. It contains
brief.html, summary.md, podcast-script.md, run.json.

Step 3: Use the notebooklm skill to generate a 5-7 minute two-host
explainer podcast from RUN_DIR/summary.md. Tone: warm and conversational;
assume the listener is busy. Save the resulting MP3 as RUN_DIR/podcast.mp3.
If NotebookLM fails for any reason, log the failure and continue — audio
is best-effort; brief.html and summary.md are the primary deliverables.

Step 4: Verify brief.html and summary.md exist in RUN_DIR (podcast.mp3
is optional). Print the RUN_DIR path. Then exit.`;

    cwd = briefHome;

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
  log.info({ slug, command, cwd }, 'Spawning Claude Code session');

  const logPath = join(dir, 'build.log');
  const logStream = createWriteStream(logPath, { flags: 'a' });

  // Strip API keys so Claude Code uses the subscription, not the API.
  // Exception: story projects need OPENAI_API_KEY (TTS narration) and
  // GEMINI_API_KEY/NANOBANANA_API_KEY (Nano Banana image generation).
  //
  // Also strip infrastructure secrets that no project session should ever
  // see — the bot/digest/webhook is the only legitimate consumer of these,
  // and a leak into a build log or a prompt-injected sub-agent would be
  // a real-world incident.
  const cleanEnv = { ...process.env };
  delete cleanEnv.ANTHROPIC_API_KEY;
  delete cleanEnv.WEBEX_BOT_TOKEN;
  delete cleanEnv.WEBEX_WEBHOOK_SECRET;
  delete cleanEnv.WEBEX_OWNER_PERSON_ID;
  delete cleanEnv.RESEND_API_KEY;
  delete cleanEnv.NGROK_AUTHTOKEN;
  // Brief sessions may need Google/OpenAI keys for NotebookLM audio generation.
  if (projectType !== 'story' && projectType !== 'brief') {
    delete cleanEnv.OPENAI_API_KEY;
    delete cleanEnv.GOOGLE_API_KEY;
    delete cleanEnv.GEMINI_API_KEY;
    delete cleanEnv.NANOBANANA_API_KEY;
  }

  // For brief sessions, put $NSAF_BRIEF_HOME/.venv/bin first on PATH so
  // Claude can find the `notebooklm` CLI installed in the Daily-Brief venv.
  if (projectType === 'brief' && process.env.NSAF_BRIEF_HOME) {
    const venvBin = join(process.env.NSAF_BRIEF_HOME, '.venv', 'bin');
    cleanEnv.PATH = `${venvBin}:${cleanEnv.PATH || ''}`;
  }

  const child = spawn(bin, args, {
    cwd,
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

    } else if (currentType === 'story') {
      // Story completion: a *final.mp4 in story-output/ (<title>-final.mp4 or legacy final.mp4)
      const finalMp4 = findFinalMp4(join(dir, 'story-output'));
      const completed = finalMp4 !== null;

      if (completed) {
        projectUpdate(slug, {
          status: 'deployed-local',
          deployed_url: finalMp4,
          completed_at: new Date().toISOString(),
          last_state_change: new Date().toISOString(),
          sdd_phase: 'complete',
          sdd_progress: 100,
        });
        log.info({ slug, finalMp4 }, 'Story pipeline complete');
      } else {
        log.warn({ slug, code }, 'Story session exited without producing final.mp4');
      }

    } else if (currentType === 'brief') {
      // Brief completion: a dated subdir under $NSAF_BRIEF_HOME/data/briefs/<profile>/
      // with brief.html + summary.md (podcast.mp3 is best-effort).
      const briefHome = process.env.NSAF_BRIEF_HOME;
      let runDir = null;
      try {
        const briefCfg = JSON.parse(readFileSync(join(dir, 'brief-config.json'), 'utf-8'));
        const profile = briefCfg.profile || 'general';
        const startedAt = briefCfg.started_at || project.started_at || new Date().toISOString();
        if (briefHome) {
          runDir = findCompletedBrief(briefHome, profile, startedAt);
        }
      } catch (err) {
        log.warn({ slug, error: err.message }, 'Could not read brief-config.json on completion');
      }

      if (runDir) {
        const hasAudio = existsSync(join(runDir, 'podcast.mp3'));
        projectUpdate(slug, {
          status: 'deployed-local',
          deployed_url: join(runDir, 'brief.html'),
          brief_run_dir: runDir,
          completed_at: new Date().toISOString(),
          last_state_change: new Date().toISOString(),
          sdd_phase: 'complete',
          sdd_progress: 100,
        });
        log.info({ slug, runDir, hasAudio }, 'Brief pipeline complete');
        // Fire-and-forget Webex notification with attachments.
        const finalProject = projectGet(slug) || project;
        notifyBriefCompletion(
          finalProject, runDir,
          process.env.WEBEX_BOT_TOKEN, process.env.WEBEX_OWNER_PERSON_ID,
        ).catch(err => log.warn({ slug, error: err.message }, 'Brief Webex notify failed'));
      } else {
        log.warn({ slug, code }, 'Brief session exited without producing brief.html + summary.md');
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
