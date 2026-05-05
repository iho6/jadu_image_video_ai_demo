"""Tests for utils.comfyui_utils."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from utils.comfyui_logging import ComfyJobContext, ComfyLogger
from utils.comfyui_utils import (
    ComfyPhaseTracker,
    ComfyPromptError,
    fetch_job_status,
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


@patch("utils.comfyui_utils.requests.post")
def test_queue_prompt_emits_job_sent_phase(mock_post):
    mock_post.return_value.status_code = 200
    mock_post.return_value.content = b'{"prompt_id":"pid-123","number":1}'
    mock_post.return_value.json.return_value = {"prompt_id": "pid-123", "number": 1}
    logger = _CollectLogger()
    ctx = ComfyJobContext("job", "svc", "wf", "http://h/")
    phase = ComfyPhaseTracker(logger=logger, ctx=ctx)
    body = queue_prompt("http://h/", {"n": {}}, "cid", logger=logger, ctx=ctx, phase_tracker=phase)
    assert body["prompt_id"] == "pid-123"
    assert "job.sent" in logger.events


@patch("utils.comfyui_utils.requests.get")
def test_fetch_job_status_returns_none_on_404(mock_get):
    mock_get.return_value.status_code = 404
    out = fetch_job_status("http://h/", "pid")
    assert out is None


def test_phase_tracker_emits_once():
    logger = _CollectLogger()
    ctx = ComfyJobContext("job", "svc", "wf", "http://h/")
    phase = ComfyPhaseTracker(logger=logger, ctx=ctx)
    phase.mark_sent(prompt_id="pid")
    phase.mark_sent(prompt_id="pid")
    phase.mark_running(source="jobs_api")
    phase.mark_running(source="jobs_api")
    phase.mark_returned(result="success", source="history")
    phase.mark_returned(result="success", source="history")
    assert logger.events.count("job.sent") == 1
    assert logger.events.count("job.running") == 1
    assert logger.events.count("job.returned") == 1


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


def test_wait_for_history_entry_phase_running_and_returned(monkeypatch):
    logger = _CollectLogger()
    ctx = ComfyJobContext("job", "svc", "wf", "http://h/", prompt_id="pid")
    phase = ComfyPhaseTracker(logger=logger, ctx=ctx)
    calls = {"n": 0}

    def _fake_fetch(_base, _prompt, timeout=120, logger=None, ctx=None):
        calls["n"] += 1
        if calls["n"] >= 3:
            return {"outputs": {}, "status": {"status_str": "success"}}
        return None

    def _fake_job(_base, _prompt, timeout=120, logger=None, ctx=None):
        return {"status": "in_progress", "outputs_count": 0}

    monkeypatch.setattr("utils.comfyui_utils.fetch_history_entry", _fake_fetch)
    monkeypatch.setattr("utils.comfyui_utils.fetch_job_status", _fake_job)
    out = wait_for_history_entry(
        "http://h/",
        "pid",
        timeout_sec=3.0,
        poll_interval_sec=0.0,
        logger=logger,
        ctx=ctx,
        phase_tracker=phase,
    )
    assert out["outputs"] == {}
    assert "job.running" in logger.events
    assert "job.returned" in logger.events
