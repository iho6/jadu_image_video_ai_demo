from __future__ import annotations

import pytest

from utils.generic_utils import safe_filename_component


def test_safe_filename_component_rejects_empty():
    with pytest.raises(ValueError, match=r"^safe_filename error: input text must be non-empty\.$"):
        safe_filename_component("   ")


def test_safe_filename_component_sanitizes_text():
    assert safe_filename_component("  A/B  C!  ") == "A_B_C"

