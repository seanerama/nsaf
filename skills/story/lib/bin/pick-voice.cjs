#!/usr/bin/env node
'use strict';

/**
 * pick-voice.cjs — voice picker with cast-level de-duplication.
 *
 * Modes:
 *   node pick-voice.cjs cast <provider> <cast.json> [--out <voice-assignments.json>]
 *     Preferred API. Takes the whole cast at once, returns a dedup'd
 *     {name → voice_id} map. Ensures no two characters get the same voice
 *     when a distinct alternative exists.
 *
 *   node pick-voice.cjs single <provider> <age> <gender> <accent> [hint]
 *     Legacy single-character API. No dedup. Kept for backward compat.
 *
 *   node pick-voice.cjs <provider> <age> <gender> <accent> [hint]
 *     Also legacy — infers single mode when the first arg isn't 'cast'
 *     or 'single'.
 *
 * cast.json shape:
 *   [
 *     {"name": "narrator", "age": "-",  "gender": "-", "accent": "neutral-us", "hint": "warm storybook narrator"},
 *     {"name": "Freddie",  "age": "7",  "gender": "male", "accent": "neutral-us", "hint": "curious brave boy"},
 *     {"name": "Alden",    "age": "3",  "gender": "male", "accent": "neutral-us", "hint": "tiny toddler"},
 *     {"name": "Grandpa",  "age": "70", "gender": "male", "accent": "neutral-us", "hint": "warm grandfatherly"}
 *   ]
 *
 * Providers:
 *   openai      — 6 fixed voices, deterministic mapping with cast-level nudge
 *                 when two chars collide (fixes issue #8).
 *   elevenlabs  — fetches the full premade voice list from /v2/voices, scores
 *                 each candidate against the character's labels (gender, age,
 *                 accent, descriptive), assigns highest-scoring not-yet-used
 *                 voice. Falls back to /v1/shared-voices when the premade set
 *                 has no plausible match for the required attributes
 *                 (notably child + elderly). Requires ELEVENLABS_API_KEY.
 *
 * Env:
 *   ELEVENLABS_API_KEY   required for elevenlabs mode
 *   ELEVENLABS_VOICES_CACHE   optional override for the premade-list cache
 *                              (default: ~/.claude/story/elevenlabs-voices-cache.json)
 *
 * Loads ~/nsaf/.env safely if present, so callers don't need to pre-source.
 */

const fs = require('fs');
const path = require('path');
const https = require('https');

// ─── Load ~/nsaf/.env (safe parser, matches load-nsaf-env.sh) ───────────────

function loadNsafEnv() {
  const p = path.join(process.env.HOME || '', 'nsaf/.env');
  if (!fs.existsSync(p)) return;
  const lines = fs.readFileSync(p, 'utf8').split('\n');
  for (const raw of lines) {
    const line = raw.replace(/\r$/, '');
    const stripped = line.trimStart();
    if (!stripped || stripped.startsWith('#')) continue;
    const eq = line.indexOf('=');
    if (eq <= 0) continue;
    const key = line.slice(0, eq).trim();
    if (!/^[A-Za-z_][A-Za-z0-9_]*$/.test(key)) continue;
    let value = line.slice(eq + 1);
    if (value.length >= 2 && value[0] === value[value.length - 1] && (value[0] === '"' || value[0] === "'")) {
      value = value.slice(1, -1);
    }
    if (process.env[key] == null) process.env[key] = value;
  }
}
loadNsafEnv();

// ─── Attribute normalization ────────────────────────────────────────────────

function ageBucket(a) {
  if (a === '-' || a === '—' || !a) return 'narrator';
  const n = parseInt(a, 10);
  if (!Number.isNaN(n)) {
    if (n <= 9)  return 'child';
    if (n <= 12) return 'tween';
    if (n <= 17) return 'teen';
    if (n <= 30) return 'young-adult';
    if (n <= 60) return 'adult';
    return 'elder';
  }
  const norm = a.toLowerCase();
  if (['child','kid'].includes(norm)) return 'child';
  if (['tween'].includes(norm)) return 'tween';
  if (['teen','teenager'].includes(norm)) return 'teen';
  if (['young-adult','young_adult','youngadult','youth'].includes(norm)) return 'young-adult';
  if (['adult','middle-aged'].includes(norm)) return 'adult';
  if (['elder','senior','old'].includes(norm)) return 'elder';
  return 'adult';
}

function genderNorm(g) {
  if (!g || g === '-' || g === '—') return 'neutral';
  const n = g.toLowerCase();
  if (n.startsWith('m')) return 'male';
  if (n.startsWith('f')) return 'female';
  return 'neutral';
}

// ─── OpenAI: 6-voice mapping with cast-level dedup ─────────────────────────

