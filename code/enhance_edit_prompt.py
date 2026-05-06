"""Enhance a user edit instruction using Qwen3-VL and the edit-polish prompt template.

Uses :class:`QwenVL` for multimodal inference. Pass **1–3 image** paths or URLs
(same practical limit as ``scripts/run_qwen_vl.py``) so VRAM and message layout
stay predictable.

The model is instructed to return **JSON** with a ``Rewritten`` string; see
``parse_rewritten_json`` for parsing and normalization.
"""

from __future__ import annotations

import json
import logging
from typing import Sequence

from utils.prompt_utils import build_polish_edit_prompt_text
from qwen_vl import QwenVL

LOGGER = logging.getLogger(__name__)

_RAW_SNIPPET_LEN = 500


class EnhanceEditPrompt:
    """Format the edit-enhancement request and run it through :class:`QwenVL`."""

    def __init__(self, runner: QwenVL | None = None) -> None:
        self._runner = runner or QwenVL()

    def format_request(self, user_prompt: str) -> str:
        return build_polish_edit_prompt_text(user_prompt)

    def parse_rewritten_json(self, raw: str) -> str:
        """Parse model output as JSON with a ``Rewritten`` string; normalize whitespace."""
        text = raw.strip()
        if not text:
            raise ValueError("Model returned empty text; expected JSON with key 'Rewritten'.")
        cleaned = text.replace("```json", "").replace("```", "")
        try:
            data = json.loads(cleaned.strip())
        except json.JSONDecodeError as exc:
            snippet = raw[:_RAW_SNIPPET_LEN] + ("…" if len(raw) > _RAW_SNIPPET_LEN else "")
            raise ValueError(
                f"Model output is not valid JSON (snippet): {snippet!r}"
            ) from exc
        try:
            rewritten = data["Rewritten"]
        except (TypeError, KeyError) as exc:
            snippet = raw[:_RAW_SNIPPET_LEN] + ("…" if len(raw) > _RAW_SNIPPET_LEN else "")
            raise ValueError(
                f"JSON must contain string key 'Rewritten' (snippet): {snippet!r}"
            ) from exc
        if not isinstance(rewritten, str):
            raise ValueError("'Rewritten' must be a string.")
        out = rewritten.strip().replace("\n", " ")
        if not out:
            raise ValueError("'Rewritten' is empty after strip.")
        return out

    def run_enhance_edit_prompt(
        self,
        user_prompt: str,
        image_sources: Sequence[str],
    ) -> str:
        """Return a single enhanced edit prompt string.

        **Images:** provide 1–3 non-empty paths or URLs (recommended; matches
        ``run_qwen_vl`` CLI). More images may work but increase VRAM use.
        """
        if not image_sources:
            raise ValueError("image_sources must be non-empty.")
        paths = list(image_sources)
        for i, src in enumerate(paths):
            if not isinstance(src, str) or not src.strip():
                raise ValueError(f"image_sources[{i}] must be a non-empty string.")
        if not (1 <= len(paths) <= 3):
            raise ValueError(
                "Provide between 1 and 3 images (same limit as scripts/run_qwen_vl.py)."
            )
        full_prompt = self.format_request(user_prompt)
        LOGGER.info("Running edit-prompt enhancement with %d image(s).", len(paths))
        raw = self._runner.vl_eval(paths, full_prompt)
        return self.parse_rewritten_json(raw)
