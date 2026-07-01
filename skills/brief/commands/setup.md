---
description: Create or edit a Daily-Brief profile (a role/lens with topics + sources)
---

# /brief:setup [profile-slug]

Create a new Daily-Brief **profile** — a role/lens (e.g. Realtor, AI Engineer, Parent) with
its own topics and sources — or edit an existing one.

## Process

1. **Determine the slug.** If the user passed one (`$ARGUMENTS`), use it. Otherwise ask for the
   role this profile represents and derive a dir-safe slug.

2. **Read the template + sample** for the expected format:
   - `assets/profile-template.md`
   - `assets/profile-sample.md`

3. **Interview the user** (briefly) to fill in:
   - `title` — display name.
   - `description` — one sentence describing the role/lens (this frames every "why this matters").
   - **Topics** — what subjects they want briefed.
   - For each topic: should it do open-web research (`web_search: true`)? Any specific
     **sources** (name, type: website/blog/news/youtube, URL)?
   Offer to propose sensible topics/sources for the role and let them edit.

4. **Create the profile.** Either:
   - Scaffold then edit: `brief profile create <slug> --title "..." --description "..." [--from-sample]`
     then edit `data/profiles/<slug>/reference.md` to match the interview, OR
   - Write `data/profiles/<slug>/reference.md` directly in the template format and create empty
     `history.md` + `knowledge-base.md` alongside it.

5. **Validate** the result parses: `brief profile show <slug> --json` should return a valid
   profile with the expected topics/sources.

6. Tell the user they can now run `/brief:run <slug>` or `/brief:topic "<topic>" <slug>`.

## Notes
- `youtube` sources are stored but not ingested until v2.
- Keep `description` written as "a <role> who ..." — it is the lens for framing.
