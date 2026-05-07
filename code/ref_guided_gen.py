"""Reference-guided image edit generation.

Parse @CharacterName mentions in an edit prompt, map them to character sheet
images created by character sheet creation, and call the Qwen image edit
workflow with predictable image slot ordering.
"""

from __future__ import annotations

import re
from pathlib import Path

from utils.generic_utils import safe_filename_component
from utils.prompt_utils import append_reference_constraints

# Allow segment-delimited dots (e.g. @team.alice) but never capture trailing punctuation.
_CHAR_REF_RE = re.compile(r"@([A-Za-z0-9_-]+(?:\.[A-Za-z0-9_-]+)*)")


class RefGuidedGen:
    """Resolve @Name references into character sheet image inputs for img_edit."""

    def __init__(
        self,
        *,
        storage_root: Path = Path("storage"),
        max_character_refs: int = 2,
    ) -> None:
        self._storage_root = Path(storage_root)
        self._max_character_refs = int(max_character_refs)

    def parse_character_refs(self, prompt: str) -> list[str]:
        """Return unique @Name refs in left-to-right order (first occurrence wins)."""
        text = str(prompt)
        seen: set[str] = set()
        ordered: list[str] = []
        for m in _CHAR_REF_RE.finditer(text):
            name = m.group(1)
            if name not in seen:
                seen.add(name)
                ordered.append(name)
        return ordered

    def resolve_character_sheet_paths(self, names_in_order: list[str]) -> list[Path]:
        if not names_in_order:
            raise ValueError("No @CharacterName references found in --prompt.")
        paths: list[Path] = []
        for name in names_in_order:
            n = (name or "").strip()
            safe = safe_filename_component(n)
            p = (self._storage_root / n) / f"{safe}_character_sheet.png"
            if not p.exists():
                raise FileNotFoundError(
                    f"Missing character sheet for {name!r}. Expected: {p}. "
                    f"Create it first via scripts/run_character_sheet_creation.py "
                    f"--character-name {name!r}."
                )
            paths.append(p)
        return paths

    #refactor at later time to prompt utils
    def rewrite_prompt_with_indices(self, prompt: str, names_in_order: list[str]) -> str:
        """Replace @Name tokens with 'Character in image <idx>' based on parse order."""
        if not names_in_order:
            raise ValueError("names_in_order must be non-empty.")
        name_to_idx = {name: i + 1 for i, name in enumerate(names_in_order)}

        def repl(m: re.Match[str]) -> str:
            name = m.group(1)
            idx = name_to_idx.get(name)
            if idx is None:
                return m.group(0)
            return f"Character in image {idx}"

        return _CHAR_REF_RE.sub(repl, str(prompt))

    def build_images_and_prompt(
        self,
        *,
        prompt: str,
        backdrop_img: str | None,
    ) -> tuple[list[str], str]:
        raw_prompt = str(prompt or "")
        if not raw_prompt.strip():
            raise ValueError("--prompt must be non-empty.")

        names = self.parse_character_refs(raw_prompt)
        if not names:
            raise ValueError("No @CharacterName references found in --prompt.")
        if len(names) > self._max_character_refs:
            raise ValueError(
                f"Only {self._max_character_refs} unique @CharacterName references are supported "
                f"(found {len(names)}: {names})."
            )

        sheets = self.resolve_character_sheet_paths(names)

        images: list[str] = [str(p) for p in sheets]
        backdrop_idx: int | None = None
        if backdrop_img is not None and str(backdrop_img).strip():
            images.append(str(backdrop_img).strip())
            backdrop_idx = len(names) + 1

        if len(images) > 3:
            raise ValueError(
                f"Too many images for img_edit workflow (max 3). "
                f"Got {len(images)}: {images}"
            )

        rewritten = self.rewrite_prompt_with_indices(raw_prompt, names)
        rewritten = append_reference_constraints(
            rewritten,
            character_ref_count=len(names),
            backdrop_idx=backdrop_idx,
        )
        return images, rewritten

