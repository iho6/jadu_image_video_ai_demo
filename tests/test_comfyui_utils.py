"""Tests for utils.comfyui_utils."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from utils.comfyui_utils import (
    ComfyPromptError,
    fetch_history_entry,
    queue_prompt,
    upload_image,
)


@patch("utils.comfyui_utils.requests.post")
def test_upload_image_returns_name(mock_post):
    mock_post.return_value.raise_for_status = MagicMock()
    mock_post.return_value.json.return_value = {
        "name": "out.png",
        "subfolder": "",
        "type": "input",
    }
    assert upload_image("http://127.0.0.1:8188", b"x", "in.png") == "out.png"
    mock_post.assert_called_once()
    call_kw = mock_post.call_args
    assert "/upload/image" in call_kw[0][0]


@patch("utils.comfyui_utils.requests.post")
def test_queue_prompt_raises_on_http_error(mock_post):
    mock_post.return_value.status_code = 400
    mock_post.return_value.content = b'{"error": "bad"}'
    mock_post.return_value.json.return_value = {"error": "bad graph"}
    with pytest.raises(ComfyPromptError, match="bad graph"):
        queue_prompt("http://h:81/", {}, "cid")


@patch("utils.comfyui_utils.requests.get")
def test_fetch_history_entry_none_when_empty(mock_get):
    mock_get.return_value.raise_for_status = MagicMock()
    mock_get.return_value.json.return_value = {}
    assert fetch_history_entry("http://h/", "abc") is None


@patch("utils.comfyui_utils.requests.get")
def test_fetch_history_entry_returns_inner(mock_get):
    mock_get.return_value.raise_for_status = MagicMock()
    mock_get.return_value.json.return_value = {
        "pid": {"outputs": {"60": {"images": []}}},
    }
    assert fetch_history_entry("http://h/", "pid") == {"outputs": {"60": {"images": []}}}
