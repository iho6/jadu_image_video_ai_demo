"""Character sheet creation (Qwen-Image-Edit-2509 + edit-angle + VLM checks).

This module contains only class-based organization:
- `CharacterSheetCreation`: orchestrates optional full-body generation, 4 angle renders,
  and 3x2 stitching into a character sheet.
"""

from __future__ import annotations

import re
import uuid
from pathlib import Path

from PIL import Image

from qwen_vl import QwenVL
from services.edit_angle_service.edit_angle import run_edit_angle
from services.img_edit_service.img_edit import run_img_edit
from utils.generic_utils import safe_filename_component
from utils.image_utils import load_image
from utils.vlm_utils import character_fullbody_check
from utils.prompt_utils import (
    ANGLE_PROMPT_BACK_180,
    ANGLE_PROMPT_CLOSE_UP,
    ANGLE_PROMPT_LEFT_90,
    ANGLE_PROMPT_RIGHT_90,
    CHARACTER_DESCRIPTION_PROMPT,
    FULLBODY_CHECK_PROMPT,
    MAKE_FULLBODY_PROMPT,
)

class CharacterSheetCreation:
    def __init__(
        self,
        *,
        comfy_url: str = "http://127.0.0.1:8188",
        vlm_runner: QwenVL | None = None,
        target_size: tuple[int, int] = (928, 1664),
    ) -> None:
        self._comfy_url = comfy_url
        self._vlm_runner = vlm_runner or QwenVL()
        self._target_size = target_size

    def fullbody_image_creation(self, image_source: str, output_dir: Path) -> Path:
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)
        pre = self._preprocess_qwen_9_16(image_source, out)
        paths = run_img_edit([str(pre)], MAKE_FULLBODY_PROMPT, out, self._comfy_url)
        if not paths:
            raise RuntimeError("Full-body generation produced no outputs.")
        return Path(paths[0])

    def character_sheet_creation(self, image_source: str, character_name: str, output_dir: Path) -> Path:
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)

        is_fullbody = character_fullbody_check(
            runner=self._vlm_runner,
            image_source=image_source,
            prompt=FULLBODY_CHECK_PROMPT,
        )
        if not is_fullbody:
            return self.fullbody_image_creation(image_source, out)

        pre = self._preprocess_qwen_9_16(image_source, out)

        right = self._run_angle_once(pre, ANGLE_PROMPT_RIGHT_90, out)
        left = self._run_angle_once(pre, ANGLE_PROMPT_LEFT_90, out)
        back = self._run_angle_once(pre, ANGLE_PROMPT_BACK_180, out)
        closeup = self._run_angle_once(pre, ANGLE_PROMPT_CLOSE_UP, out)

        images = [
            Image.open(pre).convert("RGB"),
            Image.open(right).convert("RGB"),
            Image.open(left).convert("RGB"),
            Image.open(back).convert("RGB"),
            Image.open(closeup).convert("RGB"),
        ]
        stitched = self._stitch_3x2_with_blank(images)

        safe_name = safe_filename_component(character_name)
        dest = out / f"{safe_name}_character_sheet.png"
        stitched.save(dest)
        return dest

    def describe_character(self, image_source: str) -> str:
        raw = self._vlm_runner.vl_eval([image_source], CHARACTER_DESCRIPTION_PROMPT)
        text = str(raw).strip()
        if not text:
            raise ValueError("Character description is empty.")
        return text

    def _run_angle_once(self, preprocessed_input: Path, prompt: str, output_dir: Path) -> Path:
        paths = run_edit_angle(
            str(preprocessed_input),
            prompt,
            Path(output_dir),
            comfy_url=self._comfy_url,
        )
        if not paths:
            raise RuntimeError(f"Angle edit produced no outputs for prompt: {prompt!r}")
        return Path(paths[0])

    def _preprocess_qwen_9_16(self, image_source: str, dest_dir: Path) -> Path:
        """Pad-to-fit resize to exact target (default 928x1664) and save PNG."""
        dest = Path(dest_dir)
        dest.mkdir(parents=True, exist_ok=True)
        im = load_image(image_source).convert("RGB")
        tw, th = self._target_size
        sw, sh = im.size
        if sw <= 0 or sh <= 0:
            raise ValueError(f"Invalid image size: {im.size}")

        scale = min(tw / sw, th / sh)
        rw = max(1, int(round(sw * scale)))
        rh = max(1, int(round(sh * scale)))
        resample = getattr(Image, "Resampling", Image).LANCZOS
        resized = im.resize((rw, rh), resample=resample)

        canvas = Image.new("RGB", (tw, th), (0, 0, 0))
        ox = (tw - rw) // 2
        oy = (th - rh) // 2
        canvas.paste(resized, (ox, oy))

        out_path = dest / f"qwen916_{uuid.uuid4().hex}.png"
        canvas.save(out_path)
        return out_path

    def _stitch_3x2_with_blank(
        self,
        images: list[Image.Image],
        bg_color: tuple[int, int, int] = (0, 0, 0),
    ) -> Image.Image:
        if len(images) != 5:
            raise ValueError("Expected exactly 5 images: [original, right, left, back, closeup].")
        tile_w, tile_h = images[0].size
        if tile_w <= 0 or tile_h <= 0:
            raise ValueError(f"Invalid tile size: {(tile_w, tile_h)}")

        resample = getattr(Image, "Resampling", Image).LANCZOS
        tiles = [im.resize((tile_w, tile_h), resample=resample) for im in images]

        canvas = Image.new("RGB", (tile_w * 3, tile_h * 2), bg_color)
        # Row 1: original, right, left
        canvas.paste(tiles[0], (0, 0))
        canvas.paste(tiles[1], (tile_w, 0))
        canvas.paste(tiles[2], (tile_w * 2, 0))
        # Row 2: back, closeup, blank
        canvas.paste(tiles[3], (0, tile_h))
        canvas.paste(tiles[4], (tile_w, tile_h))
        return canvas

