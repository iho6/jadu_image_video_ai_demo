#!/usr/bin/env python3
"""Download ComfyUI model weights for this repo's two local-Comfy services.

Targets workflows:
  - services/img_edit_service/image_qwen_image_edit_2509.json (img-edit)
  - services/edit_angle_service/qwen_image_edit_angle_single.json (edit-angle)

Run from the directory ComfyUI uses as its model root (often the vendored ``comfyui/``
folder or repo root if ``models/`` is shared). Paths are relative (e.g. ``models/loras/...``).

Usage:
    python utils/download_models.py --img-edit [--hf-token YOUR_TOKEN]
    python utils/download_models.py --edit-angle [--hf-token YOUR_TOKEN]
    python utils/download_models.py --img-edit --edit-angle
    python utils/download_models.py --image-edit   # alias for --img-edit
    python utils/download_models.py --img-edit --force-redownload
"""

from __future__ import annotations

import os
import ssl
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

from tqdm import tqdm


class _TqdmPipeLineStdout:
    """Turn tqdm's CR-based refreshes into newline-terminated lines for piped parents."""

    def __init__(self, raw):
        self._raw = raw
        self.encoding = getattr(raw, "encoding", None)

    def write(self, s: str) -> int:
        if not s:
            return 0
        if "\r" in s:
            core = s.split("\r")[-1].rstrip()
            if core:
                self._raw.write(core + "\n")
            return len(s)
        self._raw.write(s)
        return len(s)

    def flush(self) -> None:
        self._raw.flush()


# Qwen Image Edit 2509 stack — matches image_qwen_image_edit_2509.json
IMG_EDIT_MODELS = [
    {
        "name": "qwen_2.5_vl_7b_fp8_scaled.safetensors (Text Encoder)",
        "url": "https://huggingface.co/Comfy-Org/HunyuanVideo_1.5_repackaged/resolve/main/split_files/text_encoders/qwen_2.5_vl_7b_fp8_scaled.safetensors",
        "path": "models/text_encoders/qwen_2.5_vl_7b_fp8_scaled.safetensors",
    },
    {
        "name": "Qwen-Image-Edit-2509-Lightning-4steps-V1.0-bf16.safetensors (LoRA)",
        "url": "https://huggingface.co/lightx2v/Qwen-Image-Lightning/resolve/main/Qwen-Image-Edit-2509/Qwen-Image-Edit-2509-Lightning-4steps-V1.0-bf16.safetensors",
        "path": "models/loras/Qwen-Image-Edit-2509-Lightning-4steps-V1.0-bf16.safetensors",
    },
    {
        "name": "qwen_image_edit_2509_fp8_e4m3fn.safetensors (Diffusion Model)",
        "url": "https://huggingface.co/Comfy-Org/Qwen-Image-Edit_ComfyUI/resolve/main/split_files/diffusion_models/qwen_image_edit_2509_fp8_e4m3fn.safetensors",
        "path": "models/diffusion_models/qwen_image_edit_2509_fp8_e4m3fn.safetensors",
    },
    {
        "name": "qwen_image_vae.safetensors (VAE)",
        "url": "https://huggingface.co/Comfy-Org/Qwen-Image_ComfyUI/resolve/main/split_files/vae/qwen_image_vae.safetensors",
        "path": "models/vae/qwen_image_vae.safetensors",
    },
]

_MULTIPLE_ANGLES_LORA = {
    "name": "Qwen-Edit-2509-Multiple-angles.safetensors (Multi-angle LoRA)",
    "url": "https://huggingface.co/Comfy-Org/Qwen-Image-Edit_ComfyUI/resolve/main/split_files/loras/Qwen-Edit-2509-Multiple-angles.safetensors",
    "path": "models/loras/Qwen-Edit-2509-Multiple-angles.safetensors",
}


