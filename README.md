# Setup

Install dependencies:

```bash
pip install -r requirements.txt
```

## Service

Server call to ComfyUI via JSON workflows.

Requires a local ComfyUI server (default `http://127.0.0.1:8188`).

**Img-edit** (1–3 reference images):

```bash
python services/img_edit_service/img_edit.py \
  --images ./ref.png \
  --prompt "Add soft rim lighting; keep identity." \
  --output-dir output/img-edit
```

- `--images` — one to three reference image paths or `http://` / `https://` URLs (required).
- `--prompt` — edit instruction (required, non-empty).
- `--output-dir` — directory for PNG outputs (optional; default: `output/img-edit`).
- `--comfy-url` — ComfyUI base URL (optional; default: `http://127.0.0.1:8188`).

**Edit-angle** (single reference image):

```bash
python services/edit_angle_service/edit_angle.py \
  --image ./ref.png \
  --prompt "Low-angle wide shot, same subject and outfit." \
  --output-dir output/edit-angle
```

- `--image` — reference image path or `http://` / `https://` URL (required).
- `--prompt` — angle or framing instruction (required, non-empty).
- `--output-dir` — directory for PNG outputs (optional; default: `output/edit-angle`).
- `--comfy-url` — ComfyUI base URL (optional; default: `http://127.0.0.1:8188`).

## Scripts

### Qwen VL CLI (`run_qwen_vl.py`)

From the repo root, run the Qwen VL CLI (all flags):

```bash
python scripts/run_qwen_vl.py \
  --images <path-or-url> [<path-or-url> ...] \
  --video <video-path-or-url> \
  --prompt "<question or instruction>"
```

- `--images` — optional; one to three reference image file paths or `http://` / `https://` URLs when provided.
- `--video` — optional; one video local path or `http://` / `https://` URL (must end with `.mp4`, `.mov`, `.mkv`, `.avi`, `.webm`, or `.m4v`).
- At least one of `--images` or `--video` must be provided.
- `--prompt` — text prompt for evaluation (required, non-empty).

### Edit prompt enhancement CLI (`run_enhance_edit_prompt.py`)

From the repo root, run the edit-prompt enhancement CLI (all flags):

```bash
python scripts/run_enhance_edit_prompt.py \
  --images <path-or-url> [<path-or-url> ...] \
  --prompt "<edit instruction>"
```

- `--images` — required; one to three reference image file paths or `http://` / `https://` URLs.
- `--prompt` — required; raw edit instruction to enhance (non-empty).
- Prints a single enhanced prompt to stdout. The underlying model is asked to respond with JSON containing a `Rewritten` field.

### Qwen image edit CLI (`run_qwen_img_edit.py`)

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
