"""Unit tests for code/qwen_chat.py."""

from __future__ import annotations

import importlib
import json
import sys
import types
from pathlib import Path

import pytest


def _load_qwen_chat_module():
    """Load qwen_chat with a lightweight QwenVL stub (no torch/GPU required)."""
    fake_qwen_vl = types.ModuleType("qwen_vl")

    class DummyQwenVL:
        model_id = "dummy-model"

        def chat(self, messages, **kwargs) -> str:
            return "dummy-reply"

    fake_qwen_vl.QwenVL = DummyQwenVL
    sys.modules["qwen_vl"] = fake_qwen_vl

    import qwen_chat
    return importlib.reload(qwen_chat)


@pytest.fixture
def mod():
    return _load_qwen_chat_module()


@pytest.fixture
def runner(mod):
    return mod.QwenChat.__new__(mod.QwenChat)


@pytest.fixture
def chat(mod):
    from qwen_vl import QwenVL
    return mod.QwenChat(QwenVL(), system_prompt="Be helpful.")


# ── send ──────────────────────────────────────────────────────────────────────

def test_send_appends_user_and_assistant_turns(chat):
    reply = chat.send("hello")
    assert reply == "dummy-reply"
    history = chat.history
    assert history[-2]["role"] == "user"
    assert history[-1] == {"role": "assistant", "content": "dummy-reply"}


def test_send_with_images_builds_image_content(chat):
    chat.send("describe", images=["img.png"])
    user_msg = chat.history[-2]
    content = user_msg["content"]
    assert content[0] == {"type": "image", "image": "img.png"}
    assert content[-1] == {"type": "text", "text": "describe"}


def test_send_with_no_images_text_only(chat):
    chat.send("hello")
    user_msg = chat.history[-2]
    content = user_msg["content"]
    assert len(content) == 1
    assert content[0] == {"type": "text", "text": "hello"}


def test_send_pops_on_failure(mod):
    class FailingVL:
        model_id = "fail"
        def chat(self, messages, **kwargs):
            raise RuntimeError("boom")

    c = mod.QwenChat(FailingVL(), system_prompt="")
    with pytest.raises(RuntimeError, match="boom"):
        c.send("hi")
    # user message must have been removed
    assert all(m["role"] != "user" for m in c.history)


# ── append_command_result ─────────────────────────────────────────────────────

def test_append_command_result_adds_both_turns(chat):
    before = len(chat.history)
    chat.append_command_result("create sheet for Eli", "Sheet saved to storage/Eli/Eli_character_sheet.png.")
    history = chat.history
    assert len(history) == before + 2
    assert history[-2]["role"] == "user"
    assert history[-1]["role"] == "assistant"
    assert "Eli" in history[-2]["content"][0]["text"]


# ── reset ─────────────────────────────────────────────────────────────────────

def test_reset_clears_to_system_prompt(chat):
    chat.send("hello")
    chat.send("world")
    chat.reset()
    history = chat.history
    assert len(history) == 1
    assert history[0]["role"] == "system"
    assert history[0]["content"] == "Be helpful."


def test_reset_without_system_prompt_clears_to_empty(mod):
    from qwen_vl import QwenVL
    c = mod.QwenChat(QwenVL(), system_prompt="")
    c.send("hi")
    c.reset()
    assert c.history == []


# ── history property ──────────────────────────────────────────────────────────

def test_history_returns_copy(chat):
    h = chat.history
    h.append({"role": "hacker", "content": "injected"})
    assert all(m["role"] != "hacker" for m in chat.history)


# ── export_transcript ─────────────────────────────────────────────────────────

def test_export_transcript_writes_valid_json(chat, tmp_path):
    chat.send("hello")
    out = chat.export_transcript(tmp_path / "transcript.json")
    assert out.exists()
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["model_id"] == "dummy-model"
    assert data["turns"] == 1
    assert isinstance(data["messages"], list)
    assert "exported_at" in data


def test_export_transcript_creates_parent_dirs(chat, tmp_path):
    out = chat.export_transcript(tmp_path / "a" / "b" / "t.json")
    assert out.exists()


# ── _strip_old_images ─────────────────────────────────────────────────────────

def test_strip_old_images_preserves_last_user_turn(mod):
    messages = [
        {"role": "user", "content": [{"type": "image", "image": "old.png"}, {"type": "text", "text": "turn1"}]},
        {"role": "assistant", "content": "resp"},
        {"role": "user", "content": [{"type": "image", "image": "new.png"}, {"type": "text", "text": "turn2"}]},
    ]
    result = mod._strip_old_images(messages)
    last = result[2]["content"]
    assert any(item["type"] == "image" for item in last)


def test_strip_old_images_removes_older_images(mod):
    messages = [
        {"role": "user", "content": [{"type": "image", "image": "old.png"}, {"type": "text", "text": "turn1"}]},
        {"role": "assistant", "content": "resp"},
        {"role": "user", "content": [{"type": "text", "text": "turn2"}]},
    ]
    result = mod._strip_old_images(messages)
    first = result[0]["content"]
    assert all(item["type"] != "image" for item in first)
    assert any("[image removed" in item.get("text", "") for item in first)


def test_strip_old_images_single_turn_untouched(mod):
    messages = [
        {"role": "user", "content": [{"type": "image", "image": "only.png"}, {"type": "text", "text": "describe"}]},
    ]
    result = mod._strip_old_images(messages)
    assert any(item["type"] == "image" for item in result[0]["content"])


def test_strip_old_images_no_user_turns_passthrough(mod):
    messages = [{"role": "system", "content": "hi"}]
    result = mod._strip_old_images(messages)
    assert result == messages
