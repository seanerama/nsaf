import pino from 'pino';
import { projectUpdate } from './db.js';

const log = pino({ name: 'nsaf.completion' });

export function handleCompletion(project, portStart) {
  const deployedUrl = `http://localhost:${portStart}`;

  projectUpdate(project.slug, {
    status: 'deployed-local',
    deployed_url: deployedUrl,
    completed_at: new Date().toISOString(),
  });

  log.info({ slug: project.slug, url: deployedUrl }, 'Project completed and deployed locally');

  return { slug: project.slug, deployedUrl };
}
