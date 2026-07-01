#!/usr/bin/env node
'use strict';

/**
 * make-print-pdf.cjs — assemble the story's scene images + narration into
 * a print-ready PDF suitable for a print shop.
 *
 * Usage:
 *   node make-print-pdf.cjs [--cwd <story-project-dir>] [--out <pdf-path>]
 *
 * Reads (from cwd, or --cwd):
 *   story-output/script.md      per-scene narration text
 *   story-output/outline.md     title (and any additional metadata)
 *   story-output/concept.md     backup title/author source
 *   story-output/images/scene-NN.png  scene illustrations
 *
 * Writes:
 *   story-output/print-book.html  (kept for debugging / reprinting)
 *   <out>  (default: story-output/<title-slug>-book.pdf)
 *
 * Design:
 *   - Trim size 8.5" × 8.5" landscape square (chosen by user, matches most
 *     children's picture-book trim sizes and fits 16:9 scene images with
 *     minimal cropping).
 *   - Front cover: title + subtitle + hero image (scene-01 as fallback).
 *   - Each scene: single page with the illustration in the top ~56%
 *     (aspect-preserved, full-width) and narration text in a cream text
 *     zone in the bottom ~44%. Real vector typography — no AI-rendered
 *     text, no misspelling risk.
 *   - Back cover: credits.
 *
 * PDF generation:
 *   Uses headless Chrome / Chromium first (any of: google-chrome, chromium,
 *   chromium-browser). Falls back to wkhtmltopdf if none is available.
 *
 * Note on print DPI:
 *   Scene images are 1920×1080 (~226 DPI at 8.5" wide) — acceptable for
 *   home / small-run print, marginally below the 300 DPI "true print" bar.
 *   For studio-quality print, regenerate at 2550×2550 in a future story.
 */

const fs = require('fs');
const path = require('path');
const { execSync, spawnSync } = require('child_process');

// ─── args ────────────────────────────────────────────────────────────────────

let cwd = process.cwd();
let outPath = null;
const rawArgs = process.argv.slice(2);
for (let i = 0; i < rawArgs.length; i++) {
  if (rawArgs[i] === '--cwd' && rawArgs[i + 1]) { cwd = rawArgs[++i]; continue; }
  if (rawArgs[i] === '--out' && rawArgs[i + 1]) { outPath = rawArgs[++i]; continue; }
}

const outDir = path.join(cwd, 'story-output');
if (!fs.existsSync(outDir)) {
  console.error(`no story-output/ at ${cwd}`);
  process.exit(2);
}

// ─── helpers ─────────────────────────────────────────────────────────────────

function readIfExists(p) {
  return fs.existsSync(p) ? fs.readFileSync(p, 'utf8') : null;
}

function slugify(s) {
  return String(s || 'story')
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '') || 'story';
}

