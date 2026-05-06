"""Generic shared helpers.

This module intentionally stays small and dependency-light so it can be imported
from both runtime code (`code/`) and CLI scripts (`scripts/`).
"""

from __future__ import annotations

import re

_SAFE_FILENAME_EMPTY = "safe_filename error: input text must be non-empty."


def safe_filename_component(text: str) -> str:
    """
    Normalize arbitrary user text into a safe single-path-component string.

    Rules mirror existing call sites:
    - strip whitespace; error if empty
    - replace slashes with underscores
    - collapse whitespace to underscores
    - remove everything except A-Za-z0-9._-
    - if cleanup removes all characters, fall back to 'character'
    """
    s = (text or "").strip()
    if not s:
        raise ValueError(_SAFE_FILENAME_EMPTY)
    s = s.replace("\\", "_").replace("/", "_")
    s = re.sub(r"\s+", "_", s)
    s = re.sub(r"[^A-Za-z0-9._-]", "", s)
    return s or "character"

