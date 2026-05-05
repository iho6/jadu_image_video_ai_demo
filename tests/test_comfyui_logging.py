from __future__ import annotations

import json
from pathlib import Path

from utils.comfyui_logging import ComfyJobContext, JsonlComfyLogger, StdoutComfyLogger


class _Buffer:
    def __init__(self):
        self.parts: list[str] = []

    def write(self, s: str) -> int:
        self.parts.append(s)
        return len(s)

    def flush(self) -> None:
        return None


def test_stdout_logger_renders_event_line():
    buf = _Buffer()
    logger = StdoutComfyLogger(stream=buf)
    ctx = ComfyJobContext(
        job_id="job-1",
        service="img_edit",
        workflow="wf.json",
        comfy_url="http://127.0.0.1:8188",
        prompt_id="pid-1",
    )
    logger.event(event="prompt.queue.ok", ctx=ctx, elapsed_ms=123, data={"x": 1})
    out = "".join(buf.parts)
    assert "[comfy][info] prompt.queue.ok" in out
    assert "job=job-1" in out
    assert "prompt=pid-1" in out
    assert "elapsed_ms=123" in out


def test_jsonl_logger_writes_valid_json(tmp_path: Path):
    path = tmp_path / "comfy.jsonl"
    logger = JsonlComfyLogger(path)
    ctx = ComfyJobContext(
        job_id="job-2",
        service="edit_angle",
        workflow="w2.json",
        comfy_url="http://127.0.0.1:8188",
    )
    logger.event(event="job.start", ctx=ctx, data={"a": "b"})
    payload = json.loads(path.read_text(encoding="utf-8").strip())
    assert payload["event"] == "job.start"
    assert payload["job_id"] == "job-2"
    assert payload["service"] == "edit_angle"
    assert payload["data"] == {"a": "b"}
