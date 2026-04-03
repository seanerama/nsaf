"""Morning email formatting and sending via Resend."""

import json
import logging
import os

import requests

log = logging.getLogger(__name__)


def format_ideas_html(ideas, selection_url):
    """Format 30 ideas into an HTML email grouped by provider."""
    providers = {"openai": [], "gemini": [], "anthropic": []}
    for idea in ideas:
        source = idea.get("source", "unknown")
        if source in providers:
            providers[source].append(idea)

    provider_labels = {
        "openai": "OpenAI",
        "gemini": "Gemini",
        "anthropic": "Anthropic",
    }

    sections = []
    for source, label in provider_labels.items():
        group = providers.get(source, [])
        if not group:
            continue
        rows = ""
        for idea in sorted(group, key=lambda x: x.get("rank", 0)):
            stack = idea.get("suggested_stack", {})
            if isinstance(stack, str):
                try:
                    stack = json.loads(stack)
                except (json.JSONDecodeError, TypeError):
                    stack = {}
            stack_str = ", ".join(f"{v}" for v in stack.values()) if stack else "—"
            rows += f"""
            <tr>
                <td style="padding:8px;border-bottom:1px solid #eee"><strong>{idea['name']}</strong></td>
                <td style="padding:8px;border-bottom:1px solid #eee">{idea['description']}</td>
                <td style="padding:8px;border-bottom:1px solid #eee">{idea.get('category', '—')}</td>
                <td style="padding:8px;border-bottom:1px solid #eee">{idea.get('complexity', '—')}</td>
                <td style="padding:8px;border-bottom:1px solid #eee;font-size:12px">{stack_str}</td>
            </tr>"""

        sections.append(f"""
        <h2 style="color:#333;border-bottom:2px solid #007bff;padding-bottom:4px">{label} ({len(group)} ideas)</h2>
        <table style="width:100%;border-collapse:collapse;margin-bottom:20px">
            <tr style="background:#f5f5f5">
                <th style="padding:8px;text-align:left">Name</th>
                <th style="padding:8px;text-align:left">Description</th>
                <th style="padding:8px;text-align:left">Category</th>
                <th style="padding:8px;text-align:left">Complexity</th>
                <th style="padding:8px;text-align:left">Stack</th>
            </tr>
            {rows}
        </table>""")

    body = "\n".join(sections)
    banner_url = "https://raw.githubusercontent.com/seanerama/nsaf/master/nsaf-banner-image.jpg"
    return f"""
    <html>
    <body style="font-family:sans-serif;max-width:900px;margin:0 auto;padding:20px">
        <img src="{banner_url}" alt="Nightshift AutoFoundry" style="width:100%;max-width:900px;border-radius:12px;margin-bottom:16px">
        <p>Here are today's {len(ideas)} app ideas. <a href="{selection_url}" style="color:#007bff;font-weight:bold">Select ideas to build &rarr;</a></p>
        {body}
        <p style="margin-top:30px;padding:15px;background:#f0f7ff;border-radius:8px">
            <a href="{selection_url}" style="color:#007bff;font-size:18px;font-weight:bold">Open Selection UI &rarr;</a>
        </p>
    </body>
    </html>"""


def send_morning_email(ideas, selection_url):
    """Send the morning idea email via Resend."""
    api_key = os.environ.get("RESEND_API_KEY")
    owner_email = os.environ.get("NSAF_OWNER_EMAIL")

    if not api_key or not owner_email:
        log.error("Missing RESEND_API_KEY or NSAF_OWNER_EMAIL")
        return False

    html = format_ideas_html(ideas, selection_url)

    try:
        response = requests.post(
            "https://api.resend.com/emails",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "from": "NSAF <nsaf@resend.dev>",
                "to": [owner_email],
                "subject": f"NSAF: {len(ideas)} App Ideas Ready for Selection",
                "html": html,
            },
            timeout=30,
        )
        response.raise_for_status()
        log.info(f"Morning email sent to {owner_email}")
        return True
    except Exception as e:
        log.error(f"Failed to send morning email: {e}")
        return False
