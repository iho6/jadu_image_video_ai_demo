"""
CLI: enhance an image-edit user prompt with Qwen3-VL using the polish-edit template.

Run from repo root::

    python scripts/run_enhance_edit_prompt.py --prompt "add a cat" --images path/to/img.jpg

**Images:** pass 1–3 paths or URLs (same practical cap as ``run_qwen_vl.py``).

**Model output:** the template asks for JSON with a ``Rewritten`` string; this script
prints that enhanced prompt on stdout (normalized to a single line).
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

from enhance_edit_prompt import EnhanceEditPrompt  # noqa: E402

LOGGER = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Enhance an edit instruction using Qwen3-VL and 1–3 images. "
            "The model should return JSON with a 'Rewritten' field; the enhanced "
            "prompt is printed to stdout."
        ),
    )
    parser.add_argument(
        "--prompt",
        required=True,
        help="Short user instruction to enhance (non-empty).",
    )
    parser.add_argument(
        "--images",
        nargs="+",
        required=True,
        help="1–3 image sources (local paths or http(s) URLs).",
    )
    args = parser.parse_args()
    if not args.prompt.strip():
        parser.error("--prompt must be non-empty.")
    if not (1 <= len(args.images) <= 3):
        parser.error("--images must list between 1 and 3 entries.")
    for i, img in enumerate(args.images):
        if not img.strip():
            parser.error(f"--images entry {i + 1} must be non-empty.")
    return args


def main() -> None:
    args = parse_args()
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    )
    try:
        enhanced = EnhanceEditPrompt().run_enhance_edit_prompt(
            args.prompt,
            args.images,
        )
        print(enhanced)
    except (ValueError, RuntimeError) as exc:
        print(exc, file=sys.stderr)
        raise SystemExit(1) from exc
    except Exception as exc:
        LOGGER.exception("Enhance edit prompt failed")
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
