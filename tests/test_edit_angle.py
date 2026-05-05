"""Tests for services/edit_angle_service/edit_angle.py."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from PIL import Image

import edit_angle


def test_handler_rejects_empty_image():
    args = MagicMock()
    args.image = "   "
    args.prompt = "ok"
    args.output_dir = Path("o")
    args.comfy_url = "http://127.0.0.1:8188"
    assert edit_angle.handler(args) == 1


def test_handler_rejects_empty_prompt():
    args = MagicMock()
    args.image = "a.png"
    args.prompt = "   "
    args.output_dir = Path("o")
    args.comfy_url = "http://127.0.0.1:8188"
    assert edit_angle.handler(args) == 1


@patch("edit_angle.view_image_bytes")
@patch("edit_angle.wait_for_history_entry")
@patch("edit_angle.queue_prompt")
@patch("edit_angle.upload_image")
def test_run_edit_angle_writes_outputs(
    mock_upload,
    mock_queue,
    mock_wait,
    mock_view,
    tmp_path,
):
    inp = tmp_path / "in.png"
    Image.new("RGB", (2, 2), color=(0, 255, 0)).save(inp)
    out_dir = tmp_path / "out"
    mock_upload.return_value = "uploaded.png"
    mock_queue.return_value = {"prompt_id": "pid-angle"}
    mock_wait.return_value = {
        "outputs": {
            edit_angle.NODE_SAVE: {
                "images": [
                    {
                        "filename": "ComfyUI_angle_edit_00001_.png",
                        "subfolder": "",
                        "type": "output",
                    }
                ]
            }
        }
    }
    mock_view.return_value = b"fakepng"
    paths = edit_angle.run_edit_angle(
        str(inp),
        "rotate camera left",
        out_dir,
        comfy_url="http://127.0.0.1:8188",
    )
    assert len(paths) == 1
    assert paths[0].exists()
    assert paths[0].read_bytes() == b"fakepng"
    mock_upload.assert_called_once()
    mock_queue.assert_called_once()
    mock_wait.assert_called_once()
    assert "logger" in mock_upload.call_args.kwargs
    assert "ctx" in mock_upload.call_args.kwargs
    assert "logger" in mock_queue.call_args.kwargs
    assert "ctx" in mock_queue.call_args.kwargs
    assert "phase_tracker" in mock_queue.call_args.kwargs
    assert "phase_tracker" in mock_wait.call_args.kwargs
