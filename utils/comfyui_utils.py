"""HTTP helpers for a local ComfyUI server (same routes as ComfyUI script_examples / OpenAPI)."""

from __future__ import annotations

import time
from typing import Any
from urllib.parse import urlencode

import requests
from utils.comfyui_logging import ComfyJobContext, ComfyLogger, NullComfyLogger


class ComfyPromptError(RuntimeError):
    """Raised when ComfyUI rejects or fails a workflow submission."""


def upload_image(
    base_url: str,
    png_bytes: bytes,
    filename: str,
    *,
    timeout: int = 120,
    logger: ComfyLogger | None = None,
    ctx: ComfyJobContext | None = None,
) -> str:
    """POST /upload/image; return stored ``name`` for LoadImage nodes."""
    log = logger or NullComfyLogger()
    t0 = time.monotonic()
    base = base_url.rstrip("/")
    files = {"image": (filename, png_bytes, "image/png")}
    data = {"type": "input", "overwrite": "true"}
    log.event(
        event="upload.start",
        ctx=ctx,
        data={"filename": filename, "timeout": timeout, "bytes": len(png_bytes)},
    )
    try:
        r = requests.post(f"{base}/upload/image", files=files, data=data, timeout=timeout)
        r.raise_for_status()
        body = r.json()
        log.event(
            event="upload.ok",
            ctx=ctx,
            elapsed_ms=int((time.monotonic() - t0) * 1000),
            data={"filename": filename, "stored_name": body.get("name")},
        )
        return body["name"]
    except Exception as e:
        log.event(
            event="upload.error",
            level="error",
            ctx=ctx,
            elapsed_ms=int((time.monotonic() - t0) * 1000),
            data={"filename": filename, "error": str(e), "error_type": type(e).__name__},
        )
        raise


def queue_prompt(
    base_url: str,
    workflow: dict[str, Any],
    client_id: str,
    *,
    timeout: int = 120,
    logger: ComfyLogger | None = None,
    ctx: ComfyJobContext | None = None,
) -> dict[str, Any]:
    """POST /prompt; returns JSON including ``prompt_id`` or raises."""
    log = logger or NullComfyLogger()
    t0 = time.monotonic()
    base = base_url.rstrip("/")
    log.event(event="prompt.queue.start", ctx=ctx, data={"timeout": timeout, "client_id": client_id})
    try:
        r = requests.post(
            f"{base}/prompt",
            json={"prompt": workflow, "client_id": client_id},
            timeout=timeout,
        )
        body = r.json() if r.content else {}
        if r.status_code >= 400:
            err = body.get("error", r.text)
            log.event(
                event="prompt.queue.error",
                level="error",
                ctx=ctx,
                elapsed_ms=int((time.monotonic() - t0) * 1000),
                data={"status_code": r.status_code, "error": err},
            )
            raise ComfyPromptError(f"ComfyUI prompt error ({r.status_code}): {err}")
        if "error" in body and body["error"]:
            log.event(
                event="prompt.queue.error",
                level="error",
                ctx=ctx,
                elapsed_ms=int((time.monotonic() - t0) * 1000),
                data={"error": body["error"]},
            )
            raise ComfyPromptError(f"ComfyUI prompt error: {body['error']}")
        if "prompt_id" not in body:
            log.event(
                event="prompt.queue.error",
                level="error",
                ctx=ctx,
                elapsed_ms=int((time.monotonic() - t0) * 1000),
                data={"error": "missing_prompt_id", "response": body},
            )
            raise ComfyPromptError(f"Unexpected prompt response: {body}")
        if ctx is not None:
            ctx.prompt_id = body["prompt_id"]
        log.event(
            event="prompt.queue.ok",
            ctx=ctx,
            elapsed_ms=int((time.monotonic() - t0) * 1000),
            data={"prompt_id": body.get("prompt_id")},
        )
        return body
    except ComfyPromptError:
        raise
    except Exception as e:
        log.event(
            event="prompt.queue.error",
            level="error",
            ctx=ctx,
            elapsed_ms=int((time.monotonic() - t0) * 1000),
            data={"error": str(e), "error_type": type(e).__name__},
        )
        raise


