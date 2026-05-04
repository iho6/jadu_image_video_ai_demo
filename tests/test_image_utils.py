"""Tests for utils.image_utils.load_image."""

from __future__ import annotations

import io
from unittest.mock import MagicMock, patch

from PIL import Image

from utils.image_utils import load_image


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
