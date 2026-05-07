"""
CLI: reference-guided Qwen image edit using @CharacterName prompt tokens.

Example:

    python scripts/run_ref_guided_gen.py ^
      --prompt "@Eli sitting on the couch, staring at @Beth's phone" ^
      --backdrop-img path/or/url/to/scene.png ^
      --output-dir output/ref-guided-gen
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
for _p in (str(_ROOT), str(_ROOT / "code")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from ref_guided_gen import RefGuidedGen  # type: ignore[import-not-found]  # noqa: E402
from services.img_edit_service.img_edit import DEFAULT_COMFY_URL, run_img_edit  # noqa: E402
from utils.cli_exceptions import print_cli_error  # noqa: E402
from utils.comfyui_utils import ComfyPromptError  # noqa: E402


class RunRefGuidedGen:
    def __init__(
        self,
        *,
        storage_root: Path = Path("storage"),
    ) -> None:
        self._gen = RefGuidedGen(storage_root=storage_root)

    def run(
        self,
        *,
        prompt: str,
        backdrop_img: str | None,
        output_dir: Path,
    ) -> list[Path]:
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)
        raw_prompt = str(prompt)
        # If a backdrop is provided, use its slot for the latent canvas size; otherwise force 16:9.
        char_count = len(self._gen.parse_character_refs(raw_prompt))
        has_backdrop = backdrop_img is not None and str(backdrop_img).strip() != ""
        if has_backdrop:
            # build_images_and_prompt orders images as: [char1, (char2), (backdrop)]
            latent_source = "image2" if char_count == 1 else "image3"
        else:
            latent_source = "empty_16_9"
        images, rewritten_prompt = self._gen.build_images_and_prompt(
            prompt=raw_prompt,
            backdrop_img=backdrop_img,
        )
        print("combined_prompt:\n" + rewritten_prompt)
        return run_img_edit(
            images,
            rewritten_prompt,
            out,
            comfy_url=DEFAULT_COMFY_URL,
            latent_source=latent_source,
        )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run Qwen image edit with reference-guided character inputs from "
            "@CharacterName prompt tokens. Supports up to 2 unique @CharacterName "
            "references plus an optional backdrop (max 3 images total)."
        )
    )
    parser.add_argument(
        "--prompt",
        required=True,
        help="Edit instruction containing 1–2 @CharacterName references (non-empty).",
    )
    parser.add_argument(
        "--backdrop-img",
        default=None,
        metavar="PATH_OR_URL",
        help="Optional scene/backdrop reference (local path or http(s) URL).",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("output") / "ref-guided-gen",
        help="Directory for downloaded PNG outputs (default: output/ref-guided-gen).",
    )
    args = parser.parse_args(argv)
    if not str(args.prompt).strip():
        parser.error("--prompt must be non-empty.")
    if args.backdrop_img is not None and not str(args.backdrop_img).strip():
        parser.error("--backdrop-img must be non-empty when provided.")
    return args


def main() -> None:
    args = parse_args()
    try:
        paths = RunRefGuidedGen().run(
            prompt=str(args.prompt),
            backdrop_img=(str(args.backdrop_img) if args.backdrop_img is not None else None),
            output_dir=Path(args.output_dir),
        )
        for p in paths:
            print("saved", p.resolve())
    except (ComfyPromptError, FileNotFoundError, OSError, TimeoutError, ValueError, RuntimeError) as e:
        print_cli_error(e)
        raise SystemExit(1) from e


if __name__ == "__main__":
    main()

