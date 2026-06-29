import { readFileSync, existsSync, statSync } from 'fs';
import { basename } from 'path';
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

// Per-attachment MIME guesses — Webex respects whatever we send.
const MIME_BY_EXT = {
  html: 'text/html',
  md: 'text/markdown',
  mp3: 'audio/mpeg',
  json: 'application/json',
  pdf: 'application/pdf',
  txt: 'text/plain',
};

function guessMime(filePath) {
  const ext = filePath.split('.').pop().toLowerCase();
  return MIME_BY_EXT[ext] || 'application/octet-stream';
}

// Send a Webex message with one local file attached (multipart upload).
// Webex /v1/messages accepts a single file per request via the `files` field.
async function sendWebexMessageWithFile(text, filePath, botToken, personId) {
  if (!botToken || !personId) {
    log.warn('Webex attachment skipped — missing token or personId');
    return false;
  }
  if (!existsSync(filePath)) {
    log.warn({ filePath }, 'Webex attachment skipped — file not found');
    return false;
  }
  try {
    const stats = statSync(filePath);
    if (stats.size > 100 * 1024 * 1024) {
      log.warn({ filePath, size: stats.size }, 'Webex attachment skipped — over 100MB cap');
      return false;
    }
    const buf = readFileSync(filePath);
    const form = new FormData();
    form.append('toPersonId', personId);
    form.append('markdown', text);
    form.append('files', new Blob([buf], { type: guessMime(filePath) }), basename(filePath));

    const resp = await fetch('https://webexapis.com/v1/messages', {
      method: 'POST',
      headers: { Authorization: `Bearer ${botToken}` },
      body: form,
    });
    if (!resp.ok) {
      const body = await resp.text().catch(() => '');
      log.error({ status: resp.status, body: body.slice(0, 300), filePath }, 'Webex attachment API error');
      return false;
    }
    return true;
  } catch (err) {
    log.error({ error: err.message, filePath }, 'Failed to send Webex attachment');
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

// Posts a headline message + one message per file (HTML, summary md, podcast mp3).
// podcast.mp3 is best-effort: silently skipped if missing. Returns true on best-effort
// success (headline sent + every present file uploaded).
export async function notifyBriefCompletion(project, runDir, botToken, personId) {
  const { join } = await import('path');
  const slug = project.slug;
  const profile = (slug.match(/^brief-(.+?)-\d{4}-\d{2}-\d{2}-\d{4}$/) || [])[1] || 'general';
  const briefHtml = join(runDir, 'brief.html');
  const summaryMd = join(runDir, 'summary.md');
  const podcastMp3 = join(runDir, 'podcast.mp3');
  const podcastScript = join(runDir, 'podcast-script.md');
  const hasAudio = existsSync(podcastMp3);

  // 1) Headline (no attachment)
  const audioNote = hasAudio
    ? '📎 HTML + Summary + Podcast MP3 to follow.'
    : '📎 HTML + Summary to follow. (NotebookLM audio not generated.)';
  const headline =
    `**📰 Brief ready: \`${slug}\`**\n\n` +
    `Profile: \`${profile}\`\n` +
    `Run dir: \`${runDir}\`\n\n` +
    audioNote;
  const ok1 = await sendWebexMessage(headline, botToken, personId);

  // 2) brief.html
  const ok2 = await sendWebexMessageWithFile(
    `Interactive HTML brief:`, briefHtml, botToken, personId
  );

  // 3) summary.md
  const ok3 = await sendWebexMessageWithFile(
    `Markdown summary:`, summaryMd, botToken, personId
  );

  // 4) podcast.mp3 (best-effort) — if missing, attach the script as a fallback so
  //    the user can still hand it to NotebookLM (or any TTS) manually.
  let ok4;
  if (hasAudio) {
    ok4 = await sendWebexMessageWithFile(
      `Podcast (5–7 min, NotebookLM):`, podcastMp3, botToken, personId
    );
  } else if (existsSync(podcastScript)) {
    ok4 = await sendWebexMessageWithFile(
      `Podcast script (audio not generated — feed this to NotebookLM manually):`,
      podcastScript, botToken, personId
    );
  } else {
    ok4 = true; // nothing to send is not a failure
  }

  return ok1 && ok2 && ok3 && ok4;
}
