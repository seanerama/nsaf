import { existsSync } from 'fs';
import { join } from 'path';
import { execSync } from 'child_process';
import pino from 'pino';
import { projectsByStatus, projectUpdate } from './db.js';

const log = pino({ name: 'nsaf.stall' });

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

    // For Story projects: same pattern — process-check + final.mp4 existence
    if (projectType === 'story') {
      const lastChange = project.started_at
        ? new Date(project.started_at).getTime()
        : now;
      const elapsed = (now - lastChange) / 1000 / 60;

      if (elapsed >= timeoutMinutes && !isClaudeRunningForProject(project.project_dir)) {
        const finalMp4 = join(project.project_dir, 'story-output', 'final.mp4');
        if (existsSync(finalMp4)) {
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
