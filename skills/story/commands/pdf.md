---
name: story:pdf
description: Assemble a print-ready PDF picture book (8.5×8.5 square) from the scene images + narration script
allowed-tools:
  - Read
  - Write
  - Bash
  - Glob
  - Grep
  - Agent
---
<objective>
Produce a print-ready PDF suitable for a print shop: 8.5×8.5 inch square pages,
each scene rendered as one page with the illustration on top (aspect-preserved,
full-width) and the narration text in a cream-colored zone below in real
vector typography. Cover page with title + hero image, back page with credits.

Produces: story-output/<title-slug>-book.pdf
         story-output/print-book.html  (kept for debugging / manual reprints)
</objective>

<execution_context>
@~/.claude/story/workflows/run-stage.md
</execution_context>

<context>
Context loaded via: `node "$HOME/.claude/story/bin/story-tools.cjs" init run-stage pdf`
</context>

<process>
1. Load context:
   ```bash
   node "$HOME/.claude/story/bin/story-tools.cjs" init run-stage pdf
   ```

2. Mark stage active:
   ```bash
   node "$HOME/.claude/story/bin/story-tools.cjs" state start-stage pdf
   ```

3. Verify prerequisites:
   - `story-output/script.md` exists (from `/story:write`).
   - `story-output/images/scene-NN.png` files exist (from `/story:illustrate`).
     Missing scenes render as blank image zones — warn but continue.
   - A PDF renderer is available on PATH — any of `google-chrome`,
     `google-chrome-stable`, `chromium`, `chromium-browser`, or
     `wkhtmltopdf`. The helper picks whichever it finds first. If none is
     present, tell the user how to install one (usually
     `sudo apt install chromium-browser` or `sudo apt install wkhtmltopdf`).

4. Run the helper:
   ```bash
   node "$HOME/.claude/story/bin/make-print-pdf.cjs"
   ```
   The helper:
   - Reads story-output/script.md, outline.md, concept.md.
   - Extracts per-scene narration text (strips `[VOICE:x]` tags, joins
     paragraphs).
   - Generates story-output/print-book.html with the print layout:
     - Cover page (title + hero image, cream gradient background).
     - One page per scene (image top ~4.78", cream text zone below).
     - Back page (title + credits line).
   - Renders to PDF via headless Chrome (falls back to wkhtmltopdf).
   - Writes story-output/<title-slug>-book.pdf.

5. Verify the PDF was produced and is non-empty. Report its path and size.

6. Complete stage:
   ```bash
   node "$HOME/.claude/story/bin/story-tools.cjs" state complete-stage pdf --output story-output/
   ```

7. Report the PDF path back to the user. Do NOT auto-invoke `/story:next` —
   PDF is a leaf stage; there's nothing downstream that depends on it.
</process>

<notes>
- Trim size: 8.5×8.5 inch square. Common children's picture-book format;
  compatible with most print-on-demand shops (Lulu, IngramSpark, Bookmundo,
  etc.). If the shop requires a different trim, regenerate scene images at
  the target aspect ratio and re-run this stage.
- Print DPI: scene images at 1920×1080 map to ~226 DPI on an 8.5" page —
  acceptable for home / small-run print, marginally below the 300 DPI bar
  for premium print. For studio quality, regenerate images at 2550×2550
  and update the illustrate stage's target resolution.
- Text rendering: all narration text is real vector typography (via CSS in
  the intermediate HTML). No AI-generated text on the printed page — no
  misspelling risk. Font is Charter/Georgia (system serif); embedded by
  Chrome at PDF creation time.
- Layout math: 8.5in × 9/16 = 4.78in image height (top). Text zone = 3.72in
  (bottom). Padding 0.32in top / 0.55in horizontal / 0.4in bottom.
- Cost: $0 — no additional API calls. Just page layout on artifacts you
  already generated.
- The intermediate HTML at `story-output/print-book.html` is kept for
  debugging (view in a browser to preview) and manual re-rendering if the
  PDF renderer needs a different pass.
</notes>
