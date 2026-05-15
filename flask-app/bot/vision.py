"""Vision intake — turn raw ideas into structured vision docs via Claude + Resend."""

import base64
import json
import logging
import os
import re

import requests
from anthropic import Anthropic

log = logging.getLogger(__name__)


SYSTEM_PROMPT = """You help refine raw, half-formed ideas into structured vision documents.
Each idea will be built as one of three NSAF project kinds:

- **story** — an illustrated audio story for children (3–6 scenes, narration, images)
- **studyws** — an interactive learning package on a topic (textbook chapters, study guides, slides, podcast)
- **app** — a web application that solves a problem (Flask/Next.js/etc., deployed locally)

Your job, given the user's raw idea text:
1. Echo back a 1–2 sentence interpretation that captures what you think they're really after.
2. Classify the best-fit kind (story / studyws / app / unclear).
3. Draft a vision markdown document the user can refine asynchronously by editing and re-uploading.

The vision doc must follow this exact structure:

```
# <Working Title>

## Idea
<2–4 sentence expanded restatement of the idea, including the angle/insight you hear>

## Why This Matters
<1–2 sentences on the underlying need, audience, or hook>

## Proposed Kind
<one of: story | studyws | app>

## Key Aspects
- <aspect 1>
- <aspect 2>
- <aspect 3>
- <…>

## Open Questions
1. <question that, once answered, would unblock the build>
2. <…>
3. <…>
4. <…>
5. <…>

## Your Answers
<leave this section blank — the user fills it in before re-uploading>

## Build Notes
<any hints, constraints, or stylistic preferences the bot should respect when building>
```

Respond with ONLY a JSON object — no surrounding prose, no code fences. Schema:
{
  "interpretation": "<1–2 sentence echo>",
  "proposed_kind": "story|studyws|app|unclear",
  "title": "<short working title>",
  "vision_md": "<the full markdown doc per the template above>"
}"""


def expand_idea(raw_text):
    """Call Claude to expand a raw idea into an interpretation + vision doc.

    Returns dict: {interpretation, proposed_kind, title, vision_md} on success,
    or raises on failure (caller should catch and surface error to user).
    """
    client = Anthropic()
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4000,
        temperature=0.7,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": raw_text}],
    )
    text = response.content[0].text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1]
        text = text.rsplit("```", 1)[0].strip()

    data = json.loads(text)
    for required in ("interpretation", "proposed_kind", "title", "vision_md"):
        if required not in data:
            raise ValueError(f"Claude response missing required field: {required}")
    return data


def _md_to_html(md):
    """Minimal markdown → HTML so emails are readable in clients that ignore text/plain."""
    lines = md.split("\n")
    out = []
    in_ul = False
    in_ol = False
    for raw in lines:
        line = raw.rstrip()
        if not line.strip():
            if in_ul:
                out.append("</ul>"); in_ul = False
            if in_ol:
                out.append("</ol>"); in_ol = False
            out.append("")
            continue
        h = re.match(r"^(#{1,6})\s+(.+)$", line)
        if h:
            if in_ul: out.append("</ul>"); in_ul = False
            if in_ol: out.append("</ol>"); in_ol = False
            level = len(h.group(1))
            out.append(f"<h{level}>{h.group(2)}</h{level}>")
            continue
        if re.match(r"^- ", line):
            if not in_ul:
                if in_ol: out.append("</ol>"); in_ol = False
                out.append("<ul>"); in_ul = True
            out.append(f"<li>{line[2:]}</li>")
            continue
        if re.match(r"^\d+\.\s+", line):
            if not in_ol:
                if in_ul: out.append("</ul>"); in_ul = False
                out.append("<ol>"); in_ol = True
            out.append(f"<li>{re.sub(r'^\d+\.\s+', '', line)}</li>")
            continue
        if in_ul: out.append("</ul>"); in_ul = False
        if in_ol: out.append("</ol>"); in_ol = False
        out.append(f"<p>{line}</p>")
    if in_ul: out.append("</ul>")
    if in_ol: out.append("</ol>")
    return "\n".join(out)


def send_vision_email(slug, title, raw_idea, vision_md, to_email=None):
    """Email the vision doc to the user via Resend.

    Sends both an HTML body and the .md as an attachment so the user can edit
    and re-upload it to Webex.
    """
    api_key = os.environ.get("RESEND_API_KEY")
    if to_email is None:
        to_email = os.environ.get("NSAF_OWNER_EMAIL")

    if not api_key or not to_email:
        log.error("Missing RESEND_API_KEY or NSAF_OWNER_EMAIL")
        return False, "Email transport not configured (RESEND_API_KEY / NSAF_OWNER_EMAIL)."

    body_html = _md_to_html(vision_md)
    intro = (
        f"<p>Hi — here's the draft vision doc for your idea (<code>{slug}</code>).</p>"
        f"<p>The .md is attached. Open it, fill in the <b>Your Answers</b> section, then "
        f"upload it back to the NSAF Webex bot with: <code>vision {slug}</code> "
        f"(attach the edited file with that message).</p>"
        f"<p>Your raw idea, for reference:</p>"
        f"<blockquote style='border-left:3px solid #ccc;padding-left:10px;color:#555'>"
        f"{raw_idea}</blockquote><hr>"
    )

    md_b64 = base64.b64encode(vision_md.encode("utf-8")).decode("ascii")

    try:
        response = requests.post(
            "https://api.resend.com/emails",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "from": "NSAF <nsaf@resend.dev>",
                "to": [to_email],
                "subject": f"NSAF Vision: {title} [{slug}]",
                "html": f"<html><body style='font-family:sans-serif;max-width:780px;margin:0 auto;padding:20px'>{intro}{body_html}</body></html>",
                "text": f"Vision doc for {slug}. Edit the attached .md and reply via Webex with: vision {slug}\n\n---\n\n{vision_md}",
                "attachments": [
                    {"filename": f"vision-{slug}.md", "content": md_b64}
                ],
            },
            timeout=30,
        )
        response.raise_for_status()
        log.info(f"Vision email sent for {slug} to {to_email}")
        return True, to_email
    except Exception as e:
        log.error(f"Failed to send vision email for {slug}: {e}")
        return False, str(e)
