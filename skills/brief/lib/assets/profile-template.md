# Profile Reference Template

Fill this in to define a Daily-Brief **profile** — a role/lens through which news is briefed.
Save the result as `data/profiles/<slug>/reference.md` (or use `brief profile create`).

```markdown
---
slug: <dir-safe-slug>          # e.g. realtor, ai-engineer, parent
title: <Display Name>          # e.g. Realtor
description: <one sentence describing the role/lens>   # used to frame "why this matters"
---

## Topics

### <Topic name>
- web_search: true|false       # also do open-web (Perplexity) research for this topic?
- source: <Name> (<type>) <url optional>
- source: <Name> (<type>) <url optional>

### <Another topic>
- web_search: true
```

**Source `type` values:** `website`, `blog`, `news`, `web-search`, `youtube`
(`youtube` is stored but not ingested until v2.)

**Tips**
- A topic with `web_search: true` and no sources = pure open-web research.
- A topic with sources and `web_search: false` = only check those predetermined sources.
- The `description` is the lens: write it as "a <role> who <cares about / does> ...".
- See `assets/profile-sample.md` for a complete example.
