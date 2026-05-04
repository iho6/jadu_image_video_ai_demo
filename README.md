# Setup

Install dependencies:

```bash
pip install -r requirements.txt
```

On CUDA with limited VRAM, inference uses **CPU offload** via `accelerate` (slower; needs enough **system RAM** for weights).

From the repo root, run the Qwen image edit CLI (all flags):

```bash
python scripts/run_qwen_img_edit.py \
  --images <path-or-url> [<path-or-url> ...] \
  --prompt "<edit instruction>" \
  --output-dir <output-directory>
```

- `--images` — one or more reference image file paths or `http://` / `https://` URLs (required).
- `--prompt` — text instruction for the edit (required, non-empty).
- `--output-dir` — directory for PNG outputs (optional; default: `output/qwen_edits`).

# Tests

```bash
python -m pytest tests/ -q
```
