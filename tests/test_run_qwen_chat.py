"""Unit tests for scripts/run_qwen_chat.py helper functions (no GPU required)."""

from __future__ import annotations

import importlib
import sys
import types
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]


def _load_script():
    """Import run_qwen_chat with heavy deps stubbed out."""
    # Stub qwen_vl
    fake_qwen_vl = types.ModuleType("qwen_vl")
    class _DummyQwenVL:
        model_id = "dummy"
        def __init__(self, **kwargs): pass
        def chat(self, messages, **kwargs): return "reply"
    fake_qwen_vl.QwenVL = _DummyQwenVL
    sys.modules["qwen_vl"] = fake_qwen_vl

    # Stub qwen_chat
    fake_qwen_chat = types.ModuleType("qwen_chat")
    class _DummyQwenChat:
        def __init__(self, runner, system_prompt=""): pass
        def send(self, text, images=None): return "reply"
        def reset(self): pass
        def export_transcript(self, path): return Path(path)
    fake_qwen_chat.QwenChat = _DummyQwenChat
    sys.modules["qwen_chat"] = fake_qwen_chat

    scripts_dir = str(_ROOT / "scripts")
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)

    import run_qwen_chat
    return importlib.reload(run_qwen_chat)


@pytest.fixture
def script():
    return _load_script()


# ── parse_image_prefix ────────────────────────────────────────────────────────

def test_parse_no_images(script):
    paths, text = script.parse_image_prefix("hello world")
    assert paths == []
    assert text == "hello world"


def test_parse_single_image(script):
    paths, text = script.parse_image_prefix("[photo.png] describe this")
    assert paths == ["photo.png"]
    assert text == "describe this"


def test_parse_multiple_images(script):
    paths, text = script.parse_image_prefix("[a.png, b.png] compare")
    assert paths == ["a.png", "b.png"]
    assert text == "compare"


def test_parse_images_only_no_text(script):
    paths, text = script.parse_image_prefix("[a.png]")
    assert paths == ["a.png"]
    assert text == ""


def test_parse_url_image(script):
    paths, text = script.parse_image_prefix("[https://example.com/img.png] what is this?")
    assert paths == ["https://example.com/img.png"]
    assert text == "what is this?"


def test_parse_whitespace_only_returns_empty(script):
    paths, text = script.parse_image_prefix("   ")
    assert paths == []
    assert text == ""


def test_parse_leading_whitespace_before_bracket(script):
    paths, text = script.parse_image_prefix("  [img.png] text")
    assert paths == ["img.png"]
    assert text == "text"


# ── parse_args ────────────────────────────────────────────────────────────────

def test_parse_args_defaults(script):
    args = script.parse_args([])
    assert args.model_id is None
    assert args.system_prompt is None
    assert args.transcript_dir == "output/chat_transcripts"


def test_parse_args_model_id(script):
    args = script.parse_args(["--model-id", "models/hf/Qwen__Qwen3-VL-4B-Instruct"])
    assert args.model_id == "models/hf/Qwen__Qwen3-VL-4B-Instruct"


def test_parse_args_transcript_dir(script):
    args = script.parse_args(["--transcript-dir", "logs/chat"])
    assert args.transcript_dir == "logs/chat"


def test_parse_args_system_prompt(script):
    args = script.parse_args(["--system-prompt", "Be concise."])
    assert args.system_prompt == "Be concise."
