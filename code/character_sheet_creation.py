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
from utils.generic_utils import safe_filename_component, section
from utils.image_utils import load_image, save_source_image_as_png
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

    def character_sheet_creation(
        self,
        image_source: str,
        character_name: str,
        output_dir: Path,
        *,
        full_body_check: bool = False,
    ) -> Path:
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)

        if full_body_check:
            with section("step: full-body-check (QwenVL)"):
                is_fullbody = character_fullbody_check(
                    runner=self._vlm_runner,
                    image_source=image_source,
                    prompt=FULLBODY_CHECK_PROMPT,
                )
            if not is_fullbody:
                with section("step: full-body-correction (Comfy img_edit)"):
                    return self.fullbody_image_creation(image_source, out)

        # Preserve original input dimensions to avoid padding artifacts.
        pre = save_source_image_as_png(image_source, out, prefix="input")

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
        stitched = self._stitch_square_plus_closeup(images)

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

    @staticmethod
    def _letterbox_fit(
        im: Image.Image,
        target_w: int,
        target_h: int,
        bg_color: tuple[int, int, int],
    ) -> Image.Image:
        """Scale ``im`` to fit inside ``(target_w, target_h)`` preserving aspect ratio,
        then centre it on a background canvas of that size.  No stretching occurs."""
        resample = getattr(Image, "Resampling", Image).LANCZOS
        iw, ih = im.size
        scale = min(target_w / iw, target_h / ih)
        rw = max(1, int(round(iw * scale)))
        rh = max(1, int(round(ih * scale)))
        scaled = im.resize((rw, rh), resample=resample)
        canvas = Image.new("RGB", (target_w, target_h), bg_color)
        ox = (target_w - rw) // 2
        oy = (target_h - rh) // 2
        canvas.paste(scaled, (ox, oy))
        return canvas

    def _stitch_square_plus_closeup(
        self,
        images: list[Image.Image],
        bg_color: tuple[int, int, int] = (0, 0, 0),
    ) -> Image.Image:
        if len(images) != 5:
            raise ValueError("Expected exactly 5 images: [original, right, left, back, closeup].")
        front, right, left, back, closeup = images

        # Use the first generated angle output as the canonical tile size so that
        # no generated tile is ever stretched (they share the same workflow/resolution).
        tile_w, tile_h = right.size
        if tile_w <= 0 or tile_h <= 0:
            raise ValueError(f"Invalid tile size from generated output: {(tile_w, tile_h)}")

        # Letterbox-fit each image into the canonical tile box — preserves aspect ratio.
        front_t = self._letterbox_fit(front, tile_w, tile_h, bg_color)
        right_t = self._letterbox_fit(right, tile_w, tile_h, bg_color)
        left_t = self._letterbox_fit(left, tile_w, tile_h, bg_color)
        back_t = self._letterbox_fit(back, tile_w, tile_h, bg_color)

        square_w = tile_w * 2
        square_h = tile_h * 2

        # Closeup: letterbox-fit into a column whose height equals the 2×2 square.
        cw, ch = closeup.size
        if cw <= 0 or ch <= 0:
            raise ValueError(f"Invalid closeup size: {(cw, ch)}")
        closeup_col_w = max(1, int(round(cw * (square_h / ch))))
        closeup_t = self._letterbox_fit(closeup, closeup_col_w, square_h, bg_color)

        # 2×2 grid layout (top-left: front, top-right: left-side, bottom-left: right-side, bottom-right: back)
        canvas = Image.new("RGB", (square_w + closeup_col_w, square_h), bg_color)
        canvas.paste(front_t, (0, 0))
        canvas.paste(left_t, (tile_w, 0))
        canvas.paste(right_t, (0, tile_h))
        canvas.paste(back_t, (tile_w, tile_h))
        canvas.paste(closeup_t, (square_w, 0))
        return canvas

