"""Minimal unit test for code/enhance_edit_prompt.py (one test only)."""

from __future__ import annotations

import importlib
import sys
import types


def test_parse_rewritten_json_accepts_fenced_and_normalizes():
    # Stub qwen_vl to avoid importing vllm via code/qwen_vl.py when importing EnhanceEditPrompt.
    fake_qwen_vl = types.ModuleType("qwen_vl")

    class _DummyQwenVL:
        def __init__(self, *args, **kwargs):
            pass

        def vl_eval(self, image_sources, prompt, video_source=None):
            return '{"Rewritten":"ok"}'

    fake_qwen_vl.QwenVL = _DummyQwenVL
    sys.modules["qwen_vl"] = fake_qwen_vl

    import enhance_edit_prompt

    enhance_edit_prompt = importlib.reload(enhance_edit_prompt)
    EnhanceEditPrompt = enhance_edit_prompt.EnhanceEditPrompt

    raw = "```json\n{\"Rewritten\": \"a\\n b\"}\n```"
    out = EnhanceEditPrompt(runner=None).parse_rewritten_json(raw)
    assert out == "a  b"