function escapeHtml(s) {
  return String(s || '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

// Extract narration text from a script.md scene block.
// - Strip `[VOICE:x]` tags.
// - Keep dialogue quotes intact.
// - Collapse runs of blank lines to a single blank between paragraphs.
function extractSceneText(sceneBlock) {
  const withoutTags = sceneBlock
    .replace(/\[VOICE:[^\]]+\]/g, '')
    .replace(/^### Illustration Prompt[\s\S]*$/m, '')  // drop everything from Illustration Prompt onward
    .replace(/^### Narration\s*/m, '')                  // drop the Narration heading
    .replace(/^## Scene \d+:.*$/m, '');                 // drop the Scene heading
  // Split into paragraphs on 2+ newlines, trim each, drop empties.
  return withoutTags
    .split(/\n\s*\n/)
    .map(p => p.trim())
    .filter(Boolean);
}

// Parse script.md into { sceneNumber, title, paragraphs[] }[].
function parseScript(scriptMd) {
  if (!scriptMd) return [];
  // Split on `## Scene N: ...` markers, capture the heading.
  const parts = scriptMd.split(/(?=^## Scene \d+:)/m);
  const scenes = [];
  for (const part of parts) {
    const m = part.match(/^## Scene (\d+):\s*(.*)$/m);
    if (!m) continue;
    scenes.push({
      sceneNumber: parseInt(m[1], 10),
      title: m[2].trim(),
      paragraphs: extractSceneText(part),
    });
  }
  return scenes.sort((a, b) => a.sceneNumber - b.sceneNumber);
}

// Pull "Title:" from the outline/concept frontmatter or a top-level heading.
function parseTitle(outlineMd, conceptMd) {
  for (const src of [outlineMd, conceptMd]) {
    if (!src) continue;
    let m = src.match(/^title:\s*(.+)$/im);
    if (m) return m[1].trim().replace(/^"|"$/g, '');
    m = src.match(/^# Story Outline:\s*(.+)$/m) || src.match(/^# Story Concept:\s*(.+)$/m) || src.match(/^# (.+)$/m);
    if (m) return m[1].trim();
  }
  return 'Story';
}

function parseSubtitle(conceptMd) {
  if (!conceptMd) return '';
  const m = conceptMd.match(/^subtitle:\s*(.+)$/im);
  return m ? m[1].trim().replace(/^"|"$/g, '') : '';
}

// ─── read inputs ─────────────────────────────────────────────────────────────

const scriptMd  = readIfExists(path.join(outDir, 'script.md'));
const outlineMd = readIfExists(path.join(outDir, 'outline.md'));
const conceptMd = readIfExists(path.join(outDir, 'concept.md'));

if (!scriptMd)  { console.error('missing story-output/script.md'); process.exit(3); }

const title    = parseTitle(outlineMd, conceptMd);
const subtitle = parseSubtitle(conceptMd);
const scenes   = parseScript(scriptMd);

if (scenes.length === 0) {
  console.error('no scenes parsed from script.md');
  process.exit(3);
}

// Map each scene to its image path (absolute, so headless Chrome can load it).
const imagesDir = path.join(outDir, 'images');
for (const s of scenes) {
  const nn = String(s.sceneNumber).padStart(2, '0');
  const p = path.join(imagesDir, `scene-${nn}.png`);
  s.imagePath = fs.existsSync(p) ? p : null;
  if (!s.imagePath) console.error(`WARN: missing image ${p}`);
}

// Hero image for the cover = scene 1's image, or the first image we can find.
const heroImage = scenes.find(s => s.imagePath)?.imagePath || null;

// ─── build HTML ──────────────────────────────────────────────────────────────

function fileUrl(p) {
  return 'file://' + p.replace(/ /g, '%20');
}

function sceneParagraphsHtml(paragraphs) {
  return paragraphs
    .map(p => `<p>${escapeHtml(p).replace(/\n/g, '<br/>')}</p>`)
    .join('\n');
}

const coverHtml = `
<div class="page cover">
  ${heroImage ? `<img class="cover-image" src="${fileUrl(heroImage)}" alt=""/>` : ''}
  <h1>${escapeHtml(title)}</h1>
  ${subtitle ? `<div class="cover-subtitle">${escapeHtml(subtitle)}</div>` : ''}
</div>`;

const sceneHtmls = scenes.map(s => `
<div class="page scene">
  <div class="scene-image" ${s.imagePath ? `style="background-image: url('${fileUrl(s.imagePath)}');"` : ''}></div>
  <div class="scene-text">
    ${sceneParagraphsHtml(s.paragraphs)}
  </div>
</div>`).join('\n');

const backHtml = `
<div class="page back">
  <div class="back-inner">
    <div class="back-title">${escapeHtml(title)}</div>
    <div class="back-note">Created with Story Maker (nsaf/skills/story).</div>
  </div>
</div>`;

const css = `
@page {
  size: 8.5in 8.5in;
  margin: 0;
}
* { box-sizing: border-box; }
html, body {
  margin: 0;
  padding: 0;
  font-family: 'Charter', 'Georgia', Cambria, 'Times New Roman', serif;
  color: #2a2320;
  background: #fff;
  -webkit-print-color-adjust: exact;
  print-color-adjust: exact;
}
.page {
  width: 8.5in;
  height: 8.5in;
  page-break-after: always;
  position: relative;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}
.page:last-of-type { page-break-after: auto; }

/* Cover */
.cover {
  background: linear-gradient(180deg, #f6ecd6 0%, #e6cf9f 100%);
  align-items: center;
  justify-content: center;
  text-align: center;
  padding: 0.6in 0.6in;
}
.cover .cover-image {
  max-width: 6in;
  max-height: 4.5in;
  border-radius: 0.12in;
  box-shadow: 0 0.12in 0.25in rgba(70, 40, 10, 0.25);
  margin-bottom: 0.45in;
  object-fit: cover;
}
.cover h1 {
  font-family: 'Charter', 'Georgia', serif;
  font-size: 44pt;
  font-weight: 700;
  line-height: 1.05;
  margin: 0;
  color: #3a2814;
  text-shadow: 0 1px 0 rgba(255,255,255,0.4);
}
.cover .cover-subtitle {
  margin-top: 0.3in;
  font-size: 15pt;
  color: #6b5030;
  font-style: italic;
}

/* Scene */
.scene .scene-image {
  width: 8.5in;
  height: 4.78in;              /* 8.5 × 9/16 = fit-to-width for 16:9 source */
  background-color: #fff;
  background-size: cover;
  background-position: center;
  background-repeat: no-repeat;
  border-bottom: 0.02in solid #d9c8a5;
}
.scene .scene-text {
  flex: 1 1 auto;
  padding: 0.32in 0.55in 0.4in;
  background: linear-gradient(180deg, #fbf4e4 0%, #f6ecd4 100%);
  font-size: 16.5pt;
  line-height: 1.48;
  display: flex;
  flex-direction: column;
  justify-content: center;
}
.scene .scene-text p {
  margin: 0 0 0.14in 0;
}
.scene .scene-text p:last-child { margin-bottom: 0; }

/* Back */
.back {
  background: #f6ecd6;
  align-items: center;
  justify-content: center;
  text-align: center;
}
.back .back-inner {
  padding: 1in;
}
.back .back-title {
  font-size: 24pt;
  font-weight: 700;
  margin-bottom: 0.3in;
  color: #3a2814;
}
.back .back-note {
  font-size: 11pt;
  color: #6b5030;
  font-style: italic;
}
`;

const html = `<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8"/>
<title>${escapeHtml(title)}</title>
<style>${css}</style>
</head>
<body>
${coverHtml}
${sceneHtmls}
${backHtml}
</body>
</html>`;

const htmlPath = path.join(outDir, 'print-book.html');
fs.writeFileSync(htmlPath, html, 'utf8');
console.log(`wrote ${htmlPath}`);

// ─── render to PDF ───────────────────────────────────────────────────────────

const slug = slugify(title);
if (!outPath) outPath = path.join(outDir, `${slug}-book.pdf`);

function which(cmd) {
  try {
    return execSync(`command -v ${cmd}`, { stdio: ['ignore', 'pipe', 'ignore'] }).toString().trim();
  } catch { return null; }
}

// Discover a headless-Chrome executable in this order:
//   1. Explicit env vars: PUPPETEER_EXECUTABLE_PATH, CHROME_PATH
//   2. Standard PATH candidates (google-chrome, chromium, ...)
//   3. Playwright's bundled Chromium cache (~/.cache/ms-playwright/chromium*/chrome-linux/chrome)
//   4. Puppeteer's bundled Chrome cache (~/.cache/puppeteer/chrome/*/chrome-linux*/chrome)
//
// The old detection only checked (2). When the server had Playwright installed
// (for other projects) with a bundled Chromium at ~/.cache/ms-playwright/
// chromium-1194/chrome-linux/chrome, the PDF stage reported "no PDF renderer"
// even though a headless browser was available. See STORY-MAKER-ISSUES.md #9.
function findChromeBin() {
  // 1. Explicit env-var overrides.
  for (const envVar of ['PUPPETEER_EXECUTABLE_PATH', 'CHROME_PATH']) {
    const p = process.env[envVar];
    if (p && fs.existsSync(p)) {
      try {
        // Must be executable (or at least a regular file).
        const st = fs.statSync(p);
        if (st.isFile()) return p;
      } catch {}
    }
  }

  // 2. Standard PATH candidates.
  const standard = [
    'google-chrome',
    'google-chrome-stable',
    'chromium',
    'chromium-browser',
  ];
  for (const c of standard) {
    const p = which(c);
    if (p) return p;
  }

  // 3 & 4. Bundled browser caches. Use fs to glob for the newest matching
  // directory rather than shelling out to `find` (which is slow for big caches
  // and adds a shell dep).
  const home = process.env.HOME || '';
  const bundleRoots = [
    // Playwright
    { root: path.join(home, '.cache/ms-playwright'), prefix: 'chromium', tail: 'chrome-linux/chrome' },
    { root: path.join(home, '.cache/ms-playwright'), prefix: 'chromium', tail: 'chrome-linux/headless_shell' },
    // Puppeteer
    { root: path.join(home, '.cache/puppeteer/chrome'), prefix: '', tail: 'chrome-linux/chrome' },
    { root: path.join(home, '.cache/puppeteer/chrome'), prefix: '', tail: 'chrome-linux64/chrome' },
  ];
  for (const b of bundleRoots) {
    if (!fs.existsSync(b.root)) continue;
    let entries;
    try { entries = fs.readdirSync(b.root); } catch { continue; }
    // Filter by prefix and sort descending so the newest bundle wins
    // (bundles are versioned, e.g. chromium-1194).
    const matches = entries
      .filter(e => e.startsWith(b.prefix))
      .sort()
      .reverse();
    for (const dir of matches) {
      const candidate = path.join(b.root, dir, b.tail);
      if (fs.existsSync(candidate)) {
        try {
          if (fs.statSync(candidate).isFile()) return candidate;
        } catch {}
      }
    }
  }

  return null;
}

const chromeBin = findChromeBin();

let ok = false;
if (chromeBin) {
  console.log(`rendering via ${chromeBin}`);
  const args = [
    '--headless=new',
    '--disable-gpu',
    '--no-sandbox',
    // Bundled Playwright/Puppeteer chromiums need this to run without a real
    // /dev/shm (common on headless servers); mainline google-chrome ignores it.
    '--disable-dev-shm-usage',
    '--no-pdf-header-footer',
    '--virtual-time-budget=10000',
    `--print-to-pdf=${outPath}`,
    fileUrl(htmlPath),
  ];
  const r = spawnSync(chromeBin, args, { stdio: 'inherit' });
  ok = r.status === 0 && fs.existsSync(outPath) && fs.statSync(outPath).size > 0;
} else {
  const wk = which('wkhtmltopdf');
  if (wk) {
    console.log(`rendering via wkhtmltopdf`);
    const r = spawnSync(wk, [
      '--page-width', '8.5in',
      '--page-height', '8.5in',
      '--margin-top', '0',
      '--margin-bottom', '0',
      '--margin-left', '0',
      '--margin-right', '0',
      '--enable-local-file-access',
      htmlPath,
      outPath,
    ], { stdio: 'inherit' });
    ok = r.status === 0 && fs.existsSync(outPath) && fs.statSync(outPath).size > 0;
  } else {
    console.error(
      'no PDF renderer found. Checked:\n' +
      '  - PUPPETEER_EXECUTABLE_PATH / CHROME_PATH env vars\n' +
      '  - PATH: google-chrome, google-chrome-stable, chromium, chromium-browser\n' +
      '  - ~/.cache/ms-playwright/chromium*/chrome-linux/chrome (Playwright bundled)\n' +
      '  - ~/.cache/puppeteer/chrome/*/chrome-linux*/chrome (Puppeteer bundled)\n' +
      '  - PATH: wkhtmltopdf\n' +
      'Install one, or export PUPPETEER_EXECUTABLE_PATH pointing at a Chrome binary.'
    );
    process.exit(4);
  }
}

if (!ok) {
  console.error(`PDF render failed; output at ${outPath} is missing or empty`);
  process.exit(5);
}

console.log(`wrote ${outPath} (${(fs.statSync(outPath).size / 1024).toFixed(1)} KB)`);
