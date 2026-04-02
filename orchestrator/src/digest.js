import pino from 'pino';
import { projectsActiveToday, projectsByStatus } from './db.js';

const log = pino({ name: 'nsaf.digest' });

export function compileDigest() {
  const today = projectsActiveToday();
  const completed = today.filter(p => ['deployed-local', 'reviewing', 'promoted'].includes(p.status));
  const stalled = today.filter(p => p.stall_alerted);
  const building = projectsByStatus('building');
  const queued = projectsByStatus('queued');

  return {
    date: new Date().toISOString().slice(0, 10),
    totalAttempted: today.length,
    completed: completed.map(p => ({
      slug: p.slug,
      status: p.status,
      url: p.deployed_url || p.render_url || '—',
    })),
    stalled: stalled.map(p => ({
      slug: p.slug,
      phase: p.sdd_phase,
      role: p.sdd_active_role,
    })),
    building: building.length,
    queued: queued.length,
  };
}

export function formatDigestHtml(digest) {
  const completedRows = digest.completed
    .map(p => `<tr><td>${p.slug}</td><td>${p.status}</td><td><a href="${p.url}">${p.url}</a></td></tr>`)
    .join('');

  const stalledRows = digest.stalled
    .map(p => `<tr><td>${p.slug}</td><td>${p.phase || '—'}</td><td>${p.role || '—'}</td></tr>`)
    .join('');

  return `
    <html>
    <body style="font-family:sans-serif;max-width:800px;margin:0 auto;padding:20px">
      <h1 style="color:#1a73e8">NSAF Evening Digest — ${digest.date}</h1>

      <h2>Summary</h2>
      <ul>
        <li>Total projects attempted: <strong>${digest.totalAttempted}</strong></li>
        <li>Completed: <strong>${digest.completed.length}</strong></li>
        <li>Stalled: <strong>${digest.stalled.length}</strong></li>
        <li>Still building: <strong>${digest.building}</strong></li>
        <li>Queued for tomorrow: <strong>${digest.queued}</strong></li>
      </ul>

      ${digest.completed.length > 0 ? `
      <h2 style="color:#28a745">Completed Builds</h2>
      <table style="width:100%;border-collapse:collapse">
        <tr style="background:#f5f5f5"><th style="padding:8px;text-align:left">Project</th><th style="padding:8px;text-align:left">Status</th><th style="padding:8px;text-align:left">URL</th></tr>
        ${completedRows}
      </table>` : ''}

      ${digest.stalled.length > 0 ? `
      <h2 style="color:#dc3545">Stalled Builds</h2>
      <table style="width:100%;border-collapse:collapse">
        <tr style="background:#f5f5f5"><th style="padding:8px;text-align:left">Project</th><th style="padding:8px;text-align:left">Phase</th><th style="padding:8px;text-align:left">Stuck At</th></tr>
        ${stalledRows}
      </table>` : ''}
    </body>
    </html>`;
}

export async function sendDigest(digest, resendApiKey, ownerEmail) {
  if (!resendApiKey || !ownerEmail) {
    log.warn('Digest skipped — missing RESEND_API_KEY or NSAF_OWNER_EMAIL');
    return false;
  }

  const html = formatDigestHtml(digest);

  try {
    const resp = await fetch('https://api.resend.com/emails', {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${resendApiKey}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        from: 'NSAF <nsaf@resend.dev>',
        to: [ownerEmail],
        subject: `NSAF Digest: ${digest.completed.length} built, ${digest.stalled.length} stalled — ${digest.date}`,
        html,
      }),
    });

    if (!resp.ok) {
      log.error({ status: resp.status }, 'Resend API error');
      return false;
    }

    log.info('Evening digest sent');
    return true;
  } catch (err) {
    log.error({ error: err.message }, 'Failed to send digest');
    return false;
  }
}
