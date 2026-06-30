---
name: sws:start
description: Start a new StudyWS learning pipeline
argument-hint: "[topic]"
allowed-tools:
  - Read
  - Write
  - Bash
  - Glob
  - Grep
  - AskUserQuestion
  - Agent
  - Skill
---
<objective>
Initialize a new SWS learning pipeline. Collects topic and learning style preferences,
creates the output directory, writes config.json, then auto-invokes /sws:scope.

Produces: output/{topic-slug}/config.json
</objective>

<execution_context>
@~/.claude/sws/references/pipeline-stages.md
@~/.claude/sws/templates/quiz-schema.json
</execution_context>

<context>
Arguments: $ARGUMENTS

Check for existing topics:
```bash
node "$HOME/.claude/sws/bin/sws-tools.cjs" status
```
</context>

<process>
1. **Check Perplexity MCP is configured**:
   - Read `~/.claude/settings.json` and check for `mcpServers.perplexity`
   - If NOT configured, tell the user:
     "Perplexity API key not configured. Run `sws setup` in your terminal first."
   - Do NOT proceed until configured — the research stage will fail without it.

2. **Check for existing topics**:
   ```bash
   node "$HOME/.claude/sws/bin/sws-tools.cjs" status
   ```
   - If topics exist, show their status and ask: "Start a new topic or continue an existing one?"
   - If continuing existing → run `/sws:status` and suggest the next pipeline command to run
   - If starting new → continue below

3. **Collect topic**:
   - If topic passed as argument (`$ARGUMENTS`), use it directly
   - Otherwise ask via AskUserQuestion: "What topic do you want to learn?"
   - Examples to offer: "AWS Solutions Architect exam", "Kubernetes networking", "Rust ownership model"

4. **Generate slug** from topic:
   - Lowercase, replace spaces and special chars with hyphens
   - Remove consecutive hyphens, trim leading/trailing hyphens
   - Example: "AWS Solutions Architect Exam" → "aws-solutions-architect-exam"

5. **Collect learning style preferences** via AskUserQuestion:

   Question 1 — "How deep should the textbook go?"
   - Overview (8-10 chapters, broad strokes)
   - Standard (10-12 chapters, solid coverage) (Recommended)
   - Comprehensive (12-14 chapters, deep dive into every sub-topic)

   Question 2 — "What learning aids do you prefer?" (multi-select)
   - Worked examples (step-by-step walkthroughs)
   - Real-world analogies (connect concepts to familiar things)
   - Heavy use of tables and diagrams
   - Text-focused (minimal visual elements)

6. **Map selections to config values**:
   - depth: "overview" | "standard" | "comprehensive"
   - examples: true if "Worked examples" selected
   - analogies: true if "Real-world analogies" selected
   - visual_emphasis: "tables-diagrams" if diagrams selected, "text-heavy" if text-focused selected, "balanced" otherwise

7. **Create output directory**:
   ```bash
   node "$HOME/.claude/sws/bin/sws-tools.cjs" init {slug}
   ```

8. **Write config.json** to `output/{slug}/config.json`:
   ```json
   {
     "topic": "{user's exact topic text}",
     "slug": "{generated-slug}",
     "learning_style": {
       "depth": "{depth}",
       "examples": true/false,
       "analogies": true/false,
       "visual_emphasis": "{visual_emphasis}"
     },
     "created_at": "{ISO 8601 timestamp}",
     "pipeline_stage": "scoped:false"
   }
   ```

9. **Confirm to user**: "Created learning pipeline for **{topic}**. Starting scoping session..."

10. **Auto-invoke `/sws:scope`** — IMMEDIATELY invoke via Skill tool. Do NOT just tell the user to run it.
</process>
