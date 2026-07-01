---
description: Scope a variant=comparison techguide — products × axes feature matrix
---

# /tg:scope-comparison — Outline a product/technology comparison

You were dispatched here from `/tg:scope` because `variant=comparison`.

A **comparison** techguide is a head-to-head matrix of 3–5 products (or
technologies, vendors, approaches) across 5–10 feature axes, plus a short
per-product narrative writeup. The reader sees the matrix first, can sort
and filter, then expands a product for the writeup. Think of vendor selection
guides on a vendor-neutral analyst site.

## Your job

Produce `output/<topic-slug>/outline.json` with the following shape:

```json
{
  "topic": "<from config.topic>",
  "variant": "comparison",
  "level": "<from config.level>",
  "products": [
    {
      "id": "vendor-cisco-catalyst-8500",
      "name": "Cisco Catalyst 8500",
      "vendor": "Cisco",
      "short_label": "Catalyst 8500",
      "positioning": "1–2 sentence summary of where this product fits / who it's for."
    },
    ...
  ],
  "axes": [
    {
      "id": "axis-throughput",
      "label": "Max Throughput",
      "kind": "quantitative",
      "unit": "Gbps",
      "why_it_matters": "1 sentence explaining the decision relevance.",
      "sort": "desc-better"
    },
    {
      "id": "axis-tls-offload",
      "label": "Hardware TLS Offload",
      "kind": "categorical",
      "categories": ["yes", "limited", "no"],
      "why_it_matters": "...",
      "sort": "categorical"
    },
    ...
  ],
  "scoring_rubric": "1–3 sentence explanation of how you'll judge \"better/worse\" per axis. Will be quoted on the page so readers can audit your bias."
}
```

## Product rules

- **Product count by comparison type:**
  - **Cross-vendor** (Cisco vs Fortinet vs Palo Alto): 3–5 products.
  - **Intra-family / intra-vendor** (the SKUs within one product line, the
    license tiers within one SaaS, the models within one car lineup): up to
    **20 products** — **enumerate every currently-shipping SKU** in the
    family. Do NOT prune to "the most decision-relevant N" — the reader is
    comparing variants and wants every variant visible. Only drop SKUs that
    are end-of-life, end-of-sale, or trivially-redundant rebadges.

  Use `config.products[]` if set — it overrides this guidance. Otherwise infer
  from `topic` and `notes`. If you can't infer at least 3 distinct products,
  STOP and report back to the dispatcher — comparison isn't the right variant.

- **Prefer specific SKUs/models, NOT parent series or families.** When the topic
  names a product line, series, or family, enumerate the individual SKUs within
  it. Do NOT collapse them into a single per-series entry — the reader is
  picking a specific model to buy, and the matrix should compare specific models
  with specific specs. Examples:
  - Topic "Cisco Catalyst 8000 series routers" → products are
    `C8200-1N-4T`, `C8200L-1N-4T`, `C8300-1N1S-6T`, `C8300-2N2S-6T`,
    `C8500-12X`, `C8500L-8S4X`, `C8000V`, etc. — NOT a single "Catalyst 8200
    Series Edge Platforms" entry.
  - Topic "Apple silicon MacBooks" → products are `MacBook Air 13 M3`,
    `MacBook Air 15 M3`, `MacBook Pro 14 M3`, `MacBook Pro 14 M3 Pro`,
    `MacBook Pro 16 M3 Max`, etc.
  - Topic "AWS EC2 compute-optimized instances" → products are `c7i.xlarge`,
    `c7i.2xlarge`, `c7g.xlarge`, etc. — NOT a single "C7 family" entry.

  If the family has more than 20 currently-shipping SKUs, pick the 20 most
  decision-relevant variants (one of each form factor / one per tier / one
  per generation). Below 20, do not prune — enumerate them all. It is
  always better to drop niche SKUs than to lump everything into series-level
  rows.

- **Each product is real, currently shipping, and named accurately.** Use
  vendor's own model/version naming exactly (e.g., `C8300-2N2S-6T`, not
  "8300 with 2N2S"). When a SKU has a marketing-name and a part-number,
  use the part-number — buyers search and purchase by part number.

- `positioning` is short — one or two sentences naming the niche or differentiator
  *vs other products in the same matrix*. For intra-family comparisons, that
  means saying what slot this SKU fills within the family (e.g., "fanless
  small-branch variant of the 8200 line"), not what the whole family does.

## Axis rules

- **5–10 axes.** Choose axes that materially affect a buyer/operator decision.
  Avoid trivia axes ("supports SNMP" — most everything does).
- **Mix `quantitative` and `categorical`** — quantitative axes (throughput,
  port count, max sessions) sort numerically; categorical axes (cloud-managed
  yes/no/hybrid, license model) sort categorically.
- **`why_it_matters` is required on every axis.** A reader should be able to
  understand the relevance from the axis label + `why_it_matters` alone.
- **`sort: "desc-better"` or `"asc-better"`** for quantitative axes makes the
  table's default sort meaningful.

## Source-material handling

If `has_source_file: true`, the file is the authoritative source for product
specs. Cross-reference with public datasheets if accessible via WebFetch —
do not invent numbers.

## Forbidden

- No `chapters` or `sections` arrays — these are `products` + `axes`.
- No per-axis essays — the axis description goes in `why_it_matters` (one sentence).
- No "winner" declarations — the matrix and writeups present tradeoffs; readers decide.

## When done

Save `outline.json`, then return control to the parent dispatcher.
The dispatcher will auto-chain to `/tg:research`.
