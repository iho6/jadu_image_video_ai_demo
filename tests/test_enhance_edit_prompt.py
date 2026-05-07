"""Minimal unit test for code/enhance_edit_prompt.py (one test only)."""

from __future__ import annotations

import importlib
import sys
import types
from pathlib import Path


def _load_enhancer_class():
    # Stub qwen_vl to avoid loading torch/transformers/GPU when importing EnhanceEditPrompt.
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
    return enhance_edit_prompt.EnhanceEditPrompt


def _load_prompt_fixtures() -> list[str]:
    fixtures_dir = Path(__file__).parent / "fixtures"
    sys.path.insert(0, str(fixtures_dir))
    try:
        from edit_prompt_enhancer_prompts import PROMPTS  # type: ignore
    finally:
        sys.path.pop(0)
    return list(PROMPTS)


def test_format_request_contains_user_input_and_suffix():
    EnhanceEditPrompt = _load_enhancer_class()
    prompts = _load_prompt_fixtures()
    e = EnhanceEditPrompt(runner=None)
    for p in prompts:
        out = e.format_request(p)
        assert "Edit Prompt Enhancer" in out
        assert f"User Input: {p.strip()}" in out
        assert out.strip().endswith("Rewritten Prompt:")


def test_format_request_rejects_empty_prompt():
    EnhanceEditPrompt = _load_enhancer_class()
    e = EnhanceEditPrompt(runner=None)
    try:
        e.format_request("   ")
        assert False, "Expected ValueError"
    except ValueError:
        pass


def test_parse_rewritten_json_accepts_fenced_and_normalizes():
    EnhanceEditPrompt = _load_enhancer_class()
    raw = "```json\n{\"Rewritten\": \"a\\n b\"}\n```"
    out = EnhanceEditPrompt(runner=None).parse_rewritten_json(raw)
    assert out == "a  b"


def test_parse_rewritten_json_accepts_unfenced_json():
    EnhanceEditPrompt = _load_enhancer_class()
    out = EnhanceEditPrompt(runner=None).parse_rewritten_json('{"Rewritten":"hello"}')
    assert out == "hello"


def test_parse_rewritten_json_rejects_invalid_json():
    EnhanceEditPrompt = _load_enhancer_class()
    try:
        EnhanceEditPrompt(runner=None).parse_rewritten_json("{not json}")
        assert False, "Expected ValueError"
    except ValueError as e:
        assert "not valid JSON" in str(e)


def test_parse_rewritten_json_rejects_missing_key():
    EnhanceEditPrompt = _load_enhancer_class()
    try:
        EnhanceEditPrompt(runner=None).parse_rewritten_json('{"Nope":"x"}')
        assert False, "Expected ValueError"
    except ValueError as e:
        assert "must contain string key 'Rewritten'" in str(e)


def test_parse_rewritten_json_rejects_non_string_rewritten():
    EnhanceEditPrompt = _load_enhancer_class()
    try:
        EnhanceEditPrompt(runner=None).parse_rewritten_json('{"Rewritten": 123}')
        assert False, "Expected ValueError"
    except ValueError as e:
        assert "'Rewritten' must be a string" in str(e)


def test_parse_rewritten_json_rejects_empty_rewritten():
    EnhanceEditPrompt = _load_enhancer_class()
    try:
        EnhanceEditPrompt(runner=None).parse_rewritten_json('{"Rewritten":"   "}')
        assert False, "Expected ValueError"
    except ValueError as e:
        assert "empty after strip" in str(e)

