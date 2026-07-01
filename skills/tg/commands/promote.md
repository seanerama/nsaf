# /tg:promote — Publish a completed techguide to seanmahoney.ai

Promotes the rendered HTML in `output/<slug>/guide/` to the seanmahoney.ai
website's `guides` content collection, following the canonical recipe at:

**`/home/smahoney/seanmahoneyai/deploy-technical-guide.md`**

That file is the source of truth — read it first. The skill executes the
sequence below; for the *why* behind each step, consult the canonical doc.

## Prerequisites
- A completed build at `output/<slug>/guide/` containing either:
  - `index.html` only (variant=explainer or comparison), OR
  - `index.html` + `section-NN.html` files (variant=interactive multi-page hub)
- The website repo is cloned at `$NSAF_WEBSITE_REPO`
  (= `/home/smahoney/projects/seanmahoney/website` on the NSAF server).
- `bun` is on `$PATH` (or `$BUN_PATH` is set).

## Procedure

### 1. Read the canonical recipe
Read `/home/smahoney/seanmahoneyai/deploy-technical-guide.md` end-to-end so the
edge cases (sed delimiter, `&` escaping, multi-page back-link injection,
de-linking repo-relative markdown refs) are loaded.

### 2. Detect layout
From `output/<slug>/guide/`:
```bash
GUIDE=output/<slug>/guide
single=$(ls "$GUIDE" | grep -cE '^index\.html$')
sections=$(ls "$GUIDE" | grep -cE '^section-[0-9]+\.html$')
echo "single=$single sections=$sections"
```
- `sections == 0` AND `single == 1` → **single-page** layout (explainer/comparison).
- `sections >= 1` AND `single == 1` → **multi-page hub** layout (variant=deep).
- Any other shape → STOP and report; do not guess.

### 3. Copy HTML to the website
**Single-page:**
```bash
cp "$GUIDE/index.html" "$NSAF_WEBSITE_REPO/public/guides/<slug>.html"
```
**Multi-page hub:**
```bash
mkdir -p "$NSAF_WEBSITE_REPO/public/guides/<slug>"
cp "$GUIDE"/*.html "$NSAF_WEBSITE_REPO/public/guides/<slug>/"
```

### 4. Dark mode check
Techguides are authored dark on first pass (per `techguide-overrides.md`). If
the HTML happens to ship with the light SWS palette, run the dark-mode `sed`
swap from `deploy-technical-guide.md` Step 3 on each file. Otherwise skip.

### 5. Write the YAML content entry
Pick the next free `order`:
```bash
grep -h '^order:' "$NSAF_WEBSITE_REPO/src/content/guides/"*.yaml | sort -t: -k2 -n | tail -1
```

Write `$NSAF_WEBSITE_REPO/src/content/guides/<slug>.yaml`:
```yaml
title: "<Guide Title from techguide-config.json or output/<slug>/title.txt>"
slug: "<slug>"
description: "One line — what it covers and for whom."
htmlFile: "<slug>.html"           # single-page
# htmlFile: "<slug>/index.html"   # multi-page hub
order: <next number>
```

### 6. Multi-page only — back links + relative links
Per `deploy-technical-guide.md` Step 5b, inject a "← Back to docs" header on
each sub-page if not already present. Verify hub links are RELATIVE
(`href="section-01.html"` not `href="/guides/<slug>/section-01.html"`).

### 7. Build, commit, push
```bash
cd "$NSAF_WEBSITE_REPO"
bun run build       # MUST use bun. npm desyncs the lockfile and breaks CI.

# Stage the guide files
git add public/guides/<slug>* src/content/guides/<slug>.yaml

# Update website-state.md in the SAME commit
# - Add a row to the "Current Technical Guides" table
# - Bump "Last updated"
git add website-state.md  # if you edited it

git commit -m "Add <Guide Title> technical guide"
git pull --rebase   # the remote drifts — always rebase before pushing
git push            # Cloudflare Pages auto-deploys (~60s)
```

### 8. Verify
```bash
# Card on listing page?
grep -c "<slug>" "$NSAF_WEBSITE_REPO/dist/guides/index.html"      # >= 1

# Page served?
ls "$NSAF_WEBSITE_REPO/dist/guides/<slug>".*

# 200 from public URL (after ~60s)
curl -s -o /dev/null -w "%{http_code}\n" "https://seanmahoney.ai/guides/<slug>"
```

## Troubleshooting (delegated to canonical doc)

See `/home/smahoney/seanmahoneyai/deploy-technical-guide.md` "Troubleshooting / Gotchas":
- `npm` → `bun` switch
- non-fast-forward push
- `sed` hex-color delimiter
- stale Astro cache
- imported-markdown 404s

## When done
Update `website-state.md` (Current Technical Guides table + "Last updated") in
the same commit as the YAML drop. This is the source of truth for the next
session.
