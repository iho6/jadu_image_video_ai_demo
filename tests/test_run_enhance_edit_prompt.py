"""Minimal CLI contract test for scripts/run_enhance_edit_prompt.py (one test only)."""

from __future__ import annotations

import importlib
import sys
import types


def test_parse_args_defaults_and_validation(monkeypatch):
    # Stub enhance_edit_prompt to avoid loading torch/transformers/GPU.
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


def test_main_prints_enhanced_prompt(monkeypatch, capsys):
    # Stub enhance_edit_prompt to avoid loading torch/transformers/GPU.
    fake_enhance = types.ModuleType("enhance_edit_prompt")

    class _DummyEnhance:
        def run_enhance_edit_prompt(self, prompt, images):
            assert prompt == "hi"
            assert images == ["a.png"]
            return "ENHANCED"

    fake_enhance.EnhanceEditPrompt = _DummyEnhance
    monkeypatch.setitem(sys.modules, "enhance_edit_prompt", fake_enhance)

    import run_enhance_edit_prompt

    run_enhance_edit_prompt = importlib.reload(run_enhance_edit_prompt)
    monkeypatch.setattr(
        sys,
        "argv",
        ["run_enhance_edit_prompt.py", "--prompt", "hi", "--images", "a.png"],
    )
    run_enhance_edit_prompt.main()
    out = capsys.readouterr().out.strip()
    assert out == "ENHANCED"

