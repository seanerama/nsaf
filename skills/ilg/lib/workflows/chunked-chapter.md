# Chunked Pipeline: Chapter Processing Workflow

You are a chapter processing agent in a multi-session learning guide pipeline. Previous sessions have already processed earlier chapters. Your job is to read ONE specific chapter, extract structured learning data, and append it to the existing relay files.

**IMPORTANT:** Do NOT read any other chapters. Use summary.md to understand what came before. Use progress.md to locate the page range for your assigned chapter.

## Inputs
You should have:
1. The full book (PDF or EPUB) — read ONLY your assigned chapter
2. `summary.md` — running summary of all previously processed chapters
3. `learning-data.json` — structured data from previous chapters
4. `progress.md` — chapter index with page ranges and processing status

## Tasks

### 1. Orient Yourself
- Read `progress.md` to find the page range for your assigned chapter
- Read `summary.md` to understand the narrative and key concepts so far
- Skim the existing concepts and terms in `learning-data.json` so you can:
  - Link new concepts to existing ones
  - Avoid duplicating glossary entries
  - Build cross-chapter relationships
- You do NOT need to read previous chapters — the relay files contain everything you need

### 2. Read and Analyze Your Chapter
- Navigate to your assigned chapter in the uploaded book
- Read it thoroughly, start to finish
- Identify new concepts, terms, and ideas
- Note how this chapter builds on, challenges, or extends concepts described in summary.md
- Look for cross-cutting themes that connect to earlier material

### 3. Update: summary.md
Append a new section to the END of summary.md. Do NOT modify any existing sections.

```markdown

---

## Chapter [N]: [Chapter Title]

### Key Ideas
- [Bullet list of the 3-7 most important ideas]

### How It Connects
[How this chapter builds on previous chapters — reference specific earlier concepts by name]

### Critical Context for Later Chapters
[Anything a future session MUST know. If nothing critical, write "No special context needed."]
```

### 4. Update: learning-data.json
Append new entries to the existing JSON arrays. Follow these rules strictly:

**ID Conventions:**
- Concept IDs: `c[chapter]-[number]` → e.g., `c3-001`, `c3-002`
- Quiz IDs: `q[chapter]-[number]` → e.g., `q3-001`, `q3-002`
- Term IDs: `t[chapter]-[number]` → e.g., `t3-001`, `t3-002`

**What to append:**
- New chapter object to the `chapters` array
- New concepts to the `concepts` array
- New relationships to the `relationships` array — **especially cross-chapter links**
- New quiz questions to the `quizQuestions` array
- New glossary terms to the `glossaryTerms` array

**Critical rules:**
- Do NOT modify or delete any existing entries
- Do NOT change existing IDs
- Cross-chapter relationships are the most valuable — when a new concept connects to a previous one, create a relationship entry linking their IDs
- Check existing glossary terms before adding — if already present, don't duplicate (but add a relationship)

### 5. Update: progress.md
- Change your chapter's checkbox from `[ ]` to `[x]`
- Add any processing notes that would help the next session

### 6. Extraction Targets
- **Concepts:** 5-15 meaningful concepts
- **Relationships:** Include at least 2-3 cross-chapter connections
- **Quiz questions:** At least 5, spread across difficulty levels. Include at least 1 that tests integration with earlier chapters
- **Glossary terms:** Every new domain-specific or author-defined term

### 7. Quality Checks Before Finishing
Verify:
- [ ] New concept IDs follow `c[chapter]-[number]` format and are unique
- [ ] Cross-chapter relationships reference valid existing concept IDs
- [ ] Quiz questions have unambiguous correct answers
- [ ] No duplicate glossary terms
- [ ] JSON is valid (no trailing commas, proper brackets)
- [ ] summary.md reads coherently with previous entries
- [ ] progress.md is updated
- [ ] You did NOT process content from any other chapter

### 8. Output
Save all three updated files. Report:
- Which chapter was processed
- How many new concepts, questions, and terms were added
- Key cross-chapter connections discovered
- Which chapter to process next (or if done, suggest `/ilg:build`)
