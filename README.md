# Setup

## Quickstart (recommended)

Run the repo setup script (creates `.venv`, installs requirements, downloads models, and starts ComfyUI in tmux):

```bash
./setup.sh
```

### Model downloads

- **ComfyUI workflow models**: downloaded by the setup script via `utils/load_comfy_models.py`.
- **Qwen Hugging Face weights** (downloading Qwen VL weights without vLLM which needs 580+ Nvidia driver): see `docs/download_hf_weights.md`.

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

### Character sheet creation CLI (`run_character_sheet_creation.py`)

#### Example: create a character sheet

```bash
python scripts/run_character_sheet_creation.py \
  --image ./ref.png \
  --character-name "Aria"
```

#### Example: also write a character description JSON

```bash
python scripts/run_character_sheet_creation.py \
  --image ./ref.png \
  --character-name "Aria" \
  --character-description
```

#### Optional: custom output directory and Comfy URL

```bash
python scripts/run_character_sheet_creation.py \
  --image ./ref.png \
  --character-name "Aria" \
  --output-dir storage/Aria \
  --comfy-url http://127.0.0.1:8188
```

- `--image` — required; single reference image path or `http://` / `https://` URL.
- `--character-name` — required; used for default output dir and output filenames.
- `--output-dir` — optional; default: `storage/<character-name>`.
- `--comfy-url` — optional; default: `http://127.0.0.1:8188`.
- `--character-description` — optional; when set, writes a JSON file with a VLM-generated description.

Outputs:
- Always prints a single path to stdout:
  - Fullbody input → prints `<output_dir>/<character_name>_character_sheet.png` and exits 0.
  - Non-fullbody input → generates a corrected fullbody PNG, prints its path, prints error message to stderr, exits 1.
- When `--character-description` is provided, also writes:
  - `<output_dir>/<character_name>_character_description.json`
  - JSON includes: `character_name`, `image_described`, `description`, and `character_sheet_path` (when a sheet exists).

### Ref guided generation CLI (`run_ref_guided_gen.py`)

Reference-guided Qwen image edit using `@CharacterName` tokens in the prompt.

How it works:
- Parses unique `@CharacterName` references in `--prompt` (left-to-right).
- Each `@CharacterName` maps to `storage/<CharacterName>/<safe(CharacterName)>_character_sheet.png`.
- Image slot ordering is deterministic:
  - Image 1..N: character sheets in parse order
  - Image N+1: `--backdrop-img` (optional) as scene/backdrop reference

Constraints:
- Supports up to **2 unique** `@CharacterName` references plus an optional backdrop (max **3** images total, matching `img_edit`).

Prerequisite:
- Create each character sheet first via `scripts/run_character_sheet_creation.py`.

Example:

```bash
python scripts/run_ref_guided_gen.py \
  --prompt "@Eli sitting on the couch, staring at @Beth's phone" \
  --backdrop-img <path-or-url> \
  --output-dir output/ref-guided-gen
```

Outputs:
- Prints one or more lines like `saved <path>` for generated PNGs.

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
