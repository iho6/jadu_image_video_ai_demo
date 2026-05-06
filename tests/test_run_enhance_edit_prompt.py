"""Minimal CLI contract test for scripts/run_enhance_edit_prompt.py (one test only)."""

from __future__ import annotations

import importlib
import sys
import types


def test_parse_args_defaults_and_validation(monkeypatch):
    # Avoid importing QwenVL / vLLM via EnhanceEditPrompt by stubbing enhance_edit_prompt module.
    fake_enhance = types.ModuleType("enhance_edit_prompt")

    class _DummyEnhance:
        def run_enhance_edit_prompt(self, prompt, images):
            return "ok"

    fake_enhance.EnhanceEditPrompt = _DummyEnhance
    monkeypatch.setitem(sys.modules, "enhance_edit_prompt", fake_enhance)

    import run_enhance_edit_prompt

    run_enhance_edit_prompt = importlib.reload(run_enhance_edit_prompt)

    monkeypatch.setattr(
        sys,
        "argv",
        ["run_enhance_edit_prompt.py", "--prompt", "hi", "--images", "a.png"],
    )
    args = run_enhance_edit_prompt.parse_args()
    assert args.prompt == "hi"
    assert args.images == ["a.png"]

