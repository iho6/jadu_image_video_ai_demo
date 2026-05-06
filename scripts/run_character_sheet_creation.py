"""
CLI runner for character sheet creation.

If the input is not full-body, this script generates a corrected full-body image,
prints its path, and exits non-zero with an explanatory message.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
for _p in (str(_ROOT), str(_ROOT / "code")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from character_sheet_creation import CharacterSheetCreation  # type: ignore[import-not-found]  # noqa: E402
from utils.comfyui_utils import ComfyPromptError  # noqa: E402
from utils.generic_utils import safe_filename_component  # noqa: E402


class RunCharacterSheetCreation:
    """Run helpers for the character sheet CLI."""

    def __init__(
        self,
        *,
        comfy_url: str,
        target_size: tuple[int, int] = (928, 1664),
    ) -> None:
        self._comfy_url = str(comfy_url)
        self._target_size = target_size
        self._creator = CharacterSheetCreation(
            comfy_url=self._comfy_url,
            target_size=self._target_size,
        )

    def run_describe_character(self, *, image: str) -> str:
        return self._creator.describe_character(str(image))

    def run_character_sheet_creation(
        self,
        *,
        image: str,
        character_name: str,
        output_dir: Path,
    ) -> Path:
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)
        return self._creator.character_sheet_creation(str(image), str(character_name), out)

    def run_fullbody_image_creation(
        self,
        *,
        image: str,
        output_dir: Path,
    ) -> Path:
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)
        return self._creator.fullbody_image_creation(str(image), out)

    def expected_sheet_path(self, *, output_dir: Path, character_name: str) -> Path:
        out = Path(output_dir)
        safe = safe_filename_component(str(character_name))
        return out / f"{safe}_character_sheet.png"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create a 5-view character sheet from one image."
    )
    parser.add_argument(
        "--image",
        required=True,
        metavar="PATH_OR_URL",
        help="Reference character image (local path or http(s) URL).",
    )
    parser.add_argument(
        "--character-name",
        required=True,
        help="Character name used for output directory and final filename.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Output directory (default: storage/<character-name>).",
    )
    parser.add_argument(
        "--comfy-url",
        default="http://127.0.0.1:8188",
        help="ComfyUI base URL (default: http://127.0.0.1:8188).",
    )
    parser.add_argument(
        "--character-description",
        action="store_true",
        help="When set, generate and save <character_name>_character_description.json via VLM.",
    )

    args = parser.parse_args(argv)
    if not str(args.image).strip():
        parser.error("--image must be non-empty.")
    if not str(args.character_name).strip():
        parser.error("--character-name must be non-empty.")
    if args.output_dir is None:
        args.output_dir = Path("storage") / str(args.character_name).strip()
    return args


def main() -> None:
    args = parse_args()
    try:
        runner = RunCharacterSheetCreation(comfy_url=args.comfy_url)
        safe_name = safe_filename_component(str(args.character_name))
        desc_json_path = Path(args.output_dir) / f"{safe_name}_character_description.json"

        path = runner.run_character_sheet_creation(
            image=args.image,
            character_name=args.character_name,
            output_dir=Path(args.output_dir),
        )

        expected = runner.expected_sheet_path(
            output_dir=Path(args.output_dir),
            character_name=args.character_name,
        )
        if path.resolve() != expected.resolve():
            # Non-fullbody branch: create fullbody image, print it, then exit 1.
            fb = runner.run_fullbody_image_creation(
                image=args.image,
                output_dir=Path(args.output_dir),
            )
            if args.character_description:
                desc = runner.run_describe_character(image=str(fb))
                payload = {
                    "character_name": str(args.character_name),
                    "image_described": str(fb),
                    "description": desc,
                }
                desc_json_path.write_text(
                    json.dumps(payload, ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )
            print(fb.resolve())
            print(
                "character sheet creation requires fullbody input of a character.",
                file=sys.stderr,
            )
            raise SystemExit(1)

        if args.character_description:
            desc = runner.run_describe_character(image=str(args.image))
            payload = {
                "character_name": str(args.character_name),
                "image_described": str(args.image),
                "description": desc,
                "character_sheet_path": str(path),
            }
            desc_json_path.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        print(path.resolve())
    except (ComfyPromptError, OSError, TimeoutError, ValueError, RuntimeError) as e:
        print(f"error: {e}", file=sys.stderr)
        raise SystemExit(1) from e


if __name__ == "__main__":
    main()

