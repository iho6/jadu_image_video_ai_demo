"""Tests for utils.image_utils.load_image."""

from __future__ import annotations

import io
from unittest.mock import MagicMock, patch

from PIL import Image

from utils.image_utils import (
    expand_sources_to_three_rgb_images,
    load_image,
    pil_to_png_bytes,
)


def _fake_png_bytes() -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (4, 4), color=(10, 20, 30)).save(buf, format="PNG")
    return buf.getvalue()


def test_load_image_local_file(tmp_path):
    path = tmp_path / "x.png"
    Image.new("RGB", (7, 8), color=(1, 2, 3)).save(path)
    img = load_image(str(path))
    assert img.mode == "RGB"
    assert img.size == (7, 8)


@patch("utils.image_utils.requests.get")
def test_load_image_url(mock_get):
    mock_get.return_value.content = _fake_png_bytes()
    mock_get.return_value.raise_for_status = MagicMock()
    img = load_image("https://example.com/a.png")
    assert img.mode == "RGB"
    assert img.size == (4, 4)
    mock_get.assert_called_once_with("https://example.com/a.png", timeout=120)


def test_pil_to_png_bytes_roundtrip():
    im = Image.new("RGB", (2, 3), color=(1, 2, 3))
    b = pil_to_png_bytes(im)
    out = Image.open(io.BytesIO(b))
    assert out.size == (2, 3)


def test_expand_sources_one_image(tmp_path):
    p = tmp_path / "a.png"
    Image.new("RGB", (4, 5)).save(p)
    a, b, c = expand_sources_to_three_rgb_images([str(p)])
    assert a is b is c
    assert a.size == (4, 5)


def test_expand_sources_three_distinct(tmp_path):
    paths = []
    for i, sz in enumerate([(2, 2), (3, 3), (4, 4)]):
        p = tmp_path / f"{i}.png"
        Image.new("RGB", sz).save(p)
        paths.append(str(p))
    a, b, c = expand_sources_to_three_rgb_images(paths)
    assert a.size == (2, 2) and b.size == (3, 3) and c.size == (4, 4)
