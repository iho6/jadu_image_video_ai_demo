"""Tests for services/img_edit_service/img_edit.py."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from PIL import Image

import img_edit


def test_handler_rejects_too_many_images():
    args = MagicMock()
    args.images = ["a", "b", "c", "d"]
    args.prompt = "ok"
    args.output_dir = Path("o")
    args.comfy_url = "http://127.0.0.1:8188"
    assert img_edit.handler(args) == 1


def test_handler_rejects_empty_prompt():
    args = MagicMock()
    args.images = ["a.png"]
    args.prompt = "   "
    args.output_dir = Path("o")
    args.comfy_url = "http://127.0.0.1:8188"
    assert img_edit.handler(args) == 1


@patch("img_edit.view_image_bytes")
@patch("img_edit.wait_for_history_entry")
@patch("img_edit.queue_prompt")
@patch("img_edit.upload_image")
def test_run_img_edit_writes_outputs(
    mock_upload,
    mock_queue,
    mock_wait,
    mock_view,
    tmp_path,
):
    inp = tmp_path / "in.png"
    Image.new("RGB", (2, 2), color=(255, 0, 0)).save(inp)
    out_dir = tmp_path / "out"
    mock_upload.side_effect = ["u0.png", "u1.png", "u2.png"]
    mock_queue.return_value = {"prompt_id": "pid-1"}
    mock_wait.return_value = {
        "outputs": {
            img_edit.NODE_SAVE: {
                "images": [
                    {
                        "filename": "ComfyUI_00001_.png",
                        "subfolder": "",
                        "type": "output",
                    }
                ]
            }
        }
    }
    mock_view.return_value = b"fakepng"
    paths = img_edit.run_img_edit(
        [str(inp)],
        "make it blue",
        out_dir,
        comfy_url="http://127.0.0.1:8188",
    )
    assert len(paths) == 1
    assert paths[0].exists()
    assert paths[0].read_bytes() == b"fakepng"
    mock_upload.assert_called()
    mock_queue.assert_called_once()
    mock_wait.assert_called_once()
    assert "logger" in mock_upload.call_args.kwargs
    assert "ctx" in mock_upload.call_args.kwargs
    assert "logger" in mock_queue.call_args.kwargs
    assert "ctx" in mock_queue.call_args.kwargs
