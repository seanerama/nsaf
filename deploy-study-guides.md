# Deploy Study Guide to seanmahoney.ai

## Quick Start

**User prompt:** "Deploy the study guide in `<folder-path>` to seanmahoney.ai"

This workflow takes a folder containing HTML study guides, chapter markdown files, and (optionally) a long-form textbook markdown file, and deploys them all to the seanmahoney.ai website. Each study guide can be paired with a textbook companion that renders at `/study-guides/<slug>/textbook` with mermaid diagram support.

---

## What This Workflow Does

1. Reads the source folder for HTML guide files, chapter markdown files, and (if present) a textbook markdown file
2. Extracts chapter titles from the markdown files
3. Copies HTML guides to the website repo's public directory
4. Converts guides to dark mode (CSS variable swap)
5. Creates a YAML content entry for the Astro content collection
6. If a textbook is present, copies it into the textbooks content collection with frontmatter so the "Read full textbook →" link appears on the study guide card
7. Builds, commits, and pushes — Cloudflare Pages auto-deploys

---

## Expected Source Folder Structure

The agent should search the provided folder recursively for:
- `guides/chapter-XX.html` — interactive HTML study guides (required)
- `chapters/chapter-XX.md` — markdown chapters with titles in `## Chapter N: Title` format (required for title extraction)
- `textbook.md` — long-form companion book (optional; deploys as a separate page if present)

The folder may be nested (e.g., `folder/subfolder/guides/`). The agent should find the correct paths.

---

## Step-by-Step Procedure

### 1. Discover Files

```bash
# Find HTML guides
find <source-folder> -name '*.html' -path '*/guides/*' -not -name '*Zone*' | sort

# Extract chapter titles from markdown
find <source-folder> -name 'chapter-*.md' -path '*/chapters/*' -not -name '*Zone*' | sort | while read f; do
  head -3 "$f" | grep -E '^#' | head -1
done

# Look for a textbook companion (optional)
find <source-folder> -maxdepth 3 -iname 'textbook.md' -not -name '*Zone*'
```

### 2. Choose a Slug

Create a URL-friendly slug for the guide (e.g., `cisco-dcaie`, `kubernetes-ai`, `dgx-spark`). This becomes:
- The directory name: `public/study-guides/<slug>/`
- The YAML filename: `src/content/studyGuides/<slug>.yaml`
- The URL path: `seanmahoney.ai/study-guides/<slug>/chapter-XX.html`

### 3. Copy HTML Files

```bash
mkdir -p /home/smahoney/projects/seanmahoney/website/public/study-guides/<slug>
cp <source-folder>/.../guides/chapter-*.html /home/smahoney/projects/seanmahoney/website/public/study-guides/<slug>/
```

### 4. Convert to Dark Mode

Run this sed on every copied HTML file:

```bash
cd /home/smahoney/projects/seanmahoney/website/public/study-guides/<slug>
for f in chapter-*.html; do
  sed -i \
    -e 's/--color-bg: #fafafa/--color-bg: #0a0a0f/' \
    -e 's/--color-surface: #ffffff/--color-surface: #1a1d2e/' \
    -e 's/--color-text: #1a1a1a/--color-text: #e0e0e8/' \
    -e 's/--color-muted: #6b7280/--color-muted: #9ca3af/' \
    -e 's/--color-primary: #2563eb/--color-primary: #818cf8/' \
    -e 's/--color-primary-light: #dbeafe/--color-primary-light: #1e1b4b/' \
    -e 's/--color-success: #16a34a/--color-success: #4ade80/' \
    -e 's/--color-success-light: #dcfce7/--color-success-light: #052e16/' \
    -e 's/--color-error: #dc2626/--color-error: #f87171/' \
    -e 's/--color-error-light: #fee2e2/--color-error-light: #450a0a/' \
    -e 's/--color-border: #e5e7eb/--color-border: #2a2f42/' \
    -e 's/--color-quiz-bg: #f0f4ff/--color-quiz-bg: #12151f/' \
    -e 's/--color-keypoints-bg: #fffbeb/--color-keypoints-bg: #1a1700/' \
    -e 's/--color-keypoints-border: #f59e0b/--color-keypoints-border: #d97706/' \
    -e 's/--shadow: 0 1px 3px rgba(0,0,0,0.1)/--shadow: 0 1px 3px rgba(0,0,0,0.4)/' \
    "$f"
done
```

**Note:** If guides are already dark mode (check `--color-bg` value), skip this step.

### 5. Create YAML Content Entry

Determine the next `order` number by checking existing guides:

```bash
grep '^order:' /home/smahoney/projects/seanmahoney/website/src/content/studyGuides/*.yaml | sort -t: -k3 -n | tail -1
```

Create the YAML file at `src/content/studyGuides/<slug>.yaml`:

```yaml
title: "Guide Title Here"
slug: "<slug>"
description: "One-line description of the guide content and target audience."
order: <next-number>
chapters:
  - title: "Chapter 1 Title"
    htmlFile: "chapter-01.html"
  - title: "Chapter 2 Title"
    htmlFile: "chapter-02.html"
  # ... one entry per chapter
```

### 5b. Add Textbook Companion (when `textbook.md` is present)

If the source folder contains a `textbook.md` (full-length book version of the same content, often with mermaid diagrams), deploy it alongside the study guide so it renders at `/study-guides/<slug>/textbook` and a "Read full textbook →" button appears on the study guide card.

**The slug MUST match the study guide's slug exactly** — that's the wiring between the YAML and the markdown frontmatter. If they don't match, the card won't show a textbook link.

Extract the title from the textbook's H1, prepend frontmatter, and copy the file:

