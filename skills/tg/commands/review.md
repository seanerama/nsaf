---
name: tg:review
description: On-demand Opus 4 coherence review of the full textbook
allowed-tools:
  - Read
  - Write
  - Bash
  - Glob
---
<objective>
On-demand quality review: read the full textbook and produce an advisory
review report covering coherence, terminology, gaps, citations, and
difficulty progression. Does NOT auto-modify chapters.

Produces: output/{topic-slug}/review-report.md
</objective>

<execution_context>
@~/.claude/tg/prompts/review.md
@~/.claude/tg/references/pipeline-stages.md
</execution_context>

<context>
```bash
node "$HOME/.claude/tg/bin/sws-tools.cjs" active-topic
```
</context>

<process>
1. **Find active topic** and verify chapters exist:
   ```bash
   node "$HOME/.claude/tg/bin/sws-tools.cjs" active-topic
   node "$HOME/.claude/tg/bin/sws-tools.cjs" status {slug}
   ```
   - If no chapters written, tell user to run the pipeline first

2. **Read outline.json** for the intended structure and objectives

3. **Read all chapter files** from chapters/ (or textbook.md if available)
   - Note total chapter count and approximate word count

4. **Perform thorough review** across these dimensions:

   ### A. Cross-Chapter Coherence
   - Are concepts introduced before they're referenced in later chapters?
   - Does the textbook build knowledge progressively?
   - Are there abrupt jumps in assumed knowledge?

   ### B. Terminology Consistency
   - Is the same concept called the same thing everywhere?
   - Are abbreviations introduced before use?
   - Build a table of any inconsistencies found

   ### C. Coverage Gaps
   - Compare outline.json learning objectives against actual content
   - Are there topics mentioned but never fully explained?
   - Are there key terms from the outline missing from the text?

   ### D. Citation Quality
   - Are citations present throughout (not clustered at start or end)?
   - Are there chapters with suspiciously few citations?
   - Are citation URLs formatted consistently?

   ### E. Difficulty Progression
   - Does Chapter 1 assume no prior knowledge?
   - Does complexity increase gradually?
   - Are advanced chapters building on earlier foundations?

   ### F. Learning Objectives Coverage
   - For each chapter, check: are all stated objectives addressed?
   - Flag any objectives that appear unaddressed

5. **Write review-report.md**:

   ```markdown
   # Review Report: {Textbook Title}

   **Reviewed:** {timestamp}
   **Chapters reviewed:** {count}
   **Estimated word count:** {estimate}

   ## Overall Assessment

   {2-3 paragraphs: overall quality, strongest chapters, weakest chapters,
   readiness for use as study material}

   ## Cross-Chapter Issues

   ### Terminology Inconsistencies
   | Term in Chapter X | Term in Chapter Y | Suggested Standard |
   |-------------------|-------------------|--------------------|
   | {example}         | {example}         | {recommendation}   |

   ### Forward References (concept used before introduced)
   | Chapter | Section | References | Should Come After |
   |---------|---------|-----------|-------------------|
   | {ch}    | {sec}   | {concept} | {ch where introduced} |

   ### Coverage Gaps
   - {Topic mentioned but never fully explained}
   - {Learning objective not addressed}

   ## Per-Chapter Notes

   ### Chapter 1: {Title}
   - **Strengths:** {what works well}
   - **Issues:** {what needs improvement}
   - **Suggested edits:** {specific, actionable suggestions}
   - **Objectives covered:** {yes/no per objective}

   ### Chapter 2: {Title}
   ...

   ## Citation Quality

   | Chapter | Citation Count | Assessment |
   |---------|---------------|------------|
   | Ch. 1   | {n}           | {adequate/sparse/good} |
   | Ch. 2   | {n}           | {assessment} |

   ## Difficulty Progression

   {Assessment of the learning curve — does it build appropriately?}
   {Flag any chapters that seem out of order or assume too much}

   ## Recommended Actions (Priority Order)

   1. **{Highest priority}** — {why and what to do}
   2. **{Next priority}** — {why and what to do}
   3. ...
   ```

6. **Report is advisory** — explicitly state: "This report is advisory. No chapters were modified."

7. **Display key findings** to the user:
   - Number of issues found per category
   - Top 3 recommended actions
   - Overall readiness assessment
</process>
