"""Unit tests for code/qwen_vl.py with mocked heavy dependencies."""

from __future__ import annotations

import importlib
import sys
import types
from types import SimpleNamespace

import pytest


def fake_process_vision_info(messages, **kwargs):
    has_image = any(
        item.get("type") == "image"
        for msg in messages
        for item in msg.get("content", [])
    )
    has_video = any(
        item.get("type") == "video"
        for msg in messages
        for item in msg.get("content", [])
    )
    image_inputs = ["image-bytes"] if has_image else None
    video_inputs = ["video-bytes"] if has_video else None
    return image_inputs, video_inputs, {"fps": 1}


class FakeProcessor:
    image_processor = SimpleNamespace(patch_size=14)

    @staticmethod
    def apply_chat_template(messages, tokenize, add_generation_prompt):
        assert tokenize is False
        assert add_generation_prompt is True
        return "formatted-prompt"


class FakeAutoProcessor:
    @staticmethod
    def from_pretrained(model_id):
        assert model_id
        return FakeProcessor()


class FakeSamplingParams:
    def __init__(self, **kwargs):
        self.kwargs = kwargs


class FakeLLM:
    def __init__(self, **kwargs):
        self.kwargs = kwargs

    def generate(self, requests, sampling_params):
        assert requests and isinstance(requests, list)
        assert hasattr(sampling_params, "kwargs")
        return [SimpleNamespace(outputs=[SimpleNamespace(text="ok-response")])]


def _load_qwen_vl_module(monkeypatch):
    fake_qwen_utils = types.ModuleType("qwen_vl_utils")
    fake_qwen_utils.process_vision_info = fake_process_vision_info
    monkeypatch.setitem(sys.modules, "qwen_vl_utils", fake_qwen_utils)

    fake_transformers = types.ModuleType("transformers")
    fake_transformers.AutoProcessor = FakeAutoProcessor
    monkeypatch.setitem(sys.modules, "transformers", fake_transformers)

    fake_vllm = types.ModuleType("vllm")
    fake_vllm.LLM = FakeLLM
    fake_vllm.SamplingParams = FakeSamplingParams
    monkeypatch.setitem(sys.modules, "vllm", fake_vllm)

    import qwen_vl

    return importlib.reload(qwen_vl)


@pytest.fixture
def qwen_vl_module(monkeypatch):
    qwen_vl = _load_qwen_vl_module(monkeypatch)
    monkeypatch.setattr(qwen_vl, "load_image", lambda _s: object())
    return qwen_vl


@pytest.fixture
def runner(qwen_vl_module):
    return qwen_vl_module.QwenVL()


def test_build_messages_images_only(runner):
    messages = runner.build_messages(["a.png", "b.png"], "describe")
    content = messages[0]["content"]
    assert content[0] == {"type": "image", "image": "a.png"}
    assert content[1] == {"type": "image", "image": "b.png"}
    assert content[-1] == {"type": "text", "text": "describe"}


def test_build_messages_video_only(runner):
    messages = runner.build_messages([], "describe", video_source="clip.mp4")
    content = messages[0]["content"]
    assert content[0] == {"type": "video", "video": "clip.mp4"}
    assert content[-1] == {"type": "text", "text": "describe"}


def test_prepare_vllm_input_contains_expected_keys(runner):
    messages = runner.build_messages(["a.png"], "prompt", video_source="clip.mp4")
    payload = runner.prepare_vllm_input(messages)

    assert payload["prompt"] == "formatted-prompt"
    assert payload["multi_modal_data"]["image"] == ["image-bytes"]
    assert payload["multi_modal_data"]["video"] == ["video-bytes"]
    assert payload["mm_processor_kwargs"] == {"fps": 1}


def test_vl_eval_returns_first_generated_text(runner):
    out = runner.vl_eval(["a.png"], "prompt")
    assert out == "ok-response"


def test_vl_eval_raises_when_generate_empty(monkeypatch, runner):
    monkeypatch.setattr(runner.llm, "generate", lambda *args, **kwargs: [])

    with pytest.raises(RuntimeError, match="returned no output"):
        runner.vl_eval(["a.png"], "prompt")
