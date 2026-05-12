"""Unit tests for code/qwen_vl.py with mocked heavy dependencies."""

from __future__ import annotations

import importlib
import sys
import types
from types import SimpleNamespace

import pytest


def _content_items(msg: dict):
    """Yield content items; handles both list content (user) and string content (assistant)."""
    content = msg.get("content", [])
    if isinstance(content, list):
        yield from content


def fake_process_vision_info(messages, **kwargs):
    has_image = any(
        isinstance(item, dict) and item.get("type") == "image"
        for msg in messages
        for item in _content_items(msg)
    )
    has_video = any(
        isinstance(item, dict) and item.get("type") == "video"
        for msg in messages
        for item in _content_items(msg)
    )
    image_inputs = ["image-bytes"] if has_image else None
    video_inputs = ["video-bytes"] if has_video else None
    return image_inputs, video_inputs, {"fps": 1}


class _FakeIds:
    """Minimal input_ids stub with a .shape attribute."""
    shape = (1, 1)  # shape[1] == 1, so out[:, 1:] works with FakeTensor


class FakeBatch(dict):
    input_ids = _FakeIds()

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


class FakeTensor:
    """Minimal stub supporting out[:, n:] slicing used by chat() and vl_eval()."""

    def __getitem__(self, key):
        return self  # slice returns self; batch_decode accepts it


class FakeModel:
    device = "cpu"

    def to(self, _device):
        return self

    def eval(self):
        return self

    def generate(self, **kwargs):
        return FakeTensor()


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
    # "dummy-model" contains no "/" and doesn't start with "." so the path
    # existence check in __init__ is skipped (no real weights needed for tests).
    return qwen_vl_module.QwenVL(model_id="dummy-model")


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


def test_chat_single_turn(runner):
    messages = [{"role": "user", "content": [{"type": "text", "text": "hi"}]}]
    assert runner.chat(messages) == "ok-response"


def test_chat_multi_turn(runner):
    messages = [
        {"role": "user", "content": [{"type": "text", "text": "hi"}]},
        {"role": "assistant", "content": "hello"},
        {"role": "user", "content": [{"type": "text", "text": "2+2?"}]},
    ]
    assert runner.chat(messages) == "ok-response"


def test_chat_with_image(runner):
    messages = [{"role": "user", "content": [
        {"type": "image", "image": "x.png"},
        {"type": "text", "text": "describe"},
    ]}]
    assert runner.chat(messages) == "ok-response"


def test_chat_raises_on_empty(runner):
    with pytest.raises(ValueError, match="non-empty"):
        runner.chat([])
