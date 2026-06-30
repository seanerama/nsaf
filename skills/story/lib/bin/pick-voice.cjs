#!/usr/bin/env node
'use strict';

/**
 * pick-voice — deterministic voice picker keyed off character attributes.
 *
 * Usage:
 *   node pick-voice.cjs <provider> <age> <gender> <accent> [voice_hint]
 *
 * <provider>   openai | elevenlabs
 * <age>        integer years (e.g. 7) | child | teen | young-adult | adult | elder | "-"
 * <gender>     male | female | nonbinary | "-"
 * <accent>     short label (neutral-us, british-rp, southern-us, irish, ...) | "-"
 * [voice_hint] optional short prose hint ("calm grandfather", "energetic curious")
 *
 * Output (stdout, single line):
 *   <voice_id>
 *
 * Exit non-zero if no plausible voice exists for the inputs (caller should
 * surface a clear error rather than fall back to nondeterministic vibes).
 *
 * The mapping table below is the entire voice-selection policy. It's intentional
 * that this is mechanical — the research showed the LLM-picks-by-vibes approach
 * produced the British-woman-for-a-boy failure mode. Extend the table when
 * adding new providers / voices; don't move logic upstream.
 *
 * NOTE: provider=elevenlabs returns a *voice_id stub*. ElevenLabs voice IDs are
 * 20-char strings issued by their API. For the MVP we accept a per-provider
 * override file at ~/.claude/story/elevenlabs-voices.json mapping
 * "<age-bucket>:<gender>:<accent>" → "<voice_id>"; if absent we fall back to a
 * descriptive search string the narrate stage can run against GET /v2/voices.
 */

const path = require('path');
const fs = require('fs');

const args = process.argv.slice(2);
if (args.length < 4) {
  process.stderr.write('usage: pick-voice <provider> <age> <gender> <accent> [hint]\n');
  process.exit(2);
}
const [provider, ageRaw, genderRaw, accentRaw, ...hintParts] = args;
const hint = hintParts.join(' ').toLowerCase();

function ageBucket(a) {
  if (a === '-' || a === '—' || !a) return 'narrator';
  const n = parseInt(a, 10);
  if (!Number.isNaN(n)) {
    if (n <= 9) return 'child';
    if (n <= 12) return 'tween';
    if (n <= 17) return 'teen';
    if (n <= 30) return 'young-adult';
    if (n <= 60) return 'adult';
    return 'elder';
  }
  const norm = a.toLowerCase();
  if (['child', 'kid'].includes(norm)) return 'child';
  if (['tween'].includes(norm)) return 'tween';
  if (['teen', 'teenager'].includes(norm)) return 'teen';
  if (['young-adult', 'young_adult', 'youngadult', 'youth'].includes(norm)) return 'young-adult';
  if (['adult', 'middle-aged'].includes(norm)) return 'adult';
  if (['elder', 'senior', 'old'].includes(norm)) return 'elder';
  return 'adult';
}

function gender(g) {
  if (!g || g === '-' || g === '—') return 'neutral';
  const norm = g.toLowerCase();
  if (norm.startsWith('m')) return 'male';
  if (norm.startsWith('f')) return 'female';
  return 'neutral';
}

const ageB = ageBucket(ageRaw);
const gen = gender(genderRaw);
const accent = (accentRaw || '-').toLowerCase();

// ─── OpenAI mapping (6 fixed voices) ─────────────────────────────────────────
// Voice notes from OpenAI samples + community consensus as of 2025:
//   alloy   — neutral, measured (good narrator)
//   echo    — male, mid-pitch, slightly bright (best fit for boy/young-adult male)
//   fable   — British male, warm storyteller
//   onyx    — deep adult male
//   nova    — young adult female, bright
//   shimmer — warm adult female
//
// Children: there is NO true child voice on OpenAI. For child characters we
// pick the closest "lightest" voice and the narrate stage can additionally
// shift pitch a few semitones in FFmpeg if desired. This is a documented
// limitation surfaced in the research report.
const OPENAI = {
  // narrator
  'narrator|neutral|*': 'alloy',
  // child
  'child|male|*': 'echo',
  'child|female|*': 'nova',
  'child|neutral|*': 'echo',
  // tween / teen
  'tween|male|*': 'echo',
  'tween|female|*': 'nova',
  'teen|male|*': 'echo',
  'teen|female|*': 'nova',
  // young-adult
  'young-adult|male|british-rp': 'fable',
  'young-adult|male|*': 'echo',
  'young-adult|female|*': 'nova',
  // adult
  'adult|male|british-rp': 'fable',
  'adult|male|*': 'onyx',
  'adult|female|*': 'shimmer',
  // elder
  'elder|male|british-rp': 'fable',
  'elder|male|*': 'onyx',
  'elder|female|*': 'shimmer',
};

function openAiPick() {
  const exact = `${ageB}|${gen}|${accent}`;
  if (OPENAI[exact]) return OPENAI[exact];
  const star = `${ageB}|${gen}|*`;
  if (OPENAI[star]) return OPENAI[star];
  // Fall through to a neutral default — flag on stderr.
  process.stderr.write(`pick-voice: no OpenAI mapping for ${ageB}/${gen}/${accent}; defaulting to alloy\n`);
  return 'alloy';
}

// ─── ElevenLabs mapping (configurable per-user) ──────────────────────────────
// User-supplied JSON file maps "<bucket>:<gender>:<accent>" → "<voice_id>".
// If missing, emit a descriptive search query the narrate stage can pass to
// GET https://api.elevenlabs.io/v2/voices?search=... and use the top hit.
function elevenLabsPick() {
  const mapPath = path.join(process.env.HOME || '', '.claude/story/elevenlabs-voices.json');
  let table = {};
  try {
    if (fs.existsSync(mapPath)) {
      table = JSON.parse(fs.readFileSync(mapPath, 'utf8'));
    }
  } catch (e) {
    process.stderr.write(`pick-voice: failed to read ${mapPath}: ${e.message}\n`);
  }
  const key = `${ageB}:${gen}:${accent}`;
  if (table[key]) return table[key];
  const keyStar = `${ageB}:${gen}:*`;
  if (table[keyStar]) return table[keyStar];

  // Build a search query as the fallback — the narrate stage runs the lookup.
  const ageWord = ageB === 'child' ? 'young'   // ElevenLabs prohibits child-sounding voices in public library
                : ageB === 'tween' ? 'youthful'
                : ageB === 'teen'  ? 'youthful'
                : ageB === 'young-adult' ? 'youthful'
                : ageB === 'elder' ? 'old'
                : 'adult';
  const accentWord = accent === '-' || accent === 'neutral-us' ? '' : accent.replace(/-/g, ' ');
  const hintWord = hint || '';
  const query = [ageWord, gen === 'neutral' ? '' : gen, accentWord, hintWord]
    .filter(Boolean).join(' ').trim();
  return `SEARCH:${query}`;
}

let result;
switch (provider) {
  case 'openai':
    result = openAiPick();
    break;
  case 'elevenlabs':
    result = elevenLabsPick();
    break;
  default:
    process.stderr.write(`pick-voice: unknown provider "${provider}"\n`);
    process.exit(3);
}

process.stdout.write(result + '\n');
