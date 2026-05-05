"""
CLI: one reference image and prompt, run single-branch angle-edit workflow on local ComfyUI (default :8188).

Requires ComfyUI with models/LoRAs referenced by qwen_image_edit_angle_single.json.
"""

from __future__ import annotations

import argparse
import copy
import json
import secrets
import sys
import uuid
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from utils.comfyui_utils import (
    ComfyPromptError,
    queue_prompt,
    upload_image,
    view_image_bytes,
    wait_for_history_entry,
)
from utils.image_utils import load_image, pil_to_png_bytes

DEFAULT_COMFY_URL = "http://127.0.0.1:8188"
DEFAULT_OUTPUT_DIR = Path("output") / "edit-angle"
WORKFLOW_JSON = Path(__file__).parent / "qwen_image_edit_angle_single.json"
NODE_LOAD = "25"
NODE_PROMPT = "66"
NODE_SAVE = "31"


def run_edit_angle(
    image: str,
    prompt: str,
    output_dir: Path,
    comfy_url: str = DEFAULT_COMFY_URL,
    *,
    workflow_path: Path = WORKFLOW_JSON,
    poll_interval_sec: float = 0.5,
    timeout_sec: float = 600.0,
) -> list[Path]:
    if not str(image).strip():
        raise ValueError("image must be non-empty")
    if not prompt.strip():
        raise ValueError("prompt must be non-empty")
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    base = comfy_url.rstrip("/")
    png = pil_to_png_bytes(load_image(image))
    name = upload_image(
        base,
        png,
        f"angle_edit_{uuid.uuid4().hex}.png",
        timeout=120,
    )
    workflow: dict = copy.deepcopy(
        json.loads(workflow_path.read_text(encoding="utf-8"))
    )
    workflow[NODE_LOAD]["inputs"]["image"] = name
    workflow[NODE_PROMPT]["inputs"]["value"] = prompt
    workflow["65:33:21"]["inputs"]["seed"] = secrets.randbelow(2**31)
    client_id = uuid.uuid4().hex
    resp = queue_prompt(base, workflow, client_id, timeout=120)
    entry = wait_for_history_entry(
        base,
        resp["prompt_id"],
        timeout_sec=timeout_sec,
        poll_interval_sec=poll_interval_sec,
    )
    images_meta = (
        (entry.get("outputs") or {}).get(NODE_SAVE, {}).get("images") or []
    )
    if not images_meta:
        raise RuntimeError(
            f"No images in history outputs for SaveImage node {NODE_SAVE}: {entry!r}"
        )
    written: list[Path] = []
    for item in images_meta:
        filename = item["filename"]
        subfolder = item.get("subfolder") or ""
        folder_type = item.get("type") or "output"
        data = view_image_bytes(
            base, filename, subfolder, folder_type, timeout=120
        )
        dest = out / filename
        if dest.exists():
            dest = out / f"{dest.stem}_{uuid.uuid4().hex[:8]}{dest.suffix}"
        dest.write_bytes(data)
        written.append(dest)
    return written


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Run angle-edit workflow via local ComfyUI (default port 8188)."
    )
    p.add_argument(
        "--image",
        required=True,
        metavar="PATH_OR_URL",
        help="Reference image (local path or http(s) URL).",
    )
    p.add_argument("--prompt", required=True, help="Edit / angle instruction (non-empty).")
    p.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help=f"Directory for downloaded PNGs (default: {DEFAULT_OUTPUT_DIR}).",
    )
    p.add_argument(
        "--comfy-url",
        default=DEFAULT_COMFY_URL,
        help=f"ComfyUI base URL (default: {DEFAULT_COMFY_URL}).",
    )
    return p.parse_args(argv)


def handler(args: argparse.Namespace) -> int:
    if not str(args.image).strip():
        print("error: --image must be non-empty", file=sys.stderr)
        return 1
    if not str(args.prompt).strip():
        print("error: --prompt must be non-empty", file=sys.stderr)
        return 1
    try:
        paths = run_edit_angle(
            str(args.image),
            args.prompt,
            Path(args.output_dir),
            comfy_url=str(args.comfy_url),
        )
    except (ComfyPromptError, OSError, TimeoutError, ValueError, RuntimeError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    for pth in paths:
        print("saved", pth.resolve())
    return 0


def main() -> None:
    sys.exit(handler(parse_args()))


if __name__ == "__main__":
    main()