def fetch_history_entry(
    base_url: str,
    prompt_id: str,
    *,
    timeout: int = 120,
    logger: ComfyLogger | None = None,
    ctx: ComfyJobContext | None = None,
) -> dict[str, Any] | None:
    """GET /history/{prompt_id}; returns entry dict or None if not yet available."""
    log = logger or NullComfyLogger()
    t0 = time.monotonic()
    base = base_url.rstrip("/")
    try:
        r = requests.get(f"{base}/history/{prompt_id}", timeout=timeout)
        r.raise_for_status()
        data = r.json()
        entry = None if (not data or prompt_id not in data) else data[prompt_id]
        log.event(
            event="history.fetch.ok",
            level="debug",
            ctx=ctx,
            elapsed_ms=int((time.monotonic() - t0) * 1000),
            data={"prompt_id": prompt_id, "found": entry is not None},
        )
        return entry
    except Exception as e:
        log.event(
            event="history.fetch.error",
            level="error",
            ctx=ctx,
            elapsed_ms=int((time.monotonic() - t0) * 1000),
            data={"prompt_id": prompt_id, "error": str(e), "error_type": type(e).__name__},
        )
        raise


def wait_for_history_entry(
    base_url: str,
    prompt_id: str,
    *,
    timeout_sec: float = 600.0,
    poll_interval_sec: float = 0.5,
    logger: ComfyLogger | None = None,
    ctx: ComfyJobContext | None = None,
) -> dict[str, Any]:
    """Poll until history contains ``prompt_id`` or timeout."""
    log = logger or NullComfyLogger()
    start = time.monotonic()
    deadline = time.monotonic() + timeout_sec
    polls = 0
    log.event(
        event="history.poll.start",
        ctx=ctx,
        data={"prompt_id": prompt_id, "timeout_sec": timeout_sec, "poll_interval_sec": poll_interval_sec},
    )
    while time.monotonic() < deadline:
        polls += 1
        entry = fetch_history_entry(base_url, prompt_id, logger=log, ctx=ctx)
        if entry is not None:
            log.event(
                event="history.poll.ok",
                ctx=ctx,
                elapsed_ms=int((time.monotonic() - start) * 1000),
                data={"prompt_id": prompt_id, "polls": polls},
            )
            return entry
        if polls % 10 == 0:
            elapsed = time.monotonic() - start
            log.event(
                event="history.poll.tick",
                level="debug",
                ctx=ctx,
                elapsed_ms=int(elapsed * 1000),
                data={"prompt_id": prompt_id, "polls": polls, "remaining_sec": max(0.0, timeout_sec - elapsed)},
            )
        time.sleep(poll_interval_sec)
    log.event(
        event="history.poll.timeout",
        level="error",
        ctx=ctx,
        elapsed_ms=int((time.monotonic() - start) * 1000),
        data={"prompt_id": prompt_id, "polls": polls, "timeout_sec": timeout_sec},
    )
    raise TimeoutError(
        f"Timed out after {timeout_sec}s waiting for history for prompt_id={prompt_id}"
    )


def view_image_bytes(
    base_url: str,
    filename: str,
    subfolder: str,
    folder_type: str,
    *,
    timeout: int = 120,
    logger: ComfyLogger | None = None,
    ctx: ComfyJobContext | None = None,
) -> bytes:
    """GET /view for an output/input image."""
    log = logger or NullComfyLogger()
    t0 = time.monotonic()
    base = base_url.rstrip("/")
    q = urlencode(
        {
            "filename": filename,
            "subfolder": subfolder,
            "type": folder_type,
        }
    )
    log.event(
        event="image.view.start",
        level="debug",
        ctx=ctx,
        data={"filename": filename, "subfolder": subfolder, "type": folder_type, "timeout": timeout},
    )
    try:
        r = requests.get(f"{base}/view?{q}", timeout=timeout)
        r.raise_for_status()
        data = r.content
        log.event(
            event="image.view.ok",
            level="debug",
            ctx=ctx,
            elapsed_ms=int((time.monotonic() - t0) * 1000),
            data={"filename": filename, "bytes": len(data)},
        )
        return data
    except Exception as e:
        log.event(
            event="image.view.error",
            level="error",
            ctx=ctx,
            elapsed_ms=int((time.monotonic() - t0) * 1000),
            data={"filename": filename, "error": str(e), "error_type": type(e).__name__},
        )
        raise
