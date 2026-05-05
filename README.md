# Setup

Install dependencies:

```bash
pip install -r requirements.txt
```

**ComfyUI** — A snapshot of [comfy-org/ComfyUI](https://github.com/comfy-org/ComfyUI) is vendored under [`comfyui/`](comfyui/) as plain files (not a git submodule; no nested `.git`).

From the repo root, run the Qwen image edit CLI (all flags):

```bash
python scripts/run_qwen_img_edit.py \
  --images <path-or-url> [<path-or-url> ...] \
  --prompt "<edit instruction>" \
  --output-dir <output-directory>
```

- `--images` — one or more reference image file paths or `http://` / `https://` URLs (required).
- `--prompt` — text instruction for the edit (required, non-empty).
- `--output-dir` — directory for PNG outputs (optional; default: `qwen_edit_out`).

# Tests

```bash
python -m pytest tests/ -q
```
