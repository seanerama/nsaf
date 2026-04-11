# Animation Strategy for Study Guides

When generating interactive HTML study guides, replace static diagrams and placeholder hooks with self-contained SVG/CSS animations. Every animation must be inline — no external dependencies, no CDN links.

## Requirements for Every Animation

- Self-contained HTML with inline SVG, CSS @keyframes, and optional vanilla JS
- Dark background, blue accent colors (match study guide theme)
- Height under 500px (designed for scroll context)
- Include a "Replay" button — no auto-loop
- Trigger on scroll-into-view using Intersection Observer API
- CSS-only fallback: diagrams readable if JS is blocked
- Consistent timing: 0.4s per step, 0.6s for major transitions, 0.15s stagger

## What to Animate

- **Data flow diagrams** — animated arrows between components, sequential highlighting
- **Architecture diagrams** — layered component diagrams with reveal animations
- **Process flows** — step-by-step sequences with highlights
- **Timelines** — RPO/RTO, schedules, lifecycle diagrams
- **Network topologies** — packet flow, replication paths
- **Algorithms** — sorting, traversal, encryption steps
- **State machines** — protocol states, failover sequences

## How to Generate

Use inline SVG with CSS @keyframes animations. Structure:
1. Draw all components as SVG groups
2. Add CSS @keyframes for movement, opacity, glow effects
3. Use animation-delay for sequential triggering
4. Add hover tooltips on components explaining their role
5. Include Replay button that resets all animations

## Per-Chapter Animation Targets

For each chapter in a study guide, identify 2-3 concepts that benefit from animation:
- Main architecture/topology → animated component diagram
- Key process/workflow → step-by-step flow animation
- Data movement/transformation → animated arrows with highlights

## Shared Best Practices

- **Keep animations self-contained.** Always inline CSS, no CDN links.
- **Add a replay button.** Educational animations loop on demand, not auto-loop.
- **Design for scroll context.** Height under 500px, trigger on scroll-into-view.
- **Consistent timing.** 0.4s per step, 0.6s for major transitions, 0.15s stagger.
- **CSS-only fallback.** SVG `<animate>` and CSS `@keyframes` work without JS.