const OPENAI_VOICES = ['alloy', 'echo', 'fable', 'onyx', 'nova', 'shimmer'];

// Preference matrix: for each (bucket, gender, accent), an ordered list of
// preferred voices — first is best, subsequent are fallbacks if the best is
// already used by another character in the same cast.
const OPENAI_PREF = {
  // (age|gender|accent) → ordered preferences
  'narrator|neutral|*':          ['alloy', 'shimmer', 'onyx', 'fable', 'nova', 'echo'],
  'child|male|*':                ['echo', 'nova', 'alloy', 'shimmer', 'fable', 'onyx'],
  'child|female|*':              ['nova', 'shimmer', 'alloy', 'echo', 'fable', 'onyx'],
  'child|neutral|*':             ['echo', 'nova', 'alloy', 'shimmer', 'fable', 'onyx'],
  'tween|male|*':                ['echo', 'alloy', 'nova', 'fable', 'shimmer', 'onyx'],
  'tween|female|*':              ['nova', 'shimmer', 'alloy', 'echo', 'fable', 'onyx'],
  'teen|male|*':                 ['echo', 'alloy', 'fable', 'nova', 'shimmer', 'onyx'],
  'teen|female|*':               ['nova', 'shimmer', 'alloy', 'echo', 'fable', 'onyx'],
  'young-adult|male|british-rp': ['fable', 'echo', 'onyx', 'alloy', 'nova', 'shimmer'],
  'young-adult|male|*':          ['echo', 'onyx', 'alloy', 'fable', 'nova', 'shimmer'],
  'young-adult|female|*':        ['nova', 'shimmer', 'alloy', 'echo', 'fable', 'onyx'],
  'adult|male|british-rp':       ['fable', 'onyx', 'echo', 'alloy', 'nova', 'shimmer'],
  'adult|male|*':                ['onyx', 'echo', 'fable', 'alloy', 'nova', 'shimmer'],
  'adult|female|*':              ['shimmer', 'nova', 'alloy', 'onyx', 'echo', 'fable'],
  'elder|male|british-rp':       ['fable', 'onyx', 'echo', 'alloy', 'nova', 'shimmer'],
  'elder|male|*':                ['onyx', 'fable', 'echo', 'alloy', 'nova', 'shimmer'],
  'elder|female|*':              ['shimmer', 'nova', 'alloy', 'fable', 'echo', 'onyx'],
};

function openAiPreferences(bucket, gender, accent) {
  const exact = `${bucket}|${gender}|${accent}`;
  if (OPENAI_PREF[exact]) return OPENAI_PREF[exact];
  const star = `${bucket}|${gender}|*`;
  if (OPENAI_PREF[star]) return OPENAI_PREF[star];
  return OPENAI_VOICES.slice(); // any voice, in default order
}

function assignOpenAiCast(cast) {
  const used = new Set();
  const result = {};
  for (const c of cast) {
    const bucket = ageBucket(c.age);
    const gen = genderNorm(c.gender);
    const acc = (c.accent || '-').toLowerCase();
    const prefs = openAiPreferences(bucket, gen, acc);
    const pick = prefs.find(v => !used.has(v)) || prefs[0];
    used.add(pick);
    result[c.name] = pick;
  }
  return result;
}

// ─── ElevenLabs: HTTP + scoring + assignment ────────────────────────────────

function httpsRequest(method, url, headers = {}, body = null) {
  return new Promise((resolve, reject) => {
    const u = new URL(url);
    const opts = {
      method,
      hostname: u.hostname,
      port: u.port || 443,
      path: u.pathname + u.search,
      headers,
    };
    const req = https.request(opts, res => {
      const chunks = [];
      res.on('data', c => chunks.push(c));
      res.on('end', () => {
        const raw = Buffer.concat(chunks).toString('utf8');
        resolve({ status: res.statusCode, body: raw, headers: res.headers });
      });
    });
    req.on('error', reject);
    if (body) req.write(body);
    req.end();
  });
}

async function fetchElevenLabsVoices(apiKey) {
  // Cache the /v2/voices?page_size=100 response for the day. This list changes
  // rarely and paying the ~1 s roundtrip per pick-voice invocation is wasteful.
  const cachePath = process.env.ELEVENLABS_VOICES_CACHE
    || path.join(process.env.HOME || '', '.claude/story/elevenlabs-voices-cache.json');
  const CACHE_TTL_SECS = 24 * 3600;

  try {
    if (fs.existsSync(cachePath)) {
      const stat = fs.statSync(cachePath);
      if ((Date.now() - stat.mtimeMs) / 1000 < CACHE_TTL_SECS) {
        return JSON.parse(fs.readFileSync(cachePath, 'utf8'));
      }
    }
  } catch {}

  const r = await httpsRequest(
    'GET',
    'https://api.elevenlabs.io/v2/voices?page_size=100',
    { 'xi-api-key': apiKey },
  );
  if (r.status !== 200) {
    throw new Error(`elevenlabs /v2/voices HTTP ${r.status}: ${r.body.slice(0, 200)}`);
  }
  const data = JSON.parse(r.body);
  const voices = data.voices || [];
  try {
    fs.mkdirSync(path.dirname(cachePath), { recursive: true });
    fs.writeFileSync(cachePath, JSON.stringify(voices, null, 2));
  } catch {}
  return voices;
}

