"""HTTP helpers for a local ComfyUI server (same routes as ComfyUI script_examples / OpenAPI)."""

from __future__ import annotations

import time
from typing import Any
from urllib.parse import urlencode

import requests


class ComfyPromptError(RuntimeError):
    """Raised when ComfyUI rejects or fails a workflow submission."""


def upload_image(
    base_url: str,
    png_bytes: bytes,
    filename: str,
    *,
    timeout: int = 120,
) -> str:
    """POST /upload/image; return stored ``name`` for LoadImage nodes."""
    base = base_url.rstrip("/")
    files = {"image": (filename, png_bytes, "image/png")}
    data = {"type": "input", "overwrite": "true"}
    r = requests.post(f"{base}/upload/image", files=files, data=data, timeout=timeout)
    r.raise_for_status()
    body = r.json()
    return body["name"]


def queue_prompt(
    base_url: str,
    workflow: dict[str, Any],
    client_id: str,
    *,
    timeout: int = 120,
) -> dict[str, Any]:
    """POST /prompt; returns JSON including ``prompt_id`` or raises."""
    base = base_url.rstrip("/")
    r = requests.post(
        f"{base}/prompt",
        json={"prompt": workflow, "client_id": client_id},
        timeout=timeout,
    )
    body = r.json() if r.content else {}
    if r.status_code >= 400:
        err = body.get("error", r.text)
        raise ComfyPromptError(f"ComfyUI prompt error ({r.status_code}): {err}")
    if "error" in body and body["error"]:
        raise ComfyPromptError(f"ComfyUI prompt error: {body['error']}")
    if "prompt_id" not in body:
        raise ComfyPromptError(f"Unexpected prompt response: {body}")
    return body


def fetch_history_entry(
    base_url: str,
    prompt_id: str,
    *,
    timeout: int = 120,
) -> dict[str, Any] | None:
    """GET /history/{prompt_id}; returns entry dict or None if not yet available."""
    base = base_url.rstrip("/")
    r = requests.get(f"{base}/history/{prompt_id}", timeout=timeout)
    r.raise_for_status()
    data = r.json()
    if not data or prompt_id not in data:
        return None
    return data[prompt_id]


def wait_for_history_entry(
    base_url: str,
    prompt_id: str,
    *,
    timeout_sec: float = 600.0,
    poll_interval_sec: float = 0.5,
) -> dict[str, Any]:
    """Poll until history contains ``prompt_id`` or timeout."""
    deadline = time.monotonic() + timeout_sec
    while time.monotonic() < deadline:
        entry = fetch_history_entry(base_url, prompt_id)
        if entry is not None:
            return entry
        time.sleep(poll_interval_sec)
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
) -> bytes:
    """GET /view for an output/input image."""
    base = base_url.rstrip("/")
    q = urlencode(
        {
            "filename": filename,
            "subfolder": subfolder,
            "type": folder_type,
        }
    )
    r = requests.get(f"{base}/view?{q}", timeout=timeout)
    r.raise_for_status()
    return r.content
