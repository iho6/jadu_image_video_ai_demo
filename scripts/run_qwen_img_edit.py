"""
CLI for Qwen-Image-Edit Plus: --images (one or more), --prompt, --output-dir.

Run from repo root: python scripts/run_qwen_img_edit.py ...
"""

from __future__ import annotations

import argparse
import sys
import warnings
from pathlib import Path
from typing import List, Sequence

from PIL import Image

_ROOT = Path(__file__).resolve().parents[1]
for _p in (str(_ROOT), str(_ROOT / "code")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from utils.image_utils import load_image  # noqa: E402
from qwen_img_edit import QwenImgEdit  # noqa: E402

_DEFAULT_MODEL = "Qwen/Qwen-Image-Edit-2511"


class RunQwenImgEdit:
    """Resolve paths/URLs to PIL; call QwenImgEdit; save outputs."""

    def __init__(self, model_id: str = _DEFAULT_MODEL) -> None:
        self._editor = QwenImgEdit(model_id=model_id)

    def load_images(self, sources: Sequence[str]) -> List[Image.Image]:
        # Qwen 2511 reference limits before loading paths/URLs (fail fast if n > 5).
        n = len(sources)
        if n > 5:
            raise ValueError(
                "Qwen 2511 cannot take more than 5 reference images"
            )
        if 4 <= n <= 5:
            warnings.warn(
                "Warning, while Qwen 2511 can handle up to five images, "
                "stability decreases above 3",
                UserWarning,
                stacklevel=2,
            )
        return [load_image(s) for s in sources]

    def run(
        self,
        image_sources: Sequence[str],
        prompt: str,
        inference_kwargs: dict,
    ) -> List[Image.Image]:
        if not prompt.strip():
            raise ValueError("Prompt must be non-empty.")
        pils = self.load_images(image_sources)
        return self._editor.edit(pils, prompt, **inference_kwargs)

    def save_outputs(
        self, out_dir: Path, stem: str, images: List[Image.Image]
    ) -> None:
        out_dir.mkdir(parents=True, exist_ok=True)
        for j, im in enumerate(images):
            path = out_dir / f"{stem}_{j}.png"
            im.save(path)
            print("saved", path.resolve())


def main() -> None:
    args = parse_args()
    runner = RunQwenImgEdit()

    # Inference defaults match models/qwen_image/README.md (Qwen-Image-Edit-2511 snippet):
    # num_inference_steps=40, true_cfg_scale=4.0, guidance_scale=1.0, negative_prompt=" ".
    # seed omitted here → QwenImgEdit uses a random seed each run (README demos use a fixed
    # generator only for reproducibility; no single canonical app default).
    kwargs = {
        "num_inference_steps": 40,
        "true_cfg_scale": 4.0,
        "guidance_scale": 1.0,
        "negative_prompt": " ",
        "num_images_per_prompt": 1,  # number of images outputted
    }

    outs = runner.run(args.images, args.prompt, kwargs)
    runner.save_outputs(args.output_dir, "out", outs)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument(
        "--images",
        nargs="+",
        required=True,
        help="Reference image paths or http(s) URLs.",
    )
    p.add_argument("--prompt", required=True, help="Edit instruction.")
    p.add_argument(
        "--output-dir",
        type=Path,
        default=Path("output/qwen_edits"),
        help="Directory for PNG outputs.",
    )
    args = p.parse_args()
    if not args.prompt.strip():
        p.error("Prompt must be non-empty.")
    return args


if __name__ == "__main__":
    main()
