import pino from 'pino';
import { projectsByStatus, projectUpdate } from './db.js';
import { spawnSession } from './spawner.js';

const log = pino({ name: 'nsaf.promotion' });

export function checkPromotions(claudeCommand) {
  const promoted = projectsByStatus('promoted');
  const launched = [];

  for (const project of promoted) {
    // Only promote if not already being deployed
    if (project.render_url) continue;

    log.info({ slug: project.slug }, 'Starting Render promotion');

    // Build a deployment-specific Claude command
    const deployPrompt = `Deploy this project to Render using the Render MCP tools. Follow the instructions in sdd-output/deploy-instruct.md. The project is at ${project.project_dir}.`;
    const command = claudeCommand.replace('{prompt}', deployPrompt);

    try {
      spawnSession(
        { ...project, status: 'promoted' },
        command
      );
      launched.push(project);
    } catch (err) {
      log.error({ slug: project.slug, error: err.message }, 'Failed to start promotion');
    }
  }

  return launched;
}
