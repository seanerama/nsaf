import { readFileSync } from 'fs';
import { join } from 'path';
import pino from 'pino';
import { projectUpdate } from './db.js';

const log = pino({ name: 'nsaf.completion' });

export function handleCompletion(project, portStart) {
  // Try to extract actual URL from build log or STATE.md
  let deployedUrl = `http://localhost:${portStart}`;
  try {
    const buildLog = readFileSync(join(project.project_dir, 'build.log'), 'utf-8');
    const urlMatch = buildLog.match(/http:\/\/localhost:(\d+)/);
    if (urlMatch) {
      deployedUrl = urlMatch[0];
    }
  } catch { /* use default */ }

  projectUpdate(project.slug, {
    status: 'deployed-local',
    deployed_url: deployedUrl,
    completed_at: new Date().toISOString(),
  });

  log.info({ slug: project.slug, url: deployedUrl }, 'Project completed and deployed locally');

  return { slug: project.slug, deployedUrl };
}
