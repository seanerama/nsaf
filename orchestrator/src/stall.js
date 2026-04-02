import pino from 'pino';
import { projectsByStatus, projectUpdate } from './db.js';

const log = pino({ name: 'nsaf.stall' });

export function checkStalls(timeoutMinutes) {
  const building = projectsByStatus('building');
  const now = Date.now();
  const stalled = [];

  for (const project of building) {
    if (project.stall_alerted) continue;

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
