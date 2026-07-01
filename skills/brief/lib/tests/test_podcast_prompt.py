"""Stage 3: podcast prompt builder."""

from __future__ import annotations

from daily_brief.render import build_podcast_prompt

from .fixtures import sample_profile


def test_prompt_embeds_summary_and_lens():
    prompt = build_podcast_prompt("# Brief\n\n- something happened", sample_profile())
    assert "something happened" in prompt
    assert "two hosts" in prompt.lower()
    assert "ships LLM products" in prompt  # profile description as the lens


def test_prompt_asks_for_script_only():
    prompt = build_podcast_prompt("summary", sample_profile())
    assert "Output ONLY the script" in prompt
