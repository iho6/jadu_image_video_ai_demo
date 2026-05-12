"""CLI for generating a detailed description of a single image or video.

Run from repo root:
    python scripts/run_describe_media.py --input input/room.png
    python scripts/run_describe_media.py --input input/scene_video.mp4
    python scripts/run_describe_media.py --input https://example.com/img.png
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
for _p in (str(_ROOT), str(_ROOT / "code")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from describe_media import describe_media  # noqa: E402
from qwen_vl import QwenVL                # noqa: E402


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate a detailed description of a single image or video.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python scripts/run_describe_media.py --input input/room.png\n"
            "  python scripts/run_describe_media.py --input input/scene_video.mp4\n"
            "  python scripts/run_describe_media.py --input https://example.com/img.png"
        ),
    )
    parser.add_argument(
        "--input",
        required=True,
        metavar="PATH_OR_URL",
        help="Path or URL of the image or video to describe.",
    )
    parser.add_argument(
        "--model-id",
        default=None,
        help="Override model path or HF repo ID (default: QwenVL default).",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)

    kwargs: dict = {}
    if args.model_id:
        kwargs["model_id"] = args.model_id
    runner = QwenVL(**kwargs)

    print(describe_media(runner, args.input))


if __name__ == "__main__":
    main()
