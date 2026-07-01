# Daily-Brief User Guide

Daily-Brief catches you up on the news that matters — through the lens of whatever **role**
you're wearing. Ask for a brief, and it researches your sources and the open web, skips what
you've already seen, explains *why each item matters to you*, and hands you back an interactive
web page, a markdown summary, and a podcast script.

This guide walks you from zero to your first brief, then through everyday use.

---

## 1. Concepts in 60 seconds

- **Profile** — a role/lens you wear, like *AI Engineer*, *Realtor*, or *Parent*. Each profile
  has its own topics, sources, and memory. There's a built-in **General** profile for
  everything else.
- **Brief** — one run's output: an interactive HTML page, a markdown summary, and a podcast
  script, all saved together.
- **Two ways to ask:**
  - **Run** — "sweep everything in this profile" (`/brief:run`).
  - **Topic** — "just catch me up on this one thing" (`/brief:topic`).
- **Memory** — every brief is logged per profile, so future briefs skip repeats and tell you
  *"also covered by X on DATE"* instead.

---

## 2. First-time setup

Install once (see the [README](../README.md) for the full list):

```bash
pip install -e .
cp .env.example .env          # add your PERPLEXITY_API_KEY
ln -s "$(pwd)/commands/brief" ~/.claude/commands/brief
brief init                    # creates your data folder + the General profile
```

Confirm it's working:

```bash
brief status
```

You should see the **General** profile listed.

---

## 3. Your first brief

The fastest way to see Daily-Brief work is a single-topic brief on the General profile:

```
/brief:topic "what happened in AI this week"
```

Daily-Brief will research the topic, build the outputs, and tell you where they landed:

```
data/briefs/general/2026-06-29-1430/
  brief.html          ← open this in your browser
  summary.md          ← skimmable markdown
  podcast-script.md   ← two-host deep-dive script
  run.json            ← machine record of the run
```

Open `brief.html` in any browser. It works offline — no internet needed to read it.

---

## 4. Reading an interactive brief

`brief.html` is a single self-contained page built for skimming:

- **Collapsible topics** — click a topic heading to fold/unfold it.
- **Search** — type in the search box to filter items by title and summary.
- **Filters** — click the **source** and **date** chips to narrow what's shown.
- **Mark as read** — tick the *read* box on any item; it dims and is remembered the next time
  you open the page (stored in your browser).
- **Hide read** — flip the toggle to clear out everything you've already seen.
- **Why this matters** — every item has a highlighted line explaining its relevance to your
  active profile.
- **Prior coverage** — if you've seen something before, it's flagged *"Also covered by … on …"*
  rather than shown as new.

The podcast script lives next to it in `podcast-script.md` (audio generation is planned for a
later version).

---

## 5. Creating a profile

The General profile is fine for ad-hoc questions, but the real power is a profile tuned to a
role you care about. Create one with:

```
/brief:setup ai-engineer
```

Daily-Brief asks a few questions — the role's display name, a one-line description of the lens,
and the topics and sources you want followed — then writes the profile for you.

Prefer to do it by hand or in a hurry? Scaffold from the CLI:

```bash
brief profile create realtor \
  --title "Realtor" \
  --description "a realtor tracking local housing trends and mortgage rates" \
  --from-sample
```

Then edit `data/profiles/realtor/reference.md` to list your real topics and sources. See the
[Profiles guide](profiles.md) for the file format.

Check what a profile contains anytime:

```bash
brief profile show realtor
```

---

## 6. Everyday use

**Catch up on a whole profile** — sweeps every topic's sources plus the open web:

```
/brief:run ai-engineer
```

**Catch up on one topic** — quick and focused; tells you what's new since you last looked:

```
/brief:topic "open-source model releases" ai-engineer
```

**Point a topic at specific sources** (overriding the profile's defaults):

```
/brief:topic "interest rate news" realtor "Federal Reserve, WSJ"
```

**Check your state** — profiles, how much history each has, and your last run:

```
/brief:status
```

**See all commands:**

```
/brief:help
```

---

## 7. How memory works for you

You don't manage memory — it just makes each brief better:

- Every item in every brief is logged to that profile's history.
- The next brief checks new findings against that history. Repeats aren't dropped silently;
  they're surfaced with a *"also covered by …"* note so you keep the context without re-reading.
- A topic brief uses history to focus on *what's new since* your last look at that topic.

Each profile keeps its memory separate, so your *Realtor* history never muddies your
*AI Engineer* briefs.

---

## 8. Where everything lives

```
data/
  profiles/<profile>/
    reference.md        your profile: topics + sources (safe to hand-edit)
    history.md          what you've already been briefed on
    knowledge-base.md   accumulated learnings for this profile
  briefs/<profile>/<timestamp>/
    brief.html  summary.md  podcast-script.md  run.json  run.log
```

Everything is plain files on your machine. Back up the `data/` folder and you've backed up
everything. To move a profile to another machine, copy its folder.

---

## 9. Troubleshooting

| Symptom | Fix |
|--------|-----|
| `/brief:run` says the profile doesn't exist | Run `/brief:setup <name>` first, or check `brief profile list`. |
| Open-web research returns nothing | Confirm `PERPLEXITY_API_KEY` is set in `.env` and the Perplexity MCP server is configured in Claude Code. |
| A source shows up under "Could not fetch" | That source was unreachable (often a login/paywall). v1 only reads publicly available pages. |
| `brief: command not found` | Activate your virtualenv and run `pip install -e .` again. |
| I want to start a profile's memory over | Delete (or empty) `data/profiles/<profile>/history.md`. |

---

## 10. What's coming later

Planned for future versions: pulling YouTube channel content, generating podcast **audio**
(not just the script), asking questions of a profile's accumulated knowledge, and scheduled
unattended briefs. Today's version is on-demand and script-based by design.

For the command-line details behind the scenes, see the [CLI reference](cli-reference.md).
