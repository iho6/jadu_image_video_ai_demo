"""Minimal CLI contract test for scripts/run_character_sheet_creation.py.

One test only (per file) to validate argparse defaults without requiring vLLM/Comfy.
"""

from __future__ import annotations

import importlib
import sys
import types
from pathlib import Path


def test_parse_args_defaults_and_flag(monkeypatch):
    # Stub qwen_vl (avoids importing vllm via code/qwen_vl.py).
    fake_qwen_vl = types.ModuleType("qwen_vl")

    class _DummyQwenVL:
        def __init__(self, *args, **kwargs):
            pass

        def vl_eval(self, image_sources, prompt, video_source=None):
            return "yes"

    fake_qwen_vl.QwenVL = _DummyQwenVL
    monkeypatch.setitem(sys.modules, "qwen_vl", fake_qwen_vl)

    import run_character_sheet_creation

    run_character_sheet_creation = importlib.reload(run_character_sheet_creation)

    args = run_character_sheet_creation.parse_args(
        argv=["--image", "ref.png", "--character-name", "Aria", "--character-description"]
    )
    assert args.image == "ref.png"
    assert args.character_name == "Aria"
    assert Path(args.output_dir) == Path("storage") / "Aria"
    assert args.character_description is True

