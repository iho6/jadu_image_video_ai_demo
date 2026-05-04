"""Tests for scripts/run_qwen_img_edit.py."""

from __future__ import annotations

import sys
from unittest.mock import MagicMock, patch

import pytest
from PIL import Image

from run_qwen_img_edit import RunQwenImgEdit, main, parse_args


def test_load_images_returns_same_count(tmp_path):
    paths = []
    for i in range(3):
        p = tmp_path / f"{i}.png"
        Image.new("RGB", (2, 2)).save(p)
        paths.append(str(p))
    runner = RunQwenImgEdit.__new__(RunQwenImgEdit)
    out = runner.load_images(paths)
    assert len(out) == 3
    assert all(isinstance(im, Image.Image) for im in out)


def test_load_images_six_paths_raises_without_loading():
    runner = RunQwenImgEdit.__new__(RunQwenImgEdit)
    with pytest.raises(
        ValueError,
        match="Qwen 2511 cannot take more than 5 reference images",
    ):
        runner.load_images([f"{i}.png" for i in range(6)])


@patch("run_qwen_img_edit.QwenImgEdit")
def test_run_calls_editor_with_loaded_images(mock_qie, tmp_path):
    editor = MagicMock()
    editor.edit.return_value = [Image.new("RGB", (1, 1))]
    mock_qie.return_value = editor
    runner = RunQwenImgEdit()
    p = tmp_path / "a.png"
    Image.new("RGB", (2, 2)).save(p)
    kwargs = {
        "num_inference_steps": 40,
        "true_cfg_scale": 4.0,
        "guidance_scale": 1.0,
        "negative_prompt": " ",
        "num_images_per_prompt": 1,
    }
    out = runner.run([str(p)], "edit this", kwargs)
    assert len(out) == 1
    editor.edit.assert_called_once()
    call_kw = editor.edit.call_args
    assert len(call_kw[0][0]) == 1


@patch("run_qwen_img_edit.QwenImgEdit")
def test_run_empty_prompt_raises(mock_qie):
    mock_qie.return_value = MagicMock()
    runner = RunQwenImgEdit()
    with pytest.raises(ValueError, match="Prompt must be non-empty"):
        runner.run(["x.png"], "   ", {})


@patch("run_qwen_img_edit.QwenImgEdit")
def test_run_more_than_five_sources_raises_before_edit(mock_qie):
    mock_qie.return_value = MagicMock()
    runner = RunQwenImgEdit()
    paths = [f"{i}.png" for i in range(6)]
    with pytest.raises(
        ValueError,
        match="Qwen 2511 cannot take more than 5 reference images",
    ):
        runner.run(paths, "ok", {"num_images_per_prompt": 1})


@patch("run_qwen_img_edit.QwenImgEdit")
def test_run_warns_for_four_reference_images(mock_qie, tmp_path):
    mock_qie.return_value = MagicMock()
    mock_qie.return_value.edit.return_value = [Image.new("RGB", (1, 1))]
    runner = RunQwenImgEdit()
    paths = []
    for i in range(4):
        p = tmp_path / f"{i}.png"
        Image.new("RGB", (2, 2)).save(p)
        paths.append(str(p))
    kwargs = {
        "num_inference_steps": 40,
        "true_cfg_scale": 4.0,
        "guidance_scale": 1.0,
        "negative_prompt": " ",
        "num_images_per_prompt": 1,
    }
    with pytest.warns(UserWarning, match="stability decreases"):
        runner.run(paths, "go", kwargs)


def test_save_outputs_writes_readable_pngs(tmp_path):
    runner = RunQwenImgEdit.__new__(RunQwenImgEdit)
    images = [
        Image.new("RGB", (10, 12), color=(50, 100, 150)),
        Image.new("RGB", (8, 8), color=(1, 2, 3)),
    ]
    runner.save_outputs(tmp_path, "out", images)
    p0 = tmp_path / "out_0.png"
    p1 = tmp_path / "out_1.png"
    assert p0.is_file()
    assert p1.is_file()
    r0 = Image.open(p0)
    assert r0.size == (10, 12)
    assert r0.mode == "RGB"


def test_parse_args_rejects_whitespace_prompt(monkeypatch, tmp_path):
    p = tmp_path / "a.png"
    Image.new("RGB", (2, 2)).save(p)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "run_qwen_img_edit.py",
            "--images",
            str(p),
            "--prompt",
            "   ",
        ],
    )
    with pytest.raises(SystemExit):
        parse_args()


@patch("run_qwen_img_edit.RunQwenImgEdit")
def test_main_invokes_run_and_save(mock_runner_cls, tmp_path, monkeypatch):
    inst = MagicMock()
    mock_runner_cls.return_value = inst
    inst.run.return_value = [Image.new("RGB", (2, 2))]
    img_path = tmp_path / "in.png"
    Image.new("RGB", (2, 2)).save(img_path)
    out_dir = tmp_path / "out"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "run_qwen_img_edit.py",
            "--images",
            str(img_path),
            "--prompt",
            "go",
            "--output-dir",
            str(out_dir),
        ],
    )
    main()
    inst.run.assert_called_once()
    inst.save_outputs.assert_called_once()