async function fetchSharedVoices(apiKey, params) {
  // /v1/shared-voices lets us discover community voices for the categories the
  // premade set doesn't cover well — notably actual child and very elderly.
  const qs = new URLSearchParams(params).toString();
  const r = await httpsRequest(
    'GET',
    `https://api.elevenlabs.io/v1/shared-voices?${qs}`,
    { 'xi-api-key': apiKey },
  );
  if (r.status !== 200) return [];
  try {
    const data = JSON.parse(r.body);
    return data.voices || [];
  } catch {
    return [];
  }
}

// Score a voice (with .labels) against a character's normalized attributes.
// Higher score = better match. 0 = incompatible.
function scoreElevenLabsVoice(voice, wantGender, wantBucket, wantAccent, wantHint) {
  const labels = voice.labels || {};
  const l = k => (labels[k] || '').toLowerCase();
  const desc = (l('description') + ' ' + l('descriptive') + ' ' + l('use_case') + ' ' + (voice.description || '').toLowerCase()).trim();

  let score = 0;

  // Gender: hard requirement when not neutral.
  const voiceGender = l('gender');
  if (wantGender !== 'neutral') {
    if (voiceGender && voiceGender !== wantGender) return 0;
    if (voiceGender === wantGender) score += 20;
  }

  // Age: ElevenLabs uses labels like "young", "middle_aged", "old", "child".
  const voiceAge = l('age');
  const bucketAliases = {
    'child': ['child', 'young'],
    'tween': ['young', 'child'],
    'teen': ['young'],
    'young-adult': ['young', 'middle_aged'],
    'adult': ['middle_aged', 'young'],
    'elder': ['old', 'middle_aged'],
    'narrator': ['young', 'middle_aged', 'old'],
  };
  const wantAgeSet = new Set(bucketAliases[wantBucket] || []);
  if (voiceAge && wantAgeSet.has(voiceAge)) score += 15;

  // Accent: soft match.
  const voiceAccent = l('accent');
  if (wantAccent && wantAccent !== '-' && wantAccent !== 'neutral-us') {
    const normalized = wantAccent.replace(/-/g, ' ');
    if (voiceAccent && (normalized.includes(voiceAccent) || voiceAccent.includes(normalized))) {
      score += 10;
    }
  } else if (voiceAccent === 'american' || voiceAccent === '') {
    score += 3;
  }

  // Hint keywords: any word in the hint that appears in the voice description.
  if (wantHint) {
    const words = wantHint.toLowerCase().split(/\W+/).filter(w => w.length > 3);
    for (const w of words) {
      if (desc.includes(w)) score += 4;
    }
  }

  // Narration category is preferred for narrator role.
  const category = (voice.category || '').toLowerCase();
  if (wantBucket === 'narrator' && category.includes('narrat')) score += 6;

  // Small preference for premade over generated/cloned within the same score band.
  if (category === 'premade') score += 1;

  return score;
}

async function assignElevenLabsCast(cast, apiKey) {
  const premade = await fetchElevenLabsVoices(apiKey);
  const used = new Set();
  const result = {};
  const warnings = [];

  // Pre-fetch shared voices for child + elder needs (one call each per bucket).
  const sharedCache = {};
  async function getSharedFor(bucket, gender) {
    const key = `${bucket}|${gender}`;
    if (sharedCache[key]) return sharedCache[key];
    const params = { language: 'en', page_size: '50' };
    if (bucket === 'child')  { params.age = 'young'; }
    if (bucket === 'elder')  { params.age = 'old'; }
    if (gender !== 'neutral') params.gender = gender;
    sharedCache[key] = await fetchSharedVoices(apiKey, params);
    return sharedCache[key];
  }

  for (const c of cast) {
    const bucket = ageBucket(c.age);
    const gen = genderNorm(c.gender);
    const acc = (c.accent || '-').toLowerCase();
    const hint = (c.hint || '').toLowerCase();

    // Score premade voices first.
    const scored = premade
      .map(v => ({ v, s: scoreElevenLabsVoice(v, gen, bucket, acc, hint) }))
      .filter(x => x.s > 0 && !used.has(x.v.voice_id))
      .sort((a, b) => b.s - a.s);

    let chosen = scored[0]?.v;

    // Fall back to shared voices for child + elder if no premade match.
    if (!chosen && (bucket === 'child' || bucket === 'elder')) {
      const shared = await getSharedFor(bucket, gen);
      const sscored = shared
        .map(v => ({ v, s: scoreElevenLabsVoice(v, gen, bucket, acc, hint) }))
        .filter(x => x.s > 0 && !used.has(x.v.voice_id))
        .sort((a, b) => b.s - a.s);
      if (sscored[0]) {
        chosen = sscored[0].v;
        warnings.push(`${c.name}: using shared voice ${chosen.voice_id} (${chosen.name || '?'}) — premade set has no ${bucket} match`);
      }
    }

    // Last-resort: any premade voice not yet used.
    if (!chosen) {
      chosen = premade.find(v => !used.has(v.voice_id));
      if (chosen) warnings.push(`${c.name}: no attribute-match voice found; using unused premade ${chosen.name || chosen.voice_id}`);
    }

    if (!chosen) {
      throw new Error(`no ElevenLabs voice found for ${c.name}`);
    }
    used.add(chosen.voice_id);
    result[c.name] = chosen.voice_id;
  }

  return { assignments: result, warnings };
}

