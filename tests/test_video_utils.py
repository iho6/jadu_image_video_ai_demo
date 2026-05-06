"""Tests for utils/video_utils.py."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import hashlib

import pytest

from utils import video_utils


def test_needs_normalization_extensionless_url():
    assert video_utils.needs_normalization(
        "https://example.com/videos/asset-ee0e77cc-d735-4d35-bcbe-ef89eaa23789"
    )


def test_needs_normalization_mp4_url():
    assert not video_utils.needs_normalization("https://example.com/clip.mp4")


def test_needs_normalization_mp4_url_with_query():
    assert not video_utils.needs_normalization(
        "https://example.com/clip.mp4?token=abc&x=1"
    )


def test_needs_normalization_local_gif():
    assert video_utils.needs_normalization("/tmp/x.gif")


def test_needs_normalization_local_mp4():
    assert not video_utils.needs_normalization("/tmp/x.mp4")


def test_prepare_video_supported_url_unchanged(tmp_path):
    url = "https://cdn.example.com/a/file.mp4"
    assert video_utils.prepare_video_for_vl(url, cache_dir=tmp_path) == url


def test_prepare_video_url_download_and_transcode(tmp_path, monkeypatch):
    url = "https://example.com/videos/no-extension-id"
    key = hashlib.sha256(url.encode()).hexdigest()[:16]
    expected_out = tmp_path / f"url_{key}.mp4"

    def fake_run(cmd, **kwargs):
        assert "ffmpeg" in cmd[0] or cmd[0] == "ffmpeg"
        dst = Path(cmd[-1])
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes(b"fake-mp4")
        return MagicMock(returncode=0)

    monkeypatch.setattr(video_utils.shutil, "which", lambda _: "/usr/bin/ffmpeg")
    monkeypatch.setattr(video_utils.subprocess, "run", fake_run)

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

        def raise_for_status(self):
            return None

        def iter_content(self, chunk_size=1024):
            yield b"fakevid"

    def fake_get(u, **kw):
        assert u == url
        assert kw.get("stream") is True
        return FakeResponse()

    monkeypatch.setattr(video_utils.requests, "get", fake_get)

    result = video_utils.prepare_video_for_vl(url, cache_dir=tmp_path)
    assert result == str(expected_out.resolve())
    assert expected_out.is_file()


def test_prepare_video_url_cache_hit(tmp_path, monkeypatch):
    url = "https://example.com/videos/x"
    key = hashlib.sha256(url.encode()).hexdigest()[:16]
    out = tmp_path / f"url_{key}.mp4"
    out.write_bytes(b"cached")

    called = []

    def fake_run(*a, **k):
        called.append(1)
        raise AssertionError("ffmpeg should not run on cache hit")

    monkeypatch.setattr(video_utils.subprocess, "run", fake_run)
    result = video_utils.prepare_video_for_vl(url, cache_dir=tmp_path)
    assert result == str(out.resolve())
    assert not called


def test_prepare_video_local_supported(tmp_path):
    f = tmp_path / "a.mp4"
    f.write_bytes(b"x")
    assert video_utils.prepare_video_for_vl(str(f), cache_dir=tmp_path) == str(
        f.resolve()
    )


def test_prepare_video_local_transcode(tmp_path, monkeypatch):
    src = tmp_path / "weird.bin"
    src.write_bytes(b"not-really-video")

    def fake_run(cmd, **kwargs):
        dst = Path(cmd[-1])
        dst.write_bytes(b"out")
        return MagicMock(returncode=0)

    monkeypatch.setattr(video_utils.shutil, "which", lambda _: "/usr/bin/ffmpeg")
    monkeypatch.setattr(video_utils.subprocess, "run", fake_run)

    result = video_utils.prepare_video_for_vl(str(src), cache_dir=tmp_path)
    assert result.endswith(".mp4")
    assert Path(result).is_file()


def test_require_ffmpeg_missing(monkeypatch):
    monkeypatch.setattr(video_utils.shutil, "which", lambda _: None)
    with pytest.raises(RuntimeError, match="ffmpeg"):
        video_utils.require_ffmpeg()
