# Run Stage Workflow

Generic wrapper for executing any Story Maker pipeline stage.

## Pre-Execution

1. **Load context** via `story-tools init run-stage <stage-id>`
   - Returns: `can_run`, `missing_deps`, `expected_outputs`, `existing_outputs`, `config`

2. **Dependency check**:
   - If `can_run: false` → Report missing dependencies, suggest the correct command to run first
   - If `already_complete: true` → This is a re-run. Load previous outputs for context

3. **Mark stage active**: `story-tools state start-stage <stage-id>`

## Execution

4. **Load existing outputs** from completed dependencies:
   - Read files listed in `existing_outputs` for context
   - These inform the current stage's work

5. **Execute the stage-specific workflow**:
   - Follow the `<process>` section from the command file
   - The stage instructions guide the actual work

6. **Produce outputs**:
   - Write expected output files to their designated paths
   - Validate outputs exist before marking complete

## Post-Execution

7. **Complete stage**: `story-tools state complete-stage <stage-id> --output <path>`
   - Marks checklist item as [x] in STATE.md
   - Records outputs in the Outputs table

8. **Check next steps**: `story-tools graph next`
   - Parse the output to determine available next stages

9. **Auto-continue the workflow**:
   - If exactly **1 next stage** is available → Immediately invoke it via `/story:<command>`
   - If **multiple stages** are available (parallel) → Tell the user and ask which to start, or start both if possible
   - If **no stages** remain → Announce "Story complete!" with final output summary
   - IMPORTANT: Always auto-invoke. The user should not have to manually type the next command.
