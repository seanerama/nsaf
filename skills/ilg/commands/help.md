---
name: ilg:help
description: Show all interactive-learning-guide commands and usage
allowed-tools:
  - Read
  - Bash
---
<objective>
Display all available interactive-learning-guide commands with descriptions and usage examples.
</objective>

<process>
1. Display formatted help:

   ## Interactive Learning Guide Commands

   ### Getting Started
   | Command | Description |
   |---------|-------------|
   | `/ilg:start` | Choose a workflow and begin |
   | `/ilg:status` | Show current pipeline state (chunked workflow) |
   | `/ilg:help` | This help page |

   ### Workflows
   | Command | Description |
   |---------|-------------|
   | `/ilg:book` | Process a book (PDF/EPUB) — auto-chunks long books |
   | `/ilg:multiformat` | Process slides, transcripts, data sheets, or install guides |

   ### Manual Chunked Pipeline (Advanced)
   | Command | Description |
   |---------|-------------|
   | `/ilg:init` | Initialize pipeline — read preface + Chapter 1, create relay files |
   | `/ilg:chapter` | Process the next chapter — append to relay files |
   | `/ilg:build` | Final build — compile relay files into interactive HTML |

   ### Usage

   **Books (any length):**
   1. Upload a PDF/EPUB
   2. Run `/ilg:book`
   3. Download the generated HTML file
   (Long books are automatically chunked and processed chapter by chapter)

   **Other content:**
   1. Upload slides, transcripts, data sheets, or install guides
   2. Run `/ilg:multiformat`
   3. Download the generated HTML file

   ### Tips
   - Add `--focus "topic"` to give extra depth to a specific area
   - Add `--difficulty foundational|intermediate|advanced` to bias quiz difficulty
   - Add `--chapters 3-7` to scope to specific chapters
   - Add `--quiz-depth 10` to increase questions per chapter (default: 5)
</process>
