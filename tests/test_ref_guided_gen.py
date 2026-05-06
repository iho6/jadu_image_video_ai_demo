from __future__ import annotations

from pathlib import Path

import pytest

from ref_guided_gen import RefGuidedGen


def test_parse_character_refs_order_and_dedup():
    g = RefGuidedGen()
    names = g.parse_character_refs("@Eli sits with @Beth. @Eli looks at @Beth.")
    assert names == ["Eli", "Beth"]


def test_rewrite_prompt_with_indices_possessive():
    g = RefGuidedGen()
    out = g.rewrite_prompt_with_indices(
        "@Eli sitting on the couch, staring at @Beth's phone",
        ["Eli", "Beth"],
    )
    assert "Character in image 1" in out
    assert "Character in image 2's phone" in out


def test_build_adds_backdrop_as_next_index(tmp_path: Path):
    storage = tmp_path / "storage"
    (storage / "Eli").mkdir(parents=True)
    (storage / "Beth").mkdir(parents=True)
    (storage / "Eli" / "Eli_character_sheet.png").write_bytes(b"x")
    (storage / "Beth" / "Beth_character_sheet.png").write_bytes(b"x")

    g = RefGuidedGen(storage_root=storage)
    images, rewritten = g.build_images_and_prompt(
        prompt="@Eli sitting on the couch, staring at @Beth's phone",
        backdrop_img="https://example.com/backdrop.png",
    )
    assert images[0].endswith("Eli_character_sheet.png")
    assert images[1].endswith("Beth_character_sheet.png")
    assert images[2] == "https://example.com/backdrop.png"
    assert "Use image 3 as the scene/backdrop reference." in rewritten
    assert "the same as in the 2 image reference(s)." in rewritten


def test_build_errors_on_three_character_refs(tmp_path: Path):
    storage = tmp_path / "storage"
    for name in ("A", "B", "C"):
        (storage / name).mkdir(parents=True)
        (storage / name / f"{name}_character_sheet.png").write_bytes(b"x")
    g = RefGuidedGen(storage_root=storage)
    with pytest.raises(ValueError, match=r"Only 2 unique @CharacterName references are supported"):
        g.build_images_and_prompt(prompt="@A @B @C", backdrop_img=None)


def test_missing_character_sheet_raises(tmp_path: Path):
    storage = tmp_path / "storage"
    (storage / "Eli").mkdir(parents=True)
    g = RefGuidedGen(storage_root=storage)
    with pytest.raises(FileNotFoundError) as exc:
        g.build_images_and_prompt(prompt="@Eli waves", backdrop_img=None)
    assert "Expected:" in str(exc.value)


def test_ref_guided_gen_has_no_run_method():
    g = RefGuidedGen()
    assert not hasattr(g, "run")

