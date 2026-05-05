"""Tests for utils.comfyui_utils."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from utils.comfyui_logging import ComfyJobContext, ComfyLogger
from utils.comfyui_utils import (
    ComfyPromptError,
    fetch_history_entry,
    queue_prompt,
    upload_image,
    wait_for_history_entry,
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


class _CollectLogger(ComfyLogger):
    def __init__(self):
        self.events: list[str] = []

    def emit(self, event):
        self.events.append(event.event)


@patch("utils.comfyui_utils.requests.post")
def test_queue_prompt_emits_error_event(mock_post):
    mock_post.return_value.status_code = 400
    mock_post.return_value.content = b'{"error":"bad"}'
    mock_post.return_value.json.return_value = {"error": "bad graph"}
    logger = _CollectLogger()
    ctx = ComfyJobContext("job", "svc", "wf", "http://h/")
    with pytest.raises(ComfyPromptError):
        queue_prompt("http://h/", {}, "cid", logger=logger, ctx=ctx)
    assert "prompt.queue.start" in logger.events
    assert "prompt.queue.error" in logger.events


def test_wait_for_history_entry_emits_tick_and_ok(monkeypatch):
    logger = _CollectLogger()
    ctx = ComfyJobContext("job", "svc", "wf", "http://h/")
    calls = {"n": 0}

    def _fake_fetch(_base, _prompt, timeout=120, logger=None, ctx=None):
        calls["n"] += 1
        if calls["n"] >= 11:
            return {"outputs": {}}
        return None

    monkeypatch.setattr("utils.comfyui_utils.fetch_history_entry", _fake_fetch)
    out = wait_for_history_entry(
        "http://h/",
        "pid",
        timeout_sec=5.0,
        poll_interval_sec=0.0,
        logger=logger,
        ctx=ctx,
    )
    assert out == {"outputs": {}}
    assert "history.poll.start" in logger.events
    assert "history.poll.tick" in logger.events
    assert "history.poll.ok" in logger.events