// ─── Mode dispatch ─────────────────────────────────────────────────────────

async function main() {
  const args = process.argv.slice(2);
  if (args.length === 0) {
    process.stderr.write('usage: pick-voice.cjs cast <provider> <cast.json> [--out <path>]\n');
    process.stderr.write('       pick-voice.cjs single <provider> <age> <gender> <accent> [hint]\n');
    process.exit(2);
  }

  let mode = args[0];
  let rest = args.slice(1);
  if (mode !== 'cast' && mode !== 'single') {
    // Legacy: <provider> <age> <gender> <accent> [hint]
    mode = 'single';
    rest = args;
  }

  if (mode === 'cast') {
    const provider = rest[0];
    const castPath = rest[1];
    let outPath = null;
    for (let i = 2; i < rest.length; i++) {
      if (rest[i] === '--out' && rest[i + 1]) { outPath = rest[++i]; }
    }
    if (!provider || !castPath) {
      process.stderr.write('cast usage: pick-voice.cjs cast <openai|elevenlabs> <cast.json> [--out <path>]\n');
      process.exit(2);
    }
    if (!fs.existsSync(castPath)) {
      process.stderr.write(`cast.json not found: ${castPath}\n`);
      process.exit(2);
    }
    const cast = JSON.parse(fs.readFileSync(castPath, 'utf8'));

    let assignments, warnings = [];
    if (provider === 'openai') {
      assignments = assignOpenAiCast(cast);
    } else if (provider === 'elevenlabs') {
      const key = process.env.ELEVENLABS_API_KEY;
      if (!key) { process.stderr.write('ELEVENLABS_API_KEY not set\n'); process.exit(3); }
      const r = await assignElevenLabsCast(cast, key);
      assignments = r.assignments;
      warnings = r.warnings;
    } else {
      process.stderr.write(`unknown provider: ${provider}\n`);
      process.exit(3);
    }

    if (warnings.length) {
      for (const w of warnings) process.stderr.write(`WARN: ${w}\n`);
    }
    const outText = JSON.stringify(assignments, null, 2) + '\n';
    if (outPath) {
      fs.mkdirSync(path.dirname(outPath), { recursive: true });
      fs.writeFileSync(outPath, outText);
      process.stderr.write(`wrote ${outPath}\n`);
    }
    process.stdout.write(outText);
    return;
  }

  // Legacy single mode: no dedup.
  const [provider, ageRaw, genderRaw, accentRaw, ...hintParts] = rest;
  if (!provider || ageRaw === undefined || genderRaw === undefined || accentRaw === undefined) {
    process.stderr.write('single usage: pick-voice.cjs single <provider> <age> <gender> <accent> [hint]\n');
    process.exit(2);
  }
  const hint = hintParts.join(' ');
  const fakeCast = [{ name: '_', age: ageRaw, gender: genderRaw, accent: accentRaw, hint }];

  let assignments;
  if (provider === 'openai') {
    assignments = assignOpenAiCast(fakeCast);
  } else if (provider === 'elevenlabs') {
    const key = process.env.ELEVENLABS_API_KEY;
    if (!key) { process.stderr.write('ELEVENLABS_API_KEY not set\n'); process.exit(3); }
    const r = await assignElevenLabsCast(fakeCast, key);
    assignments = r.assignments;
  } else {
    process.stderr.write(`unknown provider: ${provider}\n`);
    process.exit(3);
  }
  process.stdout.write(assignments['_'] + '\n');
}

main().catch(e => {
  process.stderr.write(`pick-voice fatal: ${e.message}\n`);
  process.exit(1);
});
