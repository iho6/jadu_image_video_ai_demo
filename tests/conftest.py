from __future__ import annotations

import sys
from pathlib import Path


def pytest_configure() -> None:
    """
    Ensure repo-root imports win over vendored ComfyUI modules.

    Several modules are intended to be imported as top-level namespace packages
    (e.g. `utils.*`, `services.*`, and modules under `code/`).
    """
    root = Path(__file__).resolve().parents[1]
    code_dir = root / "code"
    scripts_dir = root / "scripts"
    service_dirs = (
        root / "services" / "img_edit_service",
        root / "services" / "edit_angle_service",
    )
    for p in (str(root), str(code_dir), str(scripts_dir), *(str(d) for d in service_dirs)):
        if p in sys.path:
            sys.path.remove(p)
        sys.path.insert(0, p)
