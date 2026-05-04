"""Tests for code/qwen_img_edit.py (mocked HF / pipeline)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
import torch
from PIL import Image

from qwen_img_edit import LoadModel, QwenImgEdit


@patch("qwen_img_edit.QwenImageEditPlusPipeline")
def test_load_model(mock_cls):
    pipe_inst = MagicMock()
    mock_cls.from_pretrained.return_value = pipe_inst
    out = LoadModel.load_model("org/model", device="cpu", dtype=torch.float32)
    mock_cls.from_pretrained.assert_called_once_with(
        "org/model", torch_dtype=torch.float32
    )
    pipe_inst.to.assert_called_once_with("cpu")
    pipe_inst.set_progress_bar_config.assert_called_once_with(disable=None)
    assert out is pipe_inst


@patch("qwen_img_edit.LoadModel.load_model")
def test_qwen_img_edit_init_sets_pipe(mock_lm):
    fake_pipe = MagicMock()
    mock_lm.return_value = fake_pipe
    ed = QwenImgEdit(model_id="Qwen/Qwen-Image-Edit-2511")
    mock_lm.assert_called_once()
    assert ed.pipe is fake_pipe


@patch("qwen_img_edit.LoadModel.load_model")
def test_torch_generator_same_seed_produces_same_randn(mock_lm):
    mock_lm.return_value = MagicMock()
    ed = QwenImgEdit()
    g1 = ed.torch_generator(999)
    g2 = ed.torch_generator(999)
    assert torch.allclose(torch.randn(5, generator=g1), torch.randn(5, generator=g2))


@patch("qwen_img_edit.LoadModel.load_model")
def test_edit_raises_when_images_empty(mock_lm):
    mock_lm.return_value = MagicMock()
    ed = QwenImgEdit()
    with pytest.raises(ValueError, match="images must be non-empty"):
        ed.edit([], "prompt")


@patch("qwen_img_edit.LoadModel.load_model")
def test_edit_calls_pipeline_and_returns_images(mock_lm):
    out_img = Image.new("RGB", (8, 8), color=(1, 2, 3))
    pipe = MagicMock()
    pipe.return_value = MagicMock(images=[out_img])
    mock_lm.return_value = pipe
    ed = QwenImgEdit()
    inp = Image.new("RGB", (4, 4))
    result = ed.edit([inp], "make it blue")
    pipe.assert_called_once()
    assert len(result) == 1
    assert result[0] is out_img


@patch("qwen_img_edit.LoadModel.load_model")
def test_from_pretrained_failure_propagates(mock_lm):
    mock_lm.side_effect = OSError("network")
    with pytest.raises(OSError, match="network"):
        QwenImgEdit()
