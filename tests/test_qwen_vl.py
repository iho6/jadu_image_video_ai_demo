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


class FakeBatch(dict):
    def to(self, _device):
        return self


class FakeProcessor:
    @staticmethod
    def apply_chat_template(messages, tokenize, add_generation_prompt):
        assert tokenize is False
        assert add_generation_prompt is True
        return "formatted-prompt"

    def __call__(self, **kwargs):
        return FakeBatch(input_ids=[[1]])

    @staticmethod
    def batch_decode(tokens, skip_special_tokens):
        return ["ok-response"]


class FakeAutoProcessor:
    @staticmethod
    def from_pretrained(model_id, **kwargs):
        assert model_id
        return FakeProcessor()


class FakeModel:
    device = "cpu"

    def to(self, _device):
        return self

    def eval(self):
        return self

    def generate(self, **kwargs):
        return ["tokens"]


class FakeAutoModelForVision2Seq:
    @staticmethod
    def from_pretrained(model_id, **kwargs):
        assert model_id
        return FakeModel()


class FakeInferenceMode:
    def __enter__(self):
        return None

    def __exit__(self, exc_type, exc, tb):
        return False


def _load_qwen_vl_module(monkeypatch):
    fake_qwen_utils = types.ModuleType("qwen_vl_utils")
    fake_qwen_utils.process_vision_info = fake_process_vision_info
    monkeypatch.setitem(sys.modules, "qwen_vl_utils", fake_qwen_utils)

    fake_transformers = types.ModuleType("transformers")
    fake_transformers.AutoProcessor = FakeAutoProcessor
    fake_transformers.AutoModelForVision2Seq = FakeAutoModelForVision2Seq
    monkeypatch.setitem(sys.modules, "transformers", fake_transformers)

    fake_cuda = SimpleNamespace(
        is_available=lambda: True,
        is_bf16_supported=lambda: True,
    )
    fake_torch = types.ModuleType("torch")
    fake_torch.bfloat16 = "bf16"
    fake_torch.float16 = "fp16"
    fake_torch.cuda = fake_cuda
    fake_torch.device = lambda s: s
    fake_torch.inference_mode = lambda: FakeInferenceMode()
    monkeypatch.setitem(sys.modules, "torch", fake_torch)

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
    assert content[0] == {"type": "image", "image": "a.png", "max_pixels": 1280 * 28 * 28}
    assert content[1] == {"type": "image", "image": "b.png", "max_pixels": 1280 * 28 * 28}
    assert content[-1] == {"type": "text", "text": "describe"}


def test_build_messages_video_only(runner):
    messages = runner.build_messages([], "describe", video_source="clip.mp4")
    content = messages[0]["content"]
    assert content[0] == {"type": "video", "video": "clip.mp4"}
    assert content[-1] == {"type": "text", "text": "describe"}


def test_vl_eval_returns_first_generated_text(runner):
    out = runner.vl_eval(["a.png"], "prompt")
    assert out == "ok-response"
