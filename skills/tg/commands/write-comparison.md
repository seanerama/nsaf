---
description: Write content for variant=comparison — vendor narratives + matrix data
---

# /tg:write-comparison — Author per-vendor narratives and the matrix data

You were dispatched here from `/tg:write` because `variant=comparison`.

## Your job

Produce two kinds of files under `output/<topic-slug>/vendors/`:

### 1. Per-vendor narrative — one file per `outline.products[]`

```
output/<topic-slug>/vendors/vendor-<id>.md
```

where `<id>` is the product's `id` from outline.json (e.g. `vendor-cisco-catalyst-8500`).

Frontmatter:
```yaml
---
product_id: vendor-cisco-catalyst-8500
name: "Cisco Catalyst 8500"
vendor: "Cisco"
order: 1
---
```

Body (300–600 words):
- **First paragraph**: 1–2 sentences naming who this product is for and what it
  trades for that fit (no marketing puff).
- **`## What it is`** — 2–4 sentences of technical positioning. What category,
  what generation, what's the architecture in one mental model.
- **`## Where it wins`** — 3–5 bullets of CONCRETE strengths grounded in axes
  from outline.json. Each bullet should reference at least one quantitative or
  categorical fact from research.
- **`## Where it doesn't`** — 3–5 bullets of CONCRETE weaknesses, gaps, or
  not-the-best-fit scenarios. If you can't name any, you haven't researched
  deeply enough. Go back to the research file.
- **`## When to pick it`** — 1–2 sentences naming the buyer profile this is the
  right answer for.
- **`## References`** — footnote-style citations to the research file's sources.

### 2. The matrix data — `output/<topic-slug>/vendors/matrix.md`

A single file capturing the full N products × M axes cell data. Use YAML
frontmatter for the matrix structure, then markdown for any per-cell notes
that don't fit a clean value:

```yaml
---
axes:
  - id: axis-throughput
    label: Max Throughput
    unit: Gbps
    kind: quantitative
  - id: axis-tls-offload
    label: Hardware TLS Offload
    kind: categorical
cells:
  vendor-cisco-catalyst-8500:
    axis-throughput: 200
    axis-tls-offload: "yes"
  vendor-versa-secure-sd-wan:
    axis-throughput: 80
    axis-tls-offload: "limited"
  # ... one row per product, one column per axis
---

# Matrix notes

## Cisco Catalyst 8500 × Throughput
The 200 Gbps figure is the max forwarding throughput per chassis with all
acceleration features enabled (DPI off). Real-world deployments… <!-- only
add notes where the cell value alone is misleading -->
```

## Parallelism

Spawn parallel sub-agents via the Agent tool — one per product (for the
narratives). The matrix.md is produced LAST, after all vendor markdowns
are complete, by a single sub-agent that reads all of them.

## Cell-value discipline

- **Every cell must have a value.** If you cannot find authoritative data
  for a cell, use the string `"unknown"` (NOT a guess, NOT an em-dash).
  Add a "Matrix notes" entry explaining what you searched.
- **Quantitative cells are numbers**, no units in the value (units live on the axis).
- **Categorical cells use the axis's declared categories exactly** (e.g.
  if axis categories are `["yes", "limited", "no"]`, do not write `"partial"`).
- **Prefer vendor's own published specs** as the citation. Cross-check with
  one independent source (analyst report, technical blog) where possible.

## Tone

Comparative-but-fair. Every product gets a "Where it wins" AND a "Where it
doesn't". No product is declared the winner overall — the matrix and writeups
present tradeoffs; readers decide.

## Forbidden

- No "Verdict" or "Our pick" sections.
- No marketing language ("industry-leading", "best-in-class").
- No vendor.md with empty Where-it-doesn't sections — that's a research gap.
- Do not write into `chapters/` (SWS legacy).

## When all vendor files + matrix.md are written

Return control to the parent dispatcher. It auto-chains to `/tg:diagrams`.
