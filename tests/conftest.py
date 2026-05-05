"""Pytest: path setup; ensure QwenImageEditPlusPipeline exists for imports (stub if missing)."""

from __future__ import annotations

import sys
import types
from pathlib import Path

try:
    import diffusers as _diffusers
except ImportError:
    _diffusers = None

if _diffusers is not None and not hasattr(_diffusers, "QwenImageEditPlusPipeline"):
    class QwenImageEditPlusPipeline:  # noqa: N801
        @classmethod
        def from_pretrained(cls, *args, **kwargs):
            raise RuntimeError(
                "Stub: upgrade diffusers for real QwenImageEditPlusPipeline"
            )

    _diffusers.QwenImageEditPlusPipeline = QwenImageEditPlusPipeline

if "diffusers" not in sys.modules:
    _mod = types.ModuleType("diffusers")

    class QwenImageEditPlusPipeline:  # noqa: N801
        @classmethod
        def from_pretrained(cls, *args, **kwargs):
            raise RuntimeError("Stub diffusers module")

    _mod.QwenImageEditPlusPipeline = QwenImageEditPlusPipeline
    sys.modules["diffusers"] = _mod

_ROOT = Path(__file__).resolve().parents[1]
for _d in (
    _ROOT,
    _ROOT / "code",
    _ROOT / "scripts",
    _ROOT / "services" / "img_edit_service",
    _ROOT / "services" / "edit_angle_service",
):
    _p = str(_d)
    if _p not in sys.path:
        sys.path.insert(0, _p)
