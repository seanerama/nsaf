import { existsSync, readdirSync, statSync, readFileSync } from 'fs';
import { join } from 'path';
import { execSync } from 'child_process';
import pino from 'pino';
import { projectsByStatus, projectUpdate, projectGet } from './db.js';
import { notifyBriefCompletion } from './notify.js';

const log = pino({ name: 'nsaf.stall' });

// Locate a story's finished video: `<title-slug>-final.mp4` (new) or `final.mp4` (legacy).
// Prefer a title-named file. Returns the absolute path, or null if none exists.
function findFinalMp4(storyOut) {
  let files;
  try { files = readdirSync(storyOut); } catch { return null; }
  const matches = files.filter(f => f.endsWith('final.mp4'));
  if (matches.length === 0) return null;
  const titled = matches.find(f => f !== 'final.mp4');
  return join(storyOut, titled || 'final.mp4');
}

function isClaudeRunningForProject(projectDir) {
  try {
    const result = execSync(`pgrep -f "claude.*${projectDir}" 2>/dev/null`, { encoding: 'utf-8' });
    return result.trim().length > 0;
  } catch {
    return false;
  }
}

export function checkStalls(timeoutMinutes) {
  const building = projectsByStatus('building');
  const now = Date.now();
  const stalled = [];

  for (const project of building) {
    if (project.stall_alerted) continue;

    const projectType = project.project_type || 'app';

    // For StudyWS projects: check if claude process is still running
    // They don't have STATE.md so time-based stall detection doesn't work
    if (projectType === 'studyws') {
      const lastChange = project.started_at
        ? new Date(project.started_at).getTime()
        : now;
      const elapsed = (now - lastChange) / 1000 / 60;

      // Only flag if enough time has passed AND no claude process running
      if (elapsed >= timeoutMinutes && !isClaudeRunningForProject(project.project_dir)) {
        // Check if it actually completed (has textbook.md)
        const outputDir = join(project.project_dir, 'output');
        const hasOutput = existsSync(outputDir);

        if (hasOutput) {
          // Completed but wasn't caught — mark as deployed
          projectUpdate(project.slug, {
            status: 'deployed-local',
            sdd_phase: 'complete',
            sdd_progress: 100,
            completed_at: new Date().toISOString(),
          });
          log.info({ slug: project.slug }, 'StudyWS project completed (detected by stall checker)');
        } else {
          projectUpdate(project.slug, { stall_alerted: 1 });
          stalled.push(project);
          log.warn({ slug: project.slug, elapsedMinutes: Math.round(elapsed) }, 'StudyWS project stalled');
        }
      }
      continue;
    }

    // For Brief projects: same pattern — process-check + brief output existence.
    if (projectType === 'brief') {
      const lastChange = project.started_at
        ? new Date(project.started_at).getTime()
        : now;
      const elapsed = (now - lastChange) / 1000 / 60;

      if (elapsed >= timeoutMinutes && !isClaudeRunningForProject(project.project_dir)) {
        let runDir = null;
        try {
          const briefHome = process.env.NSAF_BRIEF_HOME;
          const cfg = JSON.parse(readFileSync(join(project.project_dir, 'brief-config.json'), 'utf-8'));
          const profile = cfg.profile || 'general';
          const startedMs = Date.parse(cfg.started_at || project.started_at || 0) || 0;
          const profileDir = briefHome ? join(briefHome, 'data', 'briefs', profile) : null;
          if (profileDir && existsSync(profileDir)) {
            const subdirs = readdirSync(profileDir, { withFileTypes: true })
              .filter(d => d.isDirectory())
              .map(d => ({ path: join(profileDir, d.name), mtime: statSync(join(profileDir, d.name)).mtimeMs }))
              .filter(s => s.mtime >= startedMs - 60_000)
              .sort((a, b) => b.mtime - a.mtime);
            for (const s of subdirs) {
              if (existsSync(join(s.path, 'brief.html')) && existsSync(join(s.path, 'summary.md'))) {
                runDir = s.path;
                break;
              }
            }
          }
        } catch { /* fall through to stalled */ }

        if (runDir) {
          projectUpdate(project.slug, {
            status: 'deployed-local',
            deployed_url: join(runDir, 'brief.html'),
            brief_run_dir: runDir,
            sdd_phase: 'complete',
            sdd_progress: 100,
            completed_at: new Date().toISOString(),
          });
          log.info({ slug: project.slug, runDir }, 'Brief project completed (detected by stall checker)');
          const finalProject = projectGet(project.slug) || project;
          notifyBriefCompletion(
            finalProject, runDir,
            process.env.WEBEX_BOT_TOKEN, process.env.WEBEX_OWNER_PERSON_ID,
          ).catch(err => log.warn({ slug: project.slug, error: err.message }, 'Brief Webex notify failed'));
        } else {
          projectUpdate(project.slug, { stall_alerted: 1 });
          stalled.push(project);
          log.warn({ slug: project.slug, elapsedMinutes: Math.round(elapsed) }, 'Brief project stalled');
        }
      }
      continue;
    }

    // For Story projects: same pattern — process-check + final.mp4 existence
    if (projectType === 'story') {
      const lastChange = project.started_at
        ? new Date(project.started_at).getTime()
        : now;
      const elapsed = (now - lastChange) / 1000 / 60;

      if (elapsed >= timeoutMinutes && !isClaudeRunningForProject(project.project_dir)) {
        const finalMp4 = findFinalMp4(join(project.project_dir, 'story-output'));
        if (finalMp4) {
          projectUpdate(project.slug, {
            status: 'deployed-local',
            deployed_url: finalMp4,
            sdd_phase: 'complete',
            sdd_progress: 100,
            completed_at: new Date().toISOString(),
          });
          log.info({ slug: project.slug, finalMp4 }, 'Story project completed (detected by stall checker)');
        } else {
          projectUpdate(project.slug, { stall_alerted: 1 });
          stalled.push(project);
          log.warn({ slug: project.slug, elapsedMinutes: Math.round(elapsed) }, 'Story project stalled');
        }
      }
      continue;
    }

    // Standard app stall detection
    const lastChange = project.last_state_change
      ? new Date(project.last_state_change).getTime()
      : project.started_at
        ? new Date(project.started_at).getTime()
        : now;

    const elapsed = (now - lastChange) / 1000 / 60;

    if (elapsed >= timeoutMinutes) {
      projectUpdate(project.slug, { stall_alerted: 1 });
      stalled.push(project);
      log.warn({
        slug: project.slug,
        phase: project.sdd_phase,
        role: project.sdd_active_role,
        elapsedMinutes: Math.round(elapsed),
      }, 'Project stalled');
    }
  }

  return stalled;
}
