"""Interactive multi-turn chat REPL for Qwen3-VL.

Run from repo root:
    python scripts/run_qwen_chat.py
    python scripts/run_qwen_chat.py --model-id models/hf/Qwen__Qwen3-VL-4B-Instruct
    python scripts/run_qwen_chat.py --system-prompt "You are a character art assistant."
    python scripts/run_qwen_chat.py --transcript-dir logs/transcripts

Image syntax — prefix your message with bracket-enclosed paths or URLs:
    [photo.png] describe this character
    [a.png, b.png] compare these two
    [https://example.com/img.png] what is this?

Only images in the current turn are sent to the model. Images from prior turns
are stripped from the context payload to avoid re-embedding them on every call.

Slash commands:
    /quit    — save transcript and exit
    /reset   — clear conversation history
    /export  — save transcript now (continues chatting)
    /help    — show this help
"""

from __future__ import annotations

import atexit
import argparse
import logging
import os
import re
import sys
from datetime import datetime
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
for _p in (str(_ROOT), str(_ROOT / "code")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from qwen_vl import QwenVL                          # noqa: E402
from qwen_chat import QwenChat                      # noqa: E402
from utils.prompt_utils import CHAT_SYSTEM_PROMPT   # noqa: E402

LOGGER = logging.getLogger(__name__)

_IMAGE_RE = re.compile(r"^\s*\[([^\]]+)\]\s*")

HELP_TEXT = """
Commands:
  /quit    — save transcript and exit
  /reset   — clear conversation history (keeps system prompt)
  /export  — save transcript now without exiting
  /help    — show this message

Image syntax:
  [path_or_url] your message text
  [a.png, b.png] compare these two images
""".strip()


def parse_image_prefix(raw: str) -> tuple[list[str], str]:
    """Parse optional '[img1, img2] text' prefix from a raw input line.

    Returns (image_paths, remaining_text). Both may be empty.
    """
    m = _IMAGE_RE.match(raw)
    if not m:
        return [], raw.strip()
    paths = [os.path.expandvars(p.strip()) for p in m.group(1).split(",") if p.strip()]
    text = raw[m.end():].strip()
    return paths, text


def _transcript_path(transcript_dir: Path) -> Path:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return transcript_dir / f"session_{stamp}.json"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Interactive Qwen3-VL chat REPL.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python scripts/run_qwen_chat.py\n"
            "  python scripts/run_qwen_chat.py --model-id models/hf/Qwen__Qwen3-VL-4B-Instruct\n"
            "  python scripts/run_qwen_chat.py --system-prompt 'You are a helpful assistant.'\n"
            "  python scripts/run_qwen_chat.py --transcript-dir logs/transcripts"
        ),
    )
    parser.add_argument(
        "--model-id",
        default=None,
        help="Override model path or HF repo id (default: QwenVL default).",
    )
    parser.add_argument(
        "--system-prompt",
        default=None,
        help="Custom system prompt (default: character art assistant prompt).",
    )
    parser.add_argument(
        "--transcript-dir",
        default="output/chat_transcripts",
        help="Directory to write session transcripts (default: output/chat_transcripts/).",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    )

    print("Loading model (this may take a moment)...")
    kwargs: dict = {}
    if args.model_id:
        kwargs["model_id"] = args.model_id
    runner = QwenVL(**kwargs)
    chat = QwenChat(runner, system_prompt=args.system_prompt or CHAT_SYSTEM_PROMPT)

    transcript_dir = Path(args.transcript_dir)
    transcript_path = _transcript_path(transcript_dir)
    atexit.register(lambda: chat.export_transcript(transcript_path))

    print("Chat ready. Type /help for commands, /quit to exit.\n")

    while True:
        try:
            raw = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nExiting.")
            break

        if not raw:
            continue

        # ── slash commands ────────────────────────────────────────────────
        if raw == "/quit":
            path = chat.export_transcript(transcript_path)
            print(f"Transcript saved: {path}")
            sys.exit(0)

        if raw == "/reset":
            chat.reset()
            print("History cleared.")
            continue

        if raw.startswith("/export"):
            path = chat.export_transcript(transcript_path)
            print(f"Transcript saved: {path}")
            continue

        if raw == "/help":
            print(HELP_TEXT)
            continue

        if raw.startswith("/"):
            print(f"Unknown command: {raw.split()[0]}. Type /help for commands.")
            continue

        # ── image prefix + VLM turn ───────────────────────────────────────
        image_paths, text = parse_image_prefix(raw)
        if not text:
            text = "Describe this." if image_paths else ""
        if not text and not image_paths:
            continue

        valid_paths: list[str] = []
        for p in image_paths:
            if p.startswith(("http://", "https://")) or Path(p).exists():
                valid_paths.append(p)
            elif p.startswith("$"):
                print(f"Warning: env var not set, skipping: {p}")
            else:
                print(f"Warning: image path not found, skipping: {p}")

        if not image_paths and re.search(r"https?://\S+", text):
            print("Hint: to pass an image use bracket syntax: [https://...] your message")

        try:
            reply = chat.send(text, valid_paths or None)
            print(f"\nAssistant: {reply}\n")
        except RuntimeError as exc:
            print(f"Error: {exc}", file=sys.stderr)


if __name__ == "__main__":
    main()
