"""VLM helper utilities (Yes/No checks, parsing, etc.)."""

from __future__ import annotations

from qwen_vl import QwenVL


def character_fullbody_check(*, runner: QwenVL, image_source: str, prompt: str) -> bool:
    """Return True if full-body, False if not, based on strict VLM Yes/No output."""
    raw = runner.vl_eval([image_source], prompt)
    text = str(raw).strip().lower()
    if text == "yes":
        return True
    if text == "no":
        return False
    raise ValueError(f"Full-body check must return 'Yes' or 'No'. Got: {raw!r}")

