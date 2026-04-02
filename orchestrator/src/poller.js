import { readFileSync, existsSync } from 'fs';
import { join } from 'path';
import pino from 'pino';
import { projectsByStatus, projectUpdate } from './db.js';

const log = pino({ name: 'nsaf.poller' });

export function pollAllProjects() {
  const building = projectsByStatus('building');

  for (const project of building) {
    try {
      pollProject(project);
    } catch (err) {
      log.error({ slug: project.slug, error: err.message }, 'Error polling project');
    }
  }

  return building.length;
}

export function pollProject(project) {
  const statePath = join(project.project_dir, 'sdd-output', 'STATE.md');

  if (!existsSync(statePath)) return;

  const content = readFileSync(statePath, 'utf-8');
  const state = parseStateMd(content);

  if (!state) return;

  const changed =
    state.phase !== project.sdd_phase ||
    state.activeRole !== project.sdd_active_role ||
    state.progress !== project.sdd_progress;

  if (changed) {
    const updates = {
      sdd_phase: state.phase,
      sdd_active_role: state.activeRole,
      sdd_progress: state.progress,
      last_state_change: new Date().toISOString(),
    };

    // Reset stall alert when progress is made
    if (project.stall_alerted) {
      updates.stall_alerted = 0;
    }

    projectUpdate(project.slug, updates);
    log.info({
      slug: project.slug,
      phase: state.phase,
      role: state.activeRole,
      progress: state.progress,
    }, 'Project state updated');
  }

  // Check if SDD pipeline is complete
  if (state.status === 'complete' || state.progress >= 100) {
    return { complete: true, project };
  }

  return { complete: false, project };
}

export function parseStateMd(content) {
  const result = {
    phase: null,
    activeRole: null,
    progress: 0,
    status: null,
  };

  // Parse YAML frontmatter
  const fmMatch = content.match(/^---\n([\s\S]*?)\n---/);
  if (fmMatch) {
    const fm = fmMatch[1];

    const phaseMatch = fm.match(/current_phase:\s*"?([^"\n]+)"?/);
    if (phaseMatch) result.phase = phaseMatch[1].trim();

    const statusMatch = fm.match(/status:\s*"?([^"\n]+)"?/);
    if (statusMatch) result.status = statusMatch[1].trim();

    const progressMatch = fm.match(/percent:\s*(\d+)/);
    if (progressMatch) result.progress = parseInt(progressMatch[1], 10);
  }

  // Parse active roles from markdown
  const activeSection = content.match(/## Active Roles\n([\s\S]*?)(?=\n##|$)/);
  if (activeSection) {
    const roleMatch = activeSection[1].match(/\*\*(.+?):\*\*/);
    if (roleMatch) result.activeRole = roleMatch[1].trim();
  }

  // Count completed roles for progress estimate
  const completed = (content.match(/- \[x\]/g) || []).length;
  const total = (content.match(/- \[[ x]\]/g) || []).length;
  if (total > 0 && result.progress === 0) {
    result.progress = Math.round((completed / total) * 100);
  }

  return result;
}