```bash
slug=<slug>
src=<source-folder>/textbook.md

# Pull the H1 as the book title — strip leading '# ' and any trailing whitespace
title=$(grep -m1 '^# ' "$src" | sed 's/^# //; s/[[:space:]]*$//')

dst=/home/smahoney/projects/seanmahoney/website/src/content/textbooks/${slug}.md
{
  echo "---"
  echo "title: \"${title}\""
  echo "studyGuideSlug: \"${slug}\""
  echo "---"
  echo
  cat "$src"
} > "$dst"

# Sanity check
head -5 "$dst"
```

**Schema:** the `textbooks` content collection (`src/content/config.ts`) uses a `glob` loader against `src/content/textbooks/*.md` and validates the frontmatter `title` (string) and `studyGuideSlug` (string). The frontmatter block is required — the file will not load without it.

**Mermaid diagrams:** ` ```mermaid ` code blocks render client-side via the textbook page's mermaid bootstrap (`src/pages/study-guides/[slug]/textbook.astro`). No conversion needed; the bootstrap finds Shiki-highlighted `pre[data-language="mermaid"]` blocks and replaces them with rendered SVG using a dark theme that matches the site.

**Card wiring:** `src/pages/study-guides/index.astro` builds a Set of textbook slugs and passes `hasTextbook={true}` to `StudyGuideCard.astro` for any matching study guide. No further wiring needed once the markdown file lands in `src/content/textbooks/<slug>.md` with correct frontmatter.

**No textbook?** Skip this step entirely — the study guide card will simply omit the textbook link.

### 6. Build, Commit, Push

```bash
cd /home/smahoney/projects/seanmahoney/website

# Verify build passes — use bun, since CI runs bun install --frozen-lockfile + bun run build
# (Using npm install locally will desync package-lock.json from bun.lock and break CI.)
# If the cache is stale and a new collection looks empty, run: rm -rf .astro dist
bun run build

# Stage and commit (textbook line is a no-op when there is no textbook for this slug)
git add public/study-guides/<slug>/ src/content/studyGuides/<slug>.yaml
git add src/content/textbooks/<slug>.md 2>/dev/null || true
git commit -m "Add <Guide Title> study guide (<N> chapters, dark mode)

Co-Authored-By: Claude <model> <noreply@anthropic.com>"

# Push — Cloudflare Pages auto-deploys
git push
```

### 7. Update State File

After a successful deploy, update `/home/smahoney/seanmahoneyai/website-state.md`:

- Add the new guide to the **Current Study Guides** table (or **Current Technical Guides** if applicable)
- Update the "Last updated" date at the top
- If you deployed a textbook companion, add the slug to the textbook companions list under the Current Study Guides table (and remove it from the "Missing textbook" list if it was there)
- If you added a nav link or new collection, update those sections too

This file is the source of truth for future sessions. If you don't update it, the next agent won't know the guide exists.

### 8. Verify

The guide should appear at `https://seanmahoney.ai/study-guides` within ~60 seconds of push. If you deployed a textbook:

```bash
# Listing page should now have a "Read full textbook" link for this slug
curl -s https://seanmahoney.ai/study-guides | grep -c "Read full textbook"

# Textbook page should return 200 and have the book title in the <title> tag
curl -s -o /dev/null -w "%{http_code}\n" https://seanmahoney.ai/study-guides/<slug>/textbook
curl -s https://seanmahoney.ai/study-guides/<slug>/textbook | grep -oE '<title>[^<]+</title>'
```

**Known flaky behavior:** with many large textbook files, the CI build occasionally prerenders only a subset of textbook pages on the first attempt (a content-layer race). If a newly deployed textbook returns the homepage 404 fallback instead of its rendered content, push an empty commit (`git commit --allow-empty -m "chore: redeploy"`) to retrigger the build.

---

## Adding a Technical Guide (non-study-guide)

Technical guides use a different collection. They're single HTML files (or a directory with an index.html + sub-pages).

### For a single HTML file:
1. Copy to `public/guides/<filename>.html`
2. Create `src/content/guides/<slug>.yaml`:
```yaml
title: "Guide Title"
slug: "<slug>"
description: "Description"
htmlFile: "<filename>.html"
order: <next-number>
```

### For a multi-page guide (like the agentic architecture guide):
1. Create directory `public/guides/<slug>/`
2. Copy all HTML files into it (index.html + sub-pages)
3. Create `src/content/guides/<slug>.yaml` with `htmlFile: "<slug>/index.html"`

---

## Important: State Management

**Every change to the website MUST be followed by updating `website-state.md`.** This file is the handoff document between sessions. Future agents rely on it being accurate. If you add a guide, update a guide, add a page, change navigation, or modify any content collection — update the state file before finishing.

---

## Troubleshooting

- **Build fails:** Check `bun run build` output. Common issue: YAML syntax error (indentation, special characters need quoting)
- **CI build fails with "lockfile had changes, but lockfile is frozen":** You ran `npm install` locally and updated `package-lock.json`, but CI uses `bun install --frozen-lockfile`. Fix: run `bun install` and commit the updated `bun.lock`
- **Guide doesn't appear:** Verify the YAML is in `src/content/studyGuides/` (not `guides/`)
- **Dark mode not applied:** Check if the HTML uses CSS custom properties (`--color-bg`, etc.). If it uses hardcoded colors, manual conversion is needed
- **Chapters in wrong order:** The YAML `chapters` array order determines display order, not filenames
- **New collection appears empty after build:** Astro's content cache (`.astro/`) can go stale when adding a new collection. Run `rm -rf .astro dist` and rebuild
- **Textbook link missing from card:** Check that `studyGuideSlug` in the textbook's frontmatter exactly matches the study guide's `slug` (case-sensitive). A mismatch silently disables the card link
- **Textbook page returns the homepage (404 fallback):** Flaky CI race on large textbooks; push an empty commit to retrigger the build
