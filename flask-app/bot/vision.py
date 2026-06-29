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
- **techguide** — a self-contained technical guide for seanmahoney.ai/guides: a single-concept explainer, a product comparison, OR a multi-section interactive guide. Pick this for one-off web content, NOT for a multi-chapter learning track.
- **app** — a web application that solves a problem (Flask/Next.js/etc., deployed locally)

Given the user's raw idea text:
1. Echo back a 1–2 sentence interpretation that captures what you think they're really after.
2. Classify the best-fit kind (story / studyws / techguide / app / unclear).
   Disambiguation: prefer `techguide` for a single self-contained piece of web content (explainer / product comparison / interactive guide). Prefer `studyws` for a multi-chapter learning track or exam prep. Prefer `story` for a children's illustrated audio story. Prefer `app` for a deployable interactive web application.
3. Produce a short working title and a vision markdown document the user can refine
   asynchronously by editing and re-uploading.

The vision_md document must follow this exact structure:

# <Working Title>

## Idea
<2–4 sentence expanded restatement of the idea, including the angle/insight you hear>

## Why This Matters
<1–2 sentences on the underlying need, audience, or hook>

## Proposed Kind
<one of: story | studyws | techguide | app>

## Key Aspects
- <aspect 1>
- <aspect 2>
- <aspect 3>

## Open Questions
1. <question that, once answered, would unblock the build>
2. <...>
3. <...>
4. <...>
5. <...>

## Your Answers
<leave this section blank — the user fills it in before re-uploading>

## Build Notes
<any hints, constraints, or stylistic preferences the bot should respect when building>

Always submit your response by calling the submit_vision tool — do not write
markdown directly in the message body."""


SUBMIT_VISION_TOOL = {
    "name": "submit_vision",
    "description": "Submit the expanded interpretation, proposed kind, working title, and full vision markdown document.",
    "input_schema": {
        "type": "object",
        "properties": {
            "interpretation": {
                "type": "string",
                "description": "1-2 sentence echo of what the user is really after.",
            },
            "proposed_kind": {
                "type": "string",
                "enum": ["story", "studyws", "techguide", "app", "unclear"],
                "description": "Best-fit NSAF project kind.",
            },
            "title": {
                "type": "string",
                "description": "Short working title (used to derive the session slug).",
            },
            "vision_md": {
                "type": "string",
                "description": "The full vision markdown document following the prescribed structure.",
            },
        },
        "required": ["interpretation", "proposed_kind", "title", "vision_md"],
    },
}


def expand_idea(raw_text):
    """Call Claude to expand a raw idea into an interpretation + vision doc.

    Returns dict: {interpretation, proposed_kind, title, vision_md}.
    Uses tool_use for reliable structured output.
    """
    client = Anthropic()
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4000,
        temperature=0.7,
        system=SYSTEM_PROMPT,
        tools=[SUBMIT_VISION_TOOL],
        tool_choice={"type": "tool", "name": "submit_vision"},
        messages=[{"role": "user", "content": raw_text}],
    )
    for block in response.content:
        if getattr(block, "type", None) == "tool_use":
            data = dict(block.input)
            for required in ("interpretation", "proposed_kind", "title", "vision_md"):
                if required not in data:
                    raise ValueError(f"Tool output missing required field: {required}")
            return data
    raise ValueError("Claude did not invoke submit_vision; got: "
                     f"{getattr(response.content[0], 'text', '')[:200]}")


REVIEW_SYSTEM_PROMPT = """You are reviewing a user's answers to questions inside a
NSAF vision document. The document has these sections you care about:

- `## Open Questions` — numbered questions the bot drafted for the user
- `## Your Answers` — the user's responses, numbered to match the questions

For each answered question, classify the answer as one of:
- "clear" — direct, unambiguous, and answers the question
- "ambiguous" — partial, hedged, conditional, or expresses uncertainty
- "asked_back" — the user asked a clarifying question instead of answering, or commented that the question itself wasn't clear
- "missing" — no answer for that question number

Where answers are ambiguous, asked_back, or missing, propose **follow-up questions** that
would unblock a clear answer. Phrase follow-ups so they could be answered in 1-2 sentences.

If the original questions themselves don't fit the direction the user's answers are taking
(e.g. user clearly wants a different scope, audience, or kind), propose a **revised set**
of questions. Only do this when warranted — usually follow-ups are enough.

Call submit_review with the structured result."""


SUBMIT_REVIEW_TOOL = {
    "name": "submit_review",
    "description": "Submit the structured review of the user's answers.",
    "input_schema": {
        "type": "object",
        "properties": {
            "verdict": {
                "type": "string",
                "enum": ["ready_to_build", "needs_clarification", "questions_need_revision"],
                "description": "Overall verdict on whether the vision is ready to build.",
            },
            "summary": {
                "type": "string",
                "description": "1-2 sentence plain-language summary of the review.",
            },
            "answer_reviews": {
                "type": "array",
                "description": "One entry per question that has an answer (or should have one).",
                "items": {
                    "type": "object",
                    "properties": {
                        "question_number": {"type": "integer"},
                        "status": {
                            "type": "string",
                            "enum": ["clear", "ambiguous", "asked_back", "missing"],
                        },
                        "comment": {
                            "type": "string",
                            "description": "Short note explaining the classification. For ambiguous/asked_back, say what's unclear.",
                        },
                    },
                    "required": ["question_number", "status", "comment"],
                },
            },
            "followup_questions": {
                "type": "array",
                "description": "New questions to append to Open Questions. No numbering — caller adds it.",
                "items": {"type": "string"},
            },
            "revised_questions": {
                "type": "array",
                "description": "If the original question set needs rewriting, the full replacement. Otherwise empty.",
                "items": {"type": "string"},
            },
        },
        "required": ["verdict", "summary", "answer_reviews"],
    },
}


def review_answers(vision_md):
    """Have Claude review the answers in a vision doc.

    Returns dict: {verdict, summary, answer_reviews, followup_questions, revised_questions}.
    Last two may be empty lists.
    """
    client = Anthropic()
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=3000,
        temperature=0.4,
        system=REVIEW_SYSTEM_PROMPT,
        tools=[SUBMIT_REVIEW_TOOL],
        tool_choice={"type": "tool", "name": "submit_review"},
        messages=[{"role": "user", "content": vision_md}],
    )
    for block in response.content:
        if getattr(block, "type", None) == "tool_use":
            data = dict(block.input)
            data.setdefault("followup_questions", [])
            data.setdefault("revised_questions", [])
            data.setdefault("answer_reviews", [])
            for required in ("verdict", "summary"):
                if required not in data:
                    raise ValueError(f"Tool output missing required field: {required}")
            return data
    raise ValueError("Claude did not invoke submit_review; got: "
                     f"{getattr(response.content[0], 'text', '')[:200]}")


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
