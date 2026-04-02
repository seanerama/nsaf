import pino from 'pino';

const log = pino({ name: 'nsaf.notify' });

async function sendWebexMessage(text, botToken, personId) {
  if (!botToken || !personId) {
    log.warn('Webex notification skipped — missing WEBEX_BOT_TOKEN or WEBEX_OWNER_PERSON_ID');
    return false;
  }

  try {
    const resp = await fetch('https://webexapis.com/v1/messages', {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${botToken}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        toPersonId: personId,
        markdown: text,
      }),
    });

    if (!resp.ok) {
      log.error({ status: resp.status }, 'Webex API error');
      return false;
    }

    return true;
  } catch (err) {
    log.error({ error: err.message }, 'Failed to send Webex message');
    return false;
  }
}

export function notifyStall(project, botToken, personId) {
  const text =
    `**⚠️ Build Stalled: \`${project.slug}\`**\n\n` +
    `Phase: ${project.sdd_phase || 'unknown'}\n` +
    `Stuck at: ${project.sdd_active_role || 'unknown'}\n\n` +
    `Commands:\n` +
    `- \`restart ${project.slug}\` — re-queue the project\n` +
    `- \`skip ${project.slug}\` — scrap it`;

  return sendWebexMessage(text, botToken, personId);
}

export function notifyCompletion(project, botToken, personId) {
  const url = project.deployed_url || 'unknown';
  const text =
    `**✅ Build Complete: \`${project.slug}\`**\n\n` +
    `Local URL: ${url}\n\n` +
    `Commands:\n` +
    `- \`promote ${project.slug}\` — deploy to Render\n` +
    `- \`skip ${project.slug}\` — scrap it`;

  return sendWebexMessage(text, botToken, personId);
}

export function notifyPromotion(project, botToken, personId) {
  const text =
    `**🚀 Deployed to Render: \`${project.slug}\`**\n\n` +
    `Render URL: ${project.render_url || 'pending'}`;

  return sendWebexMessage(text, botToken, personId);
}
