"""Load images from local paths or HTTP(S) URLs into PIL RGB images."""

from __future__ import annotations

import io
from pathlib import Path
from typing import Union

import requests
from PIL import Image

Source = Union[str, Path]


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
