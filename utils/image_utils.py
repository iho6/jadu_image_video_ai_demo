"""Load images from local paths or HTTP(S) URLs into PIL RGB images."""

from __future__ import annotations

import io
from pathlib import Path
from typing import Sequence, Tuple, Union

import requests
from PIL import Image

Source = Union[str, Path]


def pil_to_png_bytes(im: Image.Image) -> bytes:
    """Encode a PIL image as PNG bytes."""
    buf = io.BytesIO()
    im.save(buf, format="PNG")
    return buf.getvalue()


def expand_sources_to_three_rgb_images(
    sources: Sequence[str],
) -> Tuple[Image.Image, Image.Image, Image.Image]:
    """
    Load 1–3 paths/URLs and return three RGB images for triple-slot workflows.

    Padding: one image is reused for all three slots; two images use
    (a, b, b); three images use (a, b, c).
    """
    if not (1 <= len(sources) <= 3):
        raise ValueError("sources must contain 1 to 3 items")
    loaded = [load_image(s) for s in sources]
    n = len(loaded)
    if n == 1:
        a = loaded[0]
        return (a, a, a)
    if n == 2:
        a, b = loaded[0], loaded[1]
        return (a, b, b)
    return (loaded[0], loaded[1], loaded[2])


def load_image(source: Source) -> Image.Image:
    """
    Open an image from a local path or http(s) URL and return an RGB PIL Image.
    """
    s = str(source)
    if s.startswith(("http://", "https://")):
        r = requests.get(s, timeout=120)
        r.raise_for_status()
        return Image.open(io.BytesIO(r.content)).convert("RGB")
    return Image.open(s).convert("RGB")
