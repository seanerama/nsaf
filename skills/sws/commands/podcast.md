---
name: sws:podcast
description: Generate a podcast prompt from slides and textbook content
allowed-tools:
  - Read
  - Write
  - Bash
  - Glob
---
<objective>
Generate a podcast prompt that can be fed to an audio generation agent or TTS service
to create an audio lesson about the topic.

Produces: output/{topic-slug}/podcast-prompt.md
</objective>

<execution_context>
@~/.claude/sws/prompts/podcast.md
@~/.claude/sws/references/pipeline-stages.md
</execution_context>

<context>
```bash
node "$HOME/.claude/sws/bin/sws-tools.cjs" active-topic
```
</context>

<process>
1. **Find active topic** and verify slides.md exists

2. **Read slides.md**, **textbook.md**, and **outline.json**

3. **Load podcast prompt** from ~/.claude/sws/prompts/podcast.md

4. **Generate podcast-prompt.md** in a single pass:

   ```markdown
   # Podcast Prompt: {Textbook Title}

   ## Metadata
   - **Topic:** {topic}
   - **Source Material:** {textbook title} ({N} chapters)
   - **Target Length:** {estimated total minutes} minutes
   - **Tone:** Conversational but authoritative — like a knowledgeable friend explaining over coffee
   - **Audience:** Someone curious about {topic} with no prior expertise
   - **Format:** Solo narrator educational podcast

   ## Production Notes
   - Reference the accompanying slide deck for visual structure
   - Use natural speech patterns — contractions, rhetorical questions, brief pauses
   - Include "let me give you an example" transitions before examples
   - Summarize key points before moving to next segment

   ---

   ## Opening (2-3 minutes)

   **Hook:** {An interesting fact, question, or scenario that draws the listener in}

   **Introduction:**
   {What this episode covers — frame the topic's importance}
   {Why the listener should care — real-world relevance}
   {Roadmap — brief overview of what segments are coming}

   ---

   ## Segment 1: {Chapter 1 Title} ({estimated minutes} min)

   **Key Points to Cover:**
   1. {Main concept 1 — with specific facts from the textbook}
   2. {Main concept 2}
   3. {Main concept 3}

   **Example to Use:**
   {Specific example or analogy from the chapter — quote the key passage}

   **Emphasis:**
   {What to stress — common misconceptions to address}

   **Transition to Segment 2:**
   "{Natural bridging sentence that connects this chapter's conclusion to the next topic}"

   ---

   ## Segment 2: {Chapter 2 Title} ({estimated minutes} min)
   ...

   {Continue for all chapters}

   ---

   ## Closing (2-3 minutes)

   **Recap:**
   {3-5 key takeaways from the entire topic — the "if you remember nothing else" points}

   **Call to Action:**
   {What the listener should do next — study guide, further reading, practice exercises}

   **Sign-off:**
   {Natural closing statement}
   ```

   TIMING GUIDELINES:
   - Opening: 2-3 minutes
   - Per chapter segment: 3-5 minutes (scale with chapter complexity)
   - Closing: 2-3 minutes
   - Total: roughly 3-4 minutes per chapter + 5 minutes framing

5. **Write podcast-prompt.md** to output/{slug}/

6. **Update config.json** — set pipeline_stage to "podcast:true"

7. **Announce pipeline complete**:
   ```
   ## Pipeline Complete!

   All learning materials generated for: {topic}

   **Output files in output/{slug}/:**
   - textbook.md — Full textbook ({N} chapters)
   - guides/ — {N} interactive HTML study guides
   - slides.md — Slide deck descriptions ({N} slides)
   - podcast-prompt.md — Podcast generation prompt

   **Next steps:**
   - Open any guides/*.html in a browser to start studying
   - Run /sws:review for an Opus 4 quality assessment
   - Use slides.md with a deck-creation agent to build a presentation
   - Use podcast-prompt.md with a TTS/audio agent to generate audio
   ```
</process>
