"""Minimal unit test for code/character_sheet_creation.py (one test only)."""

from __future__ import annotations

import importlib
import sys
import types


def test_describe_character_strips_output(monkeypatch):
    # Stub qwen_vl to avoid importing vllm.
    fake_qwen_vl = types.ModuleType("qwen_vl")

    class _DummyQwenVL:
        def __init__(self, *args, **kwargs):
            pass

        def vl_eval(self, image_sources, prompt, video_source=None):
            return "  line1\nline2  "

    fake_qwen_vl.QwenVL = _DummyQwenVL
    monkeypatch.setitem(sys.modules, "qwen_vl", fake_qwen_vl)

    import character_sheet_creation

    character_sheet_creation = importlib.reload(character_sheet_creation)

    creator = character_sheet_creation.CharacterSheetCreation(
        comfy_url="http://127.0.0.1:8188",
        vlm_runner=_DummyQwenVL(),
    )
    out = creator.describe_character("ref.png")
    assert out == "line1\nline2"

