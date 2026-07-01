# Profiles Guide

A **profile** is a role you wear — the lens Daily-Brief uses to decide *what to research* and
*why each item matters to you*. This guide explains the profile file format so you can author
and tune profiles by hand.

## Where profiles live

Each profile is a folder under `data/profiles/<slug>/`:

| File | Purpose | Hand-edit? |
|------|---------|------------|
| `reference.md` | The profile's config: topics + sources. | ✅ Yes — this is the one you edit. |
| `history.md` | Append-only log of what you've been briefed on. | Rarely (clear it to reset memory). |
| `knowledge-base.md` | Accumulated learnings for this profile. | Optional. |

The `slug` is the folder name and must be filesystem-safe (lowercase, hyphens), e.g.
`ai-engineer`, `realtor`, `parent`.

## The `reference.md` format

A profile is YAML frontmatter (its identity) followed by a `## Topics` section:

```markdown
---
slug: ai-engineer
title: AI Engineer
description: An AI engineer who ships LLM products and tracks the field's fast-moving frontier.
---

## Topics

### Model releases
- web_search: true
- source: Anthropic News (news) https://www.anthropic.com/news
- source: Simon Willison (blog) https://simonwillison.net

### AI agents
- web_search: true
- source: Stratechery (blog) https://stratechery.com

### Developer tooling
- web_search: true
```

### Frontmatter fields

| Field | Required | Notes |
|-------|----------|-------|
| `slug` | yes | Must match the folder name. |
| `title` | yes | Display name shown in briefs and `brief status`. |
| `description` | yes | **The lens.** Write it as *"a `<role>` who …"* — every "why this matters" line is framed from this. Make it specific. |

### Topics

Each `### Heading` is a topic. Under it:

- **`- web_search: true|false`** — should Daily-Brief also research the open web (via Perplexity)
  for this topic? Defaults to `false` if omitted.
- **`- source: NAME (TYPE) URL`** — a specific source to check. The URL is optional.

### Source types

| Type | Meaning |
|------|---------|
| `website` | A general website. |
| `blog` | A blog or newsletter. |
| `news` | A news outlet. |
| `web-search` | Open-web search (usually you'd just set `web_search: true` instead of listing this). |
| `youtube` | A YouTube channel. *Stored but not yet ingested — reserved for a future version.* |

An unrecognized type is treated as `website` rather than dropped.

## Common patterns

**Pure open-web topic** — no fixed sources, just "find me the latest":

```markdown
### Interest rates
- web_search: true
```

**Curated sources only** — check exactly these, skip the open web:

```markdown
### Company blogs I trust
- web_search: false
- source: Stratechery (blog) https://stratechery.com
- source: Simon Willison (blog) https://simonwillison.net
```

**Both** — check your sources *and* sweep the open web:

```markdown
### Model releases
- web_search: true
- source: Anthropic News (news) https://www.anthropic.com/news
```

## Creating and validating

Scaffold a new profile (then edit the generated `reference.md`):

```bash
brief profile create parent \
  --title "Parent" \
  --description "a parent of school-age kids tracking education and child-health news" \
  --from-sample      # optional: seeds example topics you can replace
```

After editing, confirm it parses correctly:

```bash
brief profile show parent
```

If a topic or source is missing from the output, check that the line matches the
`- source: NAME (TYPE) URL` shape exactly. Lines that don't match are ignored.

## Tips for good profiles

- **Write the `description` carefully** — it does the heavy lifting on relevance. "a realtor"
  is weaker than "a residential realtor in Austin tracking inventory, rates, and zoning."
- **Keep topics focused.** A handful of sharp topics beats one broad "everything" topic.
- **Mix sources and open web.** Trusted sources give depth; `web_search: true` catches what you
  didn't think to subscribe to.
- **One profile per role, not per subject.** Subjects are topics *within* a profile.

For day-to-day usage, see the [User Guide](user-guide.md).
