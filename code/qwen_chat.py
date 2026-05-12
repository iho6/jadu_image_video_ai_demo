"""Multi-turn chat session on top of QwenVL."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from qwen_vl import QwenVL

LOGGER = logging.getLogger(__name__)


class QwenChat:
    """Maintains a multi-turn conversation with a QwenVL model."""

    def __init__(self, runner: QwenVL, system_prompt: str = "") -> None:
        self._runner = runner
        self._system_prompt = system_prompt
        self._messages: list[dict[str, Any]] = []
        if system_prompt:
            self._messages.append({"role": "system", "content": system_prompt})

    # ── core ──────────────────────────────────────────────────────────────

    def send(self, text: str, images: list[str] | None = None) -> str:
        """Append a user turn, call the model, append assistant turn, return reply."""
        content: list[dict[str, Any]] = []
        for img in (images or []):
            content.append({"type": "image", "image": img})
        content.append({"type": "text", "text": text})
        self._messages.append({"role": "user", "content": content})

        try:
            reply = self._runner.chat(_strip_old_images(self._messages))
        except Exception:
            self._messages.pop()  # keep history valid on failure
            raise

        self._messages.append({"role": "assistant", "content": reply})
        return reply

    def append_command_result(self, user_text: str, assistant_text: str) -> None:
        """Inject a slash-command side-effect into history so the model stays aware."""
        self._messages.append({"role": "user", "content": [{"type": "text", "text": user_text}]})
        self._messages.append({"role": "assistant", "content": assistant_text})

    # ── state ─────────────────────────────────────────────────────────────

    @property
    def history(self) -> list[dict[str, Any]]:
        return list(self._messages)

    def reset(self) -> None:
        """Clear history back to just the system prompt."""
        self._messages = []
        if self._system_prompt:
            self._messages.append({"role": "system", "content": self._system_prompt})

    # ── export ────────────────────────────────────────────────────────────

    def export_transcript(self, path: Path) -> Path:
        """Write the full conversation history to a JSON file. Returns the path."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        user_turns = sum(1 for m in self._messages if m["role"] == "user")
        payload = {
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "model_id": self._runner.model_id,
            "turns": user_turns,
            "messages": self._messages,
        }
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        LOGGER.info("Transcript saved to %s", path)
        return path


def _strip_old_images(messages: list[dict]) -> list[dict]:
    """Remove image/video content items from all user turns except the last.

    process_vision_info re-embeds every image it finds on every call. Stripping
    old images prevents wasting VRAM re-encoding images from earlier turns.
    A placeholder text item is inserted so the model knows an image was discussed.
    """
    last_user = max(
        (i for i, m in enumerate(messages) if m["role"] == "user"),
        default=None,
    )
    if last_user is None:
        return messages

    result = []
    for i, msg in enumerate(messages):
        if msg["role"] == "user" and i < last_user:
            new_content: list[dict[str, Any]] = []
            stripped = False
            for item in msg.get("content", []):
                if item.get("type") in ("image", "video"):
                    if not stripped:
                        new_content.append({"type": "text", "text": "[image removed from history]"})
                        stripped = True
                else:
                    new_content.append(item)
            result.append({**msg, "content": new_content})
        else:
            result.append(msg)
    return result