def _dedupe_models(models: list[dict]) -> list[dict]:
    """Deduplicate models by destination path (first definition wins)."""
    deduped: list[dict] = []
    seen_paths: set[str] = set()
    for model in models:
        path = str(model.get("path", "")).strip()
        if not path or path in seen_paths:
            continue
        deduped.append(model)
        seen_paths.add(path)
    return deduped


EDIT_ANGLE_MODELS = _dedupe_models(IMG_EDIT_MODELS + [_MULTIPLE_ANGLES_LORA])

SERVICE_MODEL_MAP = {
    "img_edit": IMG_EDIT_MODELS,
    "edit_angle": EDIT_ANGLE_MODELS,
}


def _is_windows_sharing_violation(exc: BaseException) -> bool:
    if os.name != "nt":
        return False
    return isinstance(exc, OSError) and getattr(exc, "winerror", None) == 32


def _replace_with_retry(part: Path, dest: Path) -> None:
    """Commit ``.part`` to final path; retry on transient Windows file locks (WinError 32)."""
    max_attempts = 25
    delay_s = 0.25
    for attempt in range(max_attempts):
        try:
            os.replace(part, dest)
            return
        except OSError as e:
            if not _is_windows_sharing_violation(e):
                raise
            if attempt >= max_attempts - 1:
                print(
                    "    HINT: Another program may be locking files under models\\ "
                    "(e.g. Windows Defender, Explorer preview, or cloud sync). "
                    "Try again or add an exclusion; re-run this script to resume."
                )
                raise
            time.sleep(delay_s)
            delay_s = min(2.0, delay_s + 0.25)


def download_file(
    url: str,
    destination: str,
    description: str = None,
    hf_token: str = None,
    skip_ssl_verify: bool = False,
    force_redownload: bool = False,
) -> bool:
    """Download a file from URL to destination with optional HF authentication."""
    destination_path = Path(destination)
    destination_path.parent.mkdir(parents=True, exist_ok=True)

    part_path = destination_path.with_suffix(destination_path.suffix + ".part")
    if force_redownload:
        if part_path.exists():
            try:
                part_path.unlink()
            except OSError as e:
                print(f"  ERROR: Could not remove partial download {part_path}: {e}")
                return False
        if destination_path.exists():
            try:
                destination_path.unlink()
                print(f"  --force-redownload: removed existing {destination_path.name}")
            except OSError as e:
                print(f"  ERROR: Could not remove existing file {destination_path}: {e}")
                return False

    if destination_path.exists():
        file_size = destination_path.stat().st_size
        print(
            f"  OK  {description or destination_path.name} already exists "
            f"({file_size / (1024*1024):.1f} MB)"
        )
        return True

    print(f"  Downloading {description or destination_path.name}...")
    print(f"    From: {url}")
    print(f"    To: {destination}")

    try:
        ssl_context = None
        if skip_ssl_verify:
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            print("    WARN: SSL verification disabled for this download")

        req = urllib.request.Request(url)
        if hf_token and "huggingface.co" in url:
            req.add_header("Authorization", f"Bearer {hf_token}")

        if part_path.exists():
            try:
                part_path.unlink()
            except Exception:
                pass

        with urllib.request.urlopen(req, context=ssl_context) as resp:
            total = resp.headers.get("Content-Length")
            total_bytes = int(total) if total and str(total).isdigit() else None
            chunk_size = 1024 * 1024
            desc = (description or destination_path.name).strip()

            with tqdm(
                total=total_bytes,
                unit="B",
                unit_scale=True,
                unit_divisor=1024,
                desc=desc,
                dynamic_ncols=False,
                disable=False,
                file=_TqdmPipeLineStdout(sys.stdout),
            ) as bar:
                with open(part_path, "wb") as f:
                    while True:
                        chunk = resp.read(chunk_size)
                        if not chunk:
                            break
                        f.write(chunk)
                        bar.update(len(chunk))
                    f.flush()
                    os.fsync(f.fileno())

        part_size = part_path.stat().st_size if part_path.exists() else 0
        if part_size <= 0:
            print("  ERROR: Download failed - empty file")
            try:
                part_path.unlink()
            except Exception:
                pass
            return False

        _replace_with_retry(part_path, destination_path)
        file_size = destination_path.stat().st_size
        print(f"  OK  Successfully downloaded ({file_size / (1024*1024):.1f} MB)")
        return True

    except urllib.error.HTTPError as e:
        if e.code in (401, 403):
            print(f"  ERROR: Authorization failed: {e}")
            print("    Get your token from: https://huggingface.co/settings/tokens")
            print(
                "    Then run: python utils/download_models.py --img-edit --hf-token YOUR_TOKEN"
            )
        else:
            print(f"  ERROR: Download failed: {e}")
        return False
    except Exception as e:
        print(f"  ERROR: Download failed: {e}")
        try:
            part_path  # type: ignore[name-defined]
        except Exception:
            part_path = None
        if part_path:
            try:
                Path(part_path).unlink()
            except Exception:
                pass
        return False


