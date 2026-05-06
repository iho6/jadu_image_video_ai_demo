"""CLI contract tests for scripts/run_qwen_vl.py."""

from __future__ import annotations

import importlib
import os
from pathlib import Path
import subprocess
import sys
import types
from unittest.mock import MagicMock

import pytest

_ROOT = Path(__file__).resolve().parents[1]


def _load_runner_module(monkeypatch):
    fake_qwen_vl = types.ModuleType("qwen_vl")
    fake_qwen_vl.last_qwen_vl_kwargs = None

    class _DummyQwenVL:
        def __init__(self, *args, **kwargs):
            fake_qwen_vl.last_qwen_vl_kwargs = dict(kwargs)

        def vl_eval(self, image_sources, prompt, video_source=None):
            assert isinstance(image_sources, list)
            assert isinstance(prompt, str)
            return "ok"

    fake_qwen_vl.QwenVL = _DummyQwenVL
    monkeypatch.setitem(sys.modules, "qwen_vl", fake_qwen_vl)

    import run_qwen_vl

    return importlib.reload(run_qwen_vl)


def test_parse_args_accepts_images_only(monkeypatch):
    run_qwen_vl = _load_runner_module(monkeypatch)
    monkeypatch.setattr(
        sys,
        "argv",
        ["run_qwen_vl.py", "--images", "a.png", "--prompt", "describe"],
    )
    args = run_qwen_vl.parse_args()
    assert args.images == ["a.png"]
    assert args.video is None


def test_run_vl_eval_uses_qwen_vl_without_kwargs(monkeypatch):
    run_qwen_vl = _load_runner_module(monkeypatch)
    monkeypatch.setattr(
        sys,
        "argv",
        ["run_qwen_vl.py", "--images", "a.png", "--prompt", "describe"],
    )
    out = run_qwen_vl.run_vl_eval(run_qwen_vl.parse_args())
    assert out == "ok"
    assert sys.modules["qwen_vl"].last_qwen_vl_kwargs == {}


def test_parse_args_accepts_video_only(monkeypatch):
    run_qwen_vl = _load_runner_module(monkeypatch)
    monkeypatch.setattr(
        sys,
        "argv",
        ["run_qwen_vl.py", "--video", "clip.mp4", "--prompt", "describe"],
    )
    args = run_qwen_vl.parse_args()
    assert args.images is None
    assert args.video == "clip.mp4"


def test_parse_args_accepts_images_and_video(monkeypatch):
    run_qwen_vl = _load_runner_module(monkeypatch)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "run_qwen_vl.py",
            "--images",
            "a.png",
            "b.png",
            "--video",
            "https://example.com/clip.webm",
            "--prompt",
            "describe",
        ],
    )
    args = run_qwen_vl.parse_args()
    assert args.images == ["a.png", "b.png"]
    assert args.video == "https://example.com/clip.webm"


def test_parse_args_rejects_missing_images_and_video(monkeypatch):
    run_qwen_vl = _load_runner_module(monkeypatch)
    monkeypatch.setattr(
        sys,
        "argv",
        ["run_qwen_vl.py", "--prompt", "describe"],
    )
    with pytest.raises(SystemExit):
        run_qwen_vl.parse_args()


def test_parse_args_rejects_more_than_three_images(monkeypatch):
    run_qwen_vl = _load_runner_module(monkeypatch)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "run_qwen_vl.py",
            "--images",
            "a.png",
            "b.png",
            "c.png",
            "d.png",
            "--prompt",
            "describe",
        ],
    )
    with pytest.raises(SystemExit):
        run_qwen_vl.parse_args()


def test_parse_args_rejects_empty_prompt(monkeypatch):
    run_qwen_vl = _load_runner_module(monkeypatch)
    monkeypatch.setattr(
        sys,
        "argv",
        ["run_qwen_vl.py", "--images", "a.png", "--prompt", "   "],
    )
    with pytest.raises(SystemExit):
        run_qwen_vl.parse_args()


def test_parse_args_accepts_extensionless_video_url(monkeypatch):
    run_qwen_vl = _load_runner_module(monkeypatch)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "run_qwen_vl.py",
            "--video",
            "https://example.com/videos/asset-abc",
            "--prompt",
            "describe",
        ],
    )
    args = run_qwen_vl.parse_args()
    assert args.video == "https://example.com/videos/asset-abc"


def test_parse_args_accepts_odd_local_video_extension(monkeypatch):
    run_qwen_vl = _load_runner_module(monkeypatch)
    monkeypatch.setattr(
        sys,
        "argv",
        ["run_qwen_vl.py", "--video", "clip.txt", "--prompt", "describe"],
    )
    args = run_qwen_vl.parse_args()
    assert args.video == "clip.txt"


def test_main_normalizes_video_before_vl_eval(monkeypatch):
    run_qwen_vl = _load_runner_module(monkeypatch)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "run_qwen_vl.py",
            "--video",
            "https://example.com/no-ext",
            "--prompt",
            "hi",
        ],
    )

    def fake_prepare(ref, *, cache_dir):
        assert ref == "https://example.com/no-ext"
        return "/normalized/cache.mp4"

    monkeypatch.setattr(run_qwen_vl, "prepare_video_for_vl", fake_prepare)

    seen = {}

    def fake_run_vl_eval(args):
        seen["video"] = args.video
        return "model-output"

    monkeypatch.setattr(run_qwen_vl, "run_vl_eval", fake_run_vl_eval)
    monkeypatch.setattr("builtins.print", lambda *_a, **_k: None)

    run_qwen_vl.main()
    assert seen["video"] == "/normalized/cache.mp4"


def test_main_logs_traceback_on_failure(monkeypatch):
    run_qwen_vl = _load_runner_module(monkeypatch)
    monkeypatch.setattr(
        sys,
        "argv",
        ["run_qwen_vl.py", "--images", "a.png", "--prompt", "describe"],
    )

    def boom(_args):
        raise RuntimeError("boom")

    fake_logger = MagicMock()
    monkeypatch.setattr(run_qwen_vl, "LOGGER", fake_logger)
    monkeypatch.setattr(run_qwen_vl, "run_vl_eval", boom)

    with pytest.raises(SystemExit) as excinfo:
        run_qwen_vl.main()
    assert excinfo.value.code == 1
    fake_logger.exception.assert_called_once_with("Qwen3-VL runner failed")


@pytest.mark.skipif(
    os.getenv("RUN_VL_SMOKE") != "1",
    reason="Set RUN_VL_SMOKE=1 to run Qwen-VL smoke test.",
)
def test_run_qwen_vl_smoke_real_inference():
    cmd = [
        sys.executable,
        "scripts/run_qwen_vl.py",
        "--images",
        "https://qianwen-res.oss-cn-beijing.aliyuncs.com/Qwen-VL/assets/demo.jpeg",
        "--prompt",
        "Describe this image.",
    ]
    proc = subprocess.run(
        cmd,
        cwd=_ROOT,
        capture_output=True,
        text=True,
        timeout=600,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.strip()
