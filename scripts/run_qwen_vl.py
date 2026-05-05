"""
CLI runner for Qwen-VL multi-image evaluation.

Run from repo root:
python scripts/run_qwen_vl.py --images <img1> [<img2> ...] --prompt "..."
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
for _p in (str(_ROOT), str(_ROOT / "code")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from qwen_vl import QwenVL  # noqa: E402

LOGGER = logging.getLogger(__name__)
VIDEO_EXTENSIONS = (".mp4", ".mov", ".mkv", ".avi", ".webm", ".m4v")


def run_vl_eval(args: argparse.Namespace) -> str:
    runner = QwenVL()
    return runner.vl_eval(
        image_sources=args.images or [],
        prompt=args.prompt,
        video_source=args.video,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--images",
        nargs="+",
        default=None,
        help="One or more image sources (local paths or http(s) URLs).",
    )
    parser.add_argument(
        "--video",
        default=None,
        help="Single video source (local path or http(s) URL).",
    )
    parser.add_argument("--prompt", required=True, help="Prompt to evaluate.")
    args = parser.parse_args()
    if not args.prompt.strip():
        parser.error("Prompt must be non-empty.")
    if args.images is None and args.video is None:
        parser.error("At least one of --images or --video must be provided.")
    if args.images is not None and not (1 <= len(args.images) <= 3):
        parser.error("--images must contain between 1 and 3 entries.")
    if args.video is not None:
        video_value = args.video.strip()
        if not video_value:
            parser.error("--video must be non-empty when provided.")
        lower_value = video_value.lower()
        if not lower_value.endswith(VIDEO_EXTENSIONS):
            parser.error(
                "--video must be a recognized video file type "
                "(.mp4, .mov, .mkv, .avi, .webm, .m4v)."
            )
    return args


def main() -> None:
    args = parse_args()
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    )
    try:
        response = run_vl_eval(args)
        print(response)
    except Exception as exc:
        LOGGER.error("Qwen3-VL runner failed: %s", exc)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