def download_model_group(
    title: str,
    models: list[dict],
    hf_token: str | None = None,
    *,
    force_redownload: bool = False,
) -> bool:
    """Download all models in a group."""
    print("=" * 60)
    print(title)
    print("=" * 60)
    Path("models/configs").mkdir(parents=True, exist_ok=True)
    print("[OK] Created/verified models/configs directory")

    success = 0
    for model in models:
        if download_file(
            model["url"],
            model["path"],
            model["name"],
            hf_token,
            force_redownload=force_redownload,
        ):
            success += 1

    print("\n" + "=" * 60)
    print(f"Download complete: {success}/{len(models)} models")
    print("=" * 60)
    return success == len(models)


def _collect_selected_models(args) -> list[dict]:
    selected_models: list[dict] = []
    if args.img_edit:
        selected_models.extend(SERVICE_MODEL_MAP["img_edit"])
    if args.edit_angle:
        selected_models.extend(SERVICE_MODEL_MAP["edit_angle"])
    return _dedupe_models(selected_models)


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description=(
            "Download model weights for services/img_edit_service (img-edit) and "
            "services/edit_angle_service (edit-angle) Comfy workflows."
        ),
        epilog=(
            "Examples:\n"
            "  python utils/download_models.py --img-edit\n"
            "  python utils/download_models.py --edit-angle\n"
            "  python utils/download_models.py --img-edit --edit-angle\n"
            "  python utils/download_models.py --image-edit   # same as --img-edit\n"
            "  python utils/download_models.py --img-edit --hf-token hf_xxx"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--img-edit",
        "--image-edit",
        action="store_true",
        dest="img_edit",
        help=(
            "Download models for img_edit_service "
            "(image_qwen_image_edit_2509.json; 4 weights)"
        ),
    )
    parser.add_argument(
        "--edit-angle",
        action="store_true",
        dest="edit_angle",
        help=(
            "Download models for edit_angle_service "
            "(qwen_image_edit_angle_single.json; img-edit stack + multi-angle LoRA)"
        ),
    )
    parser.add_argument(
        "--force-redownload",
        action="store_true",
        help="Delete existing destination files and re-download HF weights (testing/repair)",
    )
    parser.add_argument(
        "--hf-token",
        type=str,
        help="Hugging Face API token (or set HF_TOKEN env var)",
    )
    args = parser.parse_args()

    if not args.img_edit and not args.edit_angle:
        parser.print_help()
        print("\nError: specify --img-edit and/or --edit-angle.")
        sys.exit(1)

    hf_token = args.hf_token or os.environ.get("HF_TOKEN")
    if not hf_token:
        print("\nWarning: No Hugging Face token provided. Some downloads may fail.")
        print("Get your token from: https://huggingface.co/settings/tokens\n")

    selected = _collect_selected_models(args)
    ok = download_model_group(
        "Comfy model download (deduplicated by destination path)",
        selected,
        hf_token,
        force_redownload=args.force_redownload,
    )
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
