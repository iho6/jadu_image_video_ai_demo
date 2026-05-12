# Setup

## Index

- [Services](#services)
- [Scripts](#scripts)
- [Tests](#tests)
- [Demo](#demo)
  - [Ref-guided generation](#ref-guided-generation-eli-on-couch-with-backdrop)
  - [Character sheet creation](#character-sheet-creation-eli)
  - [VLM Analysis (Video & Image)](#vlm-analysis-video--image)
  - [Angle edit](#angle-edit)
  - [Image edit service](#image-edit-service-img_edit)
- [Eval](#eval)
  - [Unprompted Artifact Check](#unprompted-artifact-check---non-prompt-artifact--question)

## Quickstart (recommended)

Run the repo setup script (creates `.venv`, installs requirements, downloads models, and starts ComfyUI in tmux):

```bash
./setup.sh
# Activate the venv created by setup.sh
source .venv/bin/activate
```

### Model downloads

- **ComfyUI workflow models**: downloaded by the setup script via `utils/load_comfy_models.py`.
- **Qwen Hugging Face weights** (downloading Qwen VL weights without vLLM which needs 580+ Nvidia driver): see `docs/download_hf_weights.md`.

Setup automatically downloads models; the links above are only needed if something errors.

## Services

Server call to ComfyUI via JSON workflows.

Requires a local ComfyUI server (default `http://127.0.0.1:8188`), started by setup script.

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
- `--video` — optional; one video local path or `http://` / `https://` URL. If the URL/path does not end in a supported video suffix (`.mp4`, `.mov`, `.mkv`, `.avi`, `.webm`, `.m4v`), the CLI will download/transcode it to MP4 first, which requires `ffmpeg` on `PATH`.
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

- `--image` — required; single reference image path or `http://` / `https://` URL.
- `--character-name` — required; used for default output dir and output filenames.
- `--output-dir` — optional; default: `storage/<character-name>`.
- `--comfy-url` — optional; default: `http://127.0.0.1:8188`.
- `--character-description` — optional; when set, writes a JSON file with a VLM-generated description.

Outputs:
- Always prints a single path to stdout:
  - Fullbody input → prints `<output_dir>/<character_name>_character_sheet.png` and exits 0.
  - Non-fullbody input → generates a corrected fullbody PNG, prints its path, prints error message to stderr, exits 1.
- When `--character-description` flag entered, also writes:
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
- Supports up to **2 unique** `@CharacterName` references plus an optional backdrop (max **3** images total, matching `img_edit` due to ComfyUI constraint and can be improved via API or direct Qwen Img repo cloning).

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

### Qwen Chat REPL (`run_qwen_chat.py`)

Interactive multi-turn chat session with Qwen3-VL. Maintains full conversation history across turns and supports inline image or URL attachment.

```bash
python scripts/run_qwen_chat.py
python scripts/run_qwen_chat.py --model-id models/hf/Qwen__Qwen3-VL-4B-Instruct
python scripts/run_qwen_chat.py --system-prompt "You are a character art assistant."
python scripts/run_qwen_chat.py --transcript-dir output/chat_transcripts
```

- `--model-id` — optional; local model path or HF repo ID (default: `models/hf/Qwen__Qwen3-VL-4B-Instruct`).
- `--system-prompt` — optional; custom system prompt string (default: character art assistant prompt).
- `--transcript-dir` — optional; directory for JSON session transcripts (default: `output/chat_transcripts/`).

**Image syntax** — prefix your message with bracket-enclosed paths or URLs:

```
[photo.png] describe this character
[a.png, b.png] compare these two
[https://example.com/img.png] what is this?
```

**Slash commands:**

| Command   | Effect                                      |
|-----------|---------------------------------------------|
| `/quit`   | Save transcript and exit                    |
| `/reset`  | Clear conversation history (keeps prompt)   |
| `/export` | Save transcript now, continue chatting      |
| `/help`   | Show command reference                      |

Images from prior turns are automatically stripped from the context payload before each inference call to avoid re-embedding them in VRAM. A placeholder text is inserted so the model retains awareness of earlier images.

Outputs:
- Prints assistant replies to stdout after each turn.
- On exit (`/quit`, EOF, or Ctrl-C), writes `output/chat_transcripts/session_YYYYMMDD_HHMMSS.json` containing `model_id`, `turns`, `exported_at`, and the full `messages` list.

### Generation eval CLI (`run_gen_eval.py`)

VLM evaluation of a generated image or video against reference inputs. Runs all evaluations by default; individual evals can be selected via flags.

Output type (image vs video) is detected automatically from the `--gen-output` extension.

#### Example: run all evals on a generated image

```bash
python scripts/run_gen_eval.py \
  --refs ref1.png ref2.png \
  --gen-output output.png \
  --prompt "Put the person in image 1 on the sofa in image 2"
```

#### Example: run only prompt adherence on a generated video

```bash
python scripts/run_gen_eval.py \
  --refs ref.png \
  --gen-output output.mp4 \
  --prompt "Animate this character walking" \
  --prompt-adherence
```

- `--refs` — required; one or more reference image paths or URLs used during generation.
- `--gen-output` — required; path or URL of the generated output (image or video) to evaluate.
- `--prompt` — required; the user prompt that was used to produce the generated output (non-empty).
- `--model-id` — optional; override model path or HF repo ID (default: QwenVL default).
- `--ref-coherence` — run reference consistency evaluation.
- `--prompt-adherence` — run prompt adherence evaluation.
- `--non-prompt-artifact` — run unprompted artifact check; lists elements present in the output but not specified in the prompt, and evaluates each as desired or undesired.
- `--question` — list unprompted elements and reformat each as a "Did you want...?" question (not included in `--all`; must be passed explicitly).
- `--debug` — print raw VLM responses to stderr for each eval call.
- `--all` — run all evaluations (default when no eval flag is specified; does not include `--question`).

Outputs:
- Prints per-eval decisions, scores, and reasoning to stdout as they complete.
- Prints final JSON result to stdout:
  ```json
  {
    "ref_consistency": {
      "required": true,
      "reasoning": "...",
      "score": 4
    },
    "prompt_adherence": {
      "score": 3,
      "reasoning": "..."
    },
    "non_prompt_artifact": {
      "items": [
        {"artifact": "...", "desired": true, "reasoning": "..."}
      ]
    },
    "questions": ["Did you want ...?"]
  }
  ```
- `ref_consistency.score` is only present when `required` is `true`.

# Tests

```bash
python -m pytest tests/ -q
```

## Demo

**Demo variables** (from `tests/test_commands.md` lines 11–16)

Ran using RunPod SSH GPU Env on 4090 GPU.

```powershell
$CAT_IMG="https://renderboard-test.s3.us-east-005.backblazeb2.com/images/base64-ea3a392a-23de-43c4-a915-83ebcc2a2725"
$VET_IMG="https://renderboard-test.s3.us-east-005.backblazeb2.com/images/base64-0c187082-bcd0-48b4-9fd6-9b8ca699b33a"
$GIRL_IMG="https://renderboard-test.s3.us-east-005.backblazeb2.com/images/base64-f38842e4-a365-479d-aa6c-c67e76ccc234"
$ROOM_IMG="https://renderboard-test.s3.us-east-005.backblazeb2.com/images/base64-6f9167f5-0d6e-4b2a-b02f-cebb165435a2"
$SCENE_VIDEO="https://renderboard-test.s3.us-east-005.backblazeb2.com/videos/asset-ee0e77cc-d735-4d35-bcbe-ef89eaa23789"
```

### Ref-guided generation: Eli on couch (with backdrop)

Still imperfect due to lack of time to refine prompt. And ref gen works better with controlNet, not yet implemented.

**Command**

```bash
python scripts/run_ref_guided_gen.py \
  --prompt "@Eli sitting on the couch" \
  --backdrop-img "$ROOM_IMG" \
  --output-dir output/ref-guided-gen
```

**Prompt**

`@Eli sitting on the couch`

**Input (scene/backdrop)**

<img src="input/room.png" width="220" />

**Output**

<img src="output/ref-guided-gen/ComfyUI_00006_.png" width="900" />

<details>
<summary>Key logs (click to expand)</summary>

```text
(.venv) root@5255d91fbdee:~/jadu_image_video_ai_demo# python scripts/run_ref_guided_gen.py --prompt "@Eli sitting on the couch" --backdrop-img $ROOM_IMG --output-dir output/ref-guided-gen

combined_prompt:
Character in image 1 sitting on the couch

Use image 2 as the scene/backdrop reference. Keep the appearance, clothing, and all details of each character the same as in the 1 image reference(s).
[comfy][info] prompt.queue.start job=0ddf86864d794b68807fc6d39945e3e8 data={"client_id": "0ddf86864d794b68807fc6d39945e3e8", "timeout": 1200}
[comfy][info] job.sent job=0ddf86864d794b68807fc6d39945e3e8 prompt=da69e199-4615-46f1-8002-3c21e5815a11 data={"prompt_id": "da69e199-4615-46f1-8002-3c21e5815a11", "queue_number": 10}
[comfy][info] prompt.queue.ok job=0ddf86864d794b68807fc6d39945e3e8 prompt=da69e199-4615-46f1-8002-3c21e5815a11 elapsed_ms=4 data={"prompt_id": "da69e199-4615-46f1-8002-3c21e5815a11"}
[comfy][info] history.poll.start job=0ddf86864d794b68807fc6d39945e3e8 prompt=da69e199-4615-46f1-8002-3c21e5815a11 data={"poll_interval_sec": 0.5, "prompt_id": "da69e199-4615-46f1-8002-3c21e5815a11", "timeout_sec": 600.0}
[comfy][info] job.running job=0ddf86864d794b68807fc6d39945e3e8 prompt=da69e199-4615-46f1-8002-3c21e5815a11 elapsed_ms=4367 data={"source": "jobs_api"}
[comfy][info] job.returned job=0ddf86864d794b68807fc6d39945e3e8 prompt=da69e199-4615-46f1-8002-3c21e5815a11 elapsed_ms=140117 data={"outputs_count": 1, "result": "success", "source": "jobs_api"}
[comfy][info] history.poll.ok job=0ddf86864d794b68807fc6d39945e3e8 prompt=da69e199-4615-46f1-8002-3c21e5815a11 elapsed_ms=136435 data={"polls": 248, "prompt_id": "da69e199-4615-46f1-8002-3c21e5815a11"}
saved /root/jadu_image_video_ai_demo/output/ref-guided-gen/ComfyUI_00001_.png
```

</details>

### Character sheet creation: Eli

Still haven't added segmentation tool for re-overlaying a background for optimal dimension/color.

**Command**

```bash
python scripts/run_character_sheet_creation.py --image $VET_IMG --character-name "Eli" --full-body-check
```

**Output**

<img src="storage/Eli/Eli_character_sheet.png" width="900" />

<details>
<summary>Sample log (click to expand)</summary>

```text
(.venv) root@5255d91fbdee:~/jadu_image_video_ai_demo# python scripts/run_character_sheet_creation.py --image $VET_IMG --character-name "Eli" --full-body-check

=== args ===
image='https://renderboard-test.s3.us-east-005.backblazeb2.com/images/base64-0c187082-bcd0-48b4-9fd6-9b8ca699b33a'
character_name='Eli'
output_dir='storage/Eli'
comfy_url='http://127.0.0.1:8188'
full_body_check=True
character_description=False
=== ok: args elapsed_ms=0 ===

=== check: comfy reachable ===
=== ok: check: comfy reachable elapsed_ms=8 ===

=== init: character sheet creator ===
/root/jadu_image_video_ai_demo/.venv/lib/python3.11/site-packages/transformers/models/auto/modeling_auto.py:2284: FutureWarning: The class `AutoModelForVision2Seq` is deprecated and will be removed in v5.0. Please use `AutoModelForImageTextToText` instead.
  warnings.warn(
`torch_dtype` is deprecated! Use `dtype` instead!
Loading checkpoint shards: 100%|████████████████████████████| 2/2 [00:00<00:00,  2.50it/s]
=== ok: init: character sheet creator elapsed_ms=24255 ===

=== step: character sheet creation ===

=== step: full-body-check (QwenVL) ===
The following generation flags are not valid and may be ignored: ['temperature', 'top_p', 'top_k']. Set `TRANSFORMERS_VERBOSITY=info` for more details.
=== ok: step: full-body-check (QwenVL) elapsed_ms=4043 ===
[comfy][info] prompt.queue.start job=31b109bfd579425da4c40e3a19c0cf4e data={"client_id": "31b109bfd579425da4c40e3a19c0cf4e", "timeout": 120}
[comfy][info] job.sent job=31b109bfd579425da4c40e3a19c0cf4e prompt=ae675c6f-482c-42ee-b650-53eac5b838cb data={"prompt_id": "ae675c6f-482c-42ee-b650-53eac5b838cb", "queue_number": 2}
[comfy][info] prompt.queue.ok job=31b109bfd579425da4c40e3a19c0cf4e prompt=ae675c6f-482c-42ee-b650-53eac5b838cb elapsed_ms=2 data={"prompt_id": "ae675c6f-482c-42ee-b650-53eac5b838cb"}
[comfy][info] history.poll.start job=31b109bfd579425da4c40e3a19c0cf4e prompt=ae675c6f-482c-42ee-b650-53eac5b838cb data={"poll_interval_sec": 0.5, "prompt_id": "ae675c6f-482c-42ee-b650-53eac5b838cb", "timeout_sec": 600.0}
[comfy][info] job.running job=31b109bfd579425da4c40e3a19c0cf4e prompt=ae675c6f-482c-42ee-b650-53eac5b838cb elapsed_ms=7782 data={"source": "jobs_api"}
[comfy][info] job.returned job=31b109bfd579425da4c40e3a19c0cf4e prompt=ae675c6f-482c-42ee-b650-53eac5b838cb elapsed_ms=128884 data={"result": "success", "source": "history"}
[comfy][info] history.poll.ok job=31b109bfd579425da4c40e3a19c0cf4e prompt=ae675c6f-482c-42ee-b650-53eac5b838cb elapsed_ms=128872 data={"polls": 239, "prompt_id": "ae675c6f-482c-42ee-b650-53eac5b838cb"}
[comfy][info] prompt.queue.start job=c48b5158fc55410b93c807c7baa52d03 data={"client_id": "c48b5158fc55410b93c807c7baa52d03", "timeout": 120}
[comfy][info] job.sent job=c48b5158fc55410b93c807c7baa52d03 prompt=82bc1ebd-85f0-42d2-b8ed-fc5bd57f6599 data={"prompt_id": "82bc1ebd-85f0-42d2-b8ed-fc5bd57f6599", "queue_number": 3}
[comfy][info] prompt.queue.ok job=c48b5158fc55410b93c807c7baa52d03 prompt=82bc1ebd-85f0-42d2-b8ed-fc5bd57f6599 elapsed_ms=2 data={"prompt_id": "82bc1ebd-85f0-42d2-b8ed-fc5bd57f6599"}
[comfy][info] history.poll.start job=c48b5158fc55410b93c807c7baa52d03 prompt=82bc1ebd-85f0-42d2-b8ed-fc5bd57f6599 data={"poll_interval_sec": 0.5, "prompt_id": "82bc1ebd-85f0-42d2-b8ed-fc5bd57f6599", "timeout_sec": 600.0}
[comfy][info] job.running job=c48b5158fc55410b93c807c7baa52d03 prompt=82bc1ebd-85f0-42d2-b8ed-fc5bd57f6599 elapsed_ms=584 data={"source": "jobs_api"}
[comfy][info] job.returned job=c48b5158fc55410b93c807c7baa52d03 prompt=82bc1ebd-85f0-42d2-b8ed-fc5bd57f6599 elapsed_ms=126892 data={"result": "success", "source": "history"}
[comfy][info] history.poll.ok job=c48b5158fc55410b93c807c7baa52d03 prompt=82bc1ebd-85f0-42d2-b8ed-fc5bd57f6599 elapsed_ms=126883 data={"polls": 235, "prompt_id": "82bc1ebd-85f0-42d2-b8ed-fc5bd57f6599"}
[comfy][info] prompt.queue.start job=ba296fa120e9470786f8583d87451acb data={"client_id": "ba296fa120e9470786f8583d87451acb", "timeout": 120}
[comfy][info] job.sent job=ba296fa120e9470786f8583d87451acb prompt=52f1bfc0-c8ae-4ad9-9589-9f740b63658c data={"prompt_id": "52f1bfc0-c8ae-4ad9-9589-9f740b63658c", "queue_number": 4}
[comfy][info] prompt.queue.ok job=ba296fa120e9470786f8583d87451acb prompt=52f1bfc0-c8ae-4ad9-9589-9f740b63658c elapsed_ms=2 data={"prompt_id": "52f1bfc0-c8ae-4ad9-9589-9f740b63658c"}
[comfy][info] history.poll.start job=ba296fa120e9470786f8583d87451acb prompt=52f1bfc0-c8ae-4ad9-9589-9f740b63658c data={"poll_interval_sec": 0.5, "prompt_id": "52f1bfc0-c8ae-4ad9-9589-9f740b63658c", "timeout_sec": 600.0}
[comfy][info] job.running job=ba296fa120e9470786f8583d87451acb prompt=52f1bfc0-c8ae-4ad9-9589-9f740b63658c elapsed_ms=592 data={"source": "jobs_api"}
[comfy][info] job.returned job=ba296fa120e9470786f8583d87451acb prompt=52f1bfc0-c8ae-4ad9-9589-9f740b63658c elapsed_ms=123267 data={"result": "success", "source": "history"}
[comfy][info] history.poll.ok job=ba296fa120e9470786f8583d87451acb prompt=52f1bfc0-c8ae-4ad9-9589-9f740b63658c elapsed_ms=123258 data={"polls": 227, "prompt_id": "52f1bfc0-c8ae-4ad9-9589-9f740b63658c"}
[comfy][info] prompt.queue.start job=d21f71a1afba494d85a97e092d77aeb3 data={"client_id": "d21f71a1afba494d85a97e092d77aeb3", "timeout": 120}
[comfy][info] job.sent job=d21f71a1afba494d85a97e092d77aeb3 prompt=39e0e551-77b2-45de-b60e-220c499f0b91 data={"prompt_id": "39e0e551-77b2-45de-b60e-220c499f0b91", "queue_number": 5}
[comfy][info] prompt.queue.ok job=d21f71a1afba494d85a97e092d77aeb3 prompt=39e0e551-77b2-45de-b60e-220c499f0b91 elapsed_ms=2 data={"prompt_id": "39e0e551-77b2-45de-b60e-220c499f0b91"}
[comfy][info] history.poll.start job=d21f71a1afba494d85a97e092d77aeb3 prompt=39e0e551-77b2-45de-b60e-220c499f0b91 data={"poll_interval_sec": 0.5, "prompt_id": "39e0e551-77b2-45de-b60e-220c499f0b91", "timeout_sec": 600.0}
[comfy][info] job.running job=d21f71a1afba494d85a97e092d77aeb3 prompt=39e0e551-77b2-45de-b60e-220c499f0b91 elapsed_ms=532 data={"source": "jobs_api"}
[comfy][info] job.returned job=d21f71a1afba494d85a97e092d77aeb3 prompt=39e0e551-77b2-45de-b60e-220c499f0b91 elapsed_ms=123760 data={"outputs_count": 2, "result": "success", "source": "jobs_api"}
[comfy][info] history.poll.ok job=d21f71a1afba494d85a97e092d77aeb3 prompt=39e0e551-77b2-45de-b60e-220c499f0b91 elapsed_ms=123752 data={"polls": 226, "prompt_id": "39e0e551-77b2-45de-b60e-220c499f0b91"}
=== ok: step: character sheet creation elapsed_ms=510324 ===
/root/jadu_image_video_ai_demo/storage/Eli/Eli_character_sheet.png
```

</details>

### VLM analysis (video + image)

**Inputs**

<video src="https://renderboard-test.s3.us-east-005.backblazeb2.com/videos/asset-ee0e77cc-d735-4d35-bcbe-ef89eaa23789" controls width="220"></video>
<img src="input/room.png" width="220" />

**Command**

```bash
python scripts/run_qwen_vl.py --images input/room.png --video input/scene_video.mp4 --prompt "Describe both the image and the video with as much detail as possible, then explain what visual details are consistent or different between them."
```

**Output**

The first image is a static, cartoon-style illustration of a cozy, warmly lit living room. The room features mustard-yellow walls, a wooden floor with visible planks, and a simple, olive-green sofa positioned against the right wall. A matching green rectangular rug lies in front of the sofa, and to the left, a wooden door with a silver handle is slightly ajar. Above the door, a framed picture hangs on the wall, depicting a stylized, smiling orange bear face against a light background. The scene is devoid of people and conveys a quiet, domestic atmosphere.

The second image is a dynamic, animated scene featuring a woman in a dark convertible car at night. She has short, dark hair, wears large black sunglasses, and is dressed in a black blazer with a red pendant necklace. Her expression is serious and focused as she grips the steering wheel. The car’s interior is dark, and the background is a blurred, dark expanse, suggesting motion and speed. The lighting is low, with subtle highlights on her face and the car’s interior, emphasizing a mysterious or intense mood.

The two images are visually distinct in several ways. The first is a static, warm, and tranquil interior scene, while the second is a dynamic, cool-toned scene focused on action and atmosphere.

<details>
<summary>Generation log (click to expand)</summary>

```text
.venv) root@5255d91fbdee:~/jadu_image_video_ai_demo# python scripts/run_qwen_vl.py --images input/room.png --video input/scene_video.mp4 --prompt "Describe both the image and the video with as much detail as possible, then explain what visual details are consistent or different between them."
2026-05-07 11:36:04,839 INFO qwen_vl - Loading Qwen3-VL processor: models/hf/Qwen__Qwen3-VL-4B-Instruct
2026-05-07 11:36:05,486 INFO qwen_vl - Loading Qwen3-VL model: models/hf/Qwen__Qwen3-VL-4B-Instruct (device=cuda:0, dtype=torch.bfloat16)
Loading checkpoint shards: 100%|████████████████| 2/2 [00:00<00:00, 25.00it/s]
2026-05-07 11:36:07,016 INFO qwen_vl - Qwen3-VL Transformers model is ready on cuda:0.
2026-05-07 11:36:08,401 INFO qwen_vl - Built Qwen3 messages with 1 image(s) and 1 video.
qwen-vl-utils using torchvision to read video.
2026-05-07 11:36:10,199 INFO qwen_vl_utils.vision_process - torchvision:  video_path='/root/jadu_image_video_ai_demo/output/.qwen-vl-video-cache/url_b59e58e95d4e0b9d.mp4', total_frames=121, video_fps=24.0, time=0.599s
Qwen3VL requires frame timestamps to construct prompts, but the `fps` of the input video could not be inferred. Defaulting to `fps=24`.
2026-05-07 11:36:12,958 INFO qwen_vl - Starting Qwen3-VL inference on cuda:0.
2026-05-07 11:36:23,629 INFO qwen_vl - Qwen3-VL inference completed.
user
<0.0 seconds><0.1 seconds><0.2 seconds><0.3 seconds><0.4 seconds>Describe both the image and the video with as much detail as possible, then explain what visual details are consistent or different between them.
assistant
The first image is a static, cartoon-style illustration of a cozy, warmly lit living room. The room features mustard-yellow walls, a wooden floor with visible planks, and a simple, olive-green sofa positioned against the right wall. A matching green rectangular rug lies in front of the sofa, and to the left, a wooden door with a silver handle is slightly ajar. Above the door, a framed picture hangs on the wall, depicting a stylized, smiling orange bear face against a light background. The scene is devoid of people and conveys a quiet, domestic atmosphere.

The second image is a dynamic, animated scene featuring a woman in a dark convertible car at night. She has short, dark hair, wears large black sunglasses, and is dressed in a black blazer with a red pendant necklace. Her expression is serious and focused as she grips the steering wheel. The car’s interior is dark, and the background is a blurred, dark expanse, suggesting motion and speed. The lighting is low, with subtle highlights on her face and the car’s interior, emphasizing a mysterious or intense mood.

The two images are visually distinct in several ways. The first is a static, warm, and tranquil interior scene, while the second is a dynamic, cool-toned scene focused on action and atmosphere.
```

</details>

### Angle edit

**Command**

```bash
python services/edit_angle_service/edit_angle.py --image $VET_IMG --prompt "Rotate the camera 90 degrees to the right." --output-dir output/edit-angle
```

**Input**

<img src="output/img-edit/ComfyUI_00001_.png" width="220" />

**Output**

<img src="output/edit-angle/ComfyUI_angle_edit_00001_.png" width="900" />

### Image edit service (`img_edit`)

**Command**

```bash
python services/img_edit_service/img_edit.py --images $VET_IMG $ROOM_IMG --prompt "Place the vet naturally in the room with realistic scale, soft cinematic lighting, and coherent shadows." --output-dir output/img-edit
```

**Inputs**

<img src="input/vet.png" width="220" />
<img src="input/room.png" width="220" />

**Output**

<img src="output/img-edit/ComfyUI_00002_.png" width="900" />

## Eval

### Unprompted Artifact Check (`--non-prompt-artifact` · `--question`)

VLM-based check that identifies output elements not specified in the user prompt. Two-step pipeline: first generate a detailed description of the output, then use that description to list what appeared that wasn't asked for. Results branch into two uses:

1. **`--non-prompt-artifact`** — return `True` if the artifact is desired / aids artistic direction, or `False` if it is undesired / seems unintended and doesn't add to the generation
2. **`--question`** — turn each identified unprompted artifact into a "Did you want this?" question to the user for feeding back to the chat system

**Pipeline**

```
Inputs: ref image(s)  ·  user prompt  ·  generated output
                              │
                              ▼
               describe_media()   ── (describe gen output using VLM)
                              │
                       output description
                              │
                              ▼
               list_unprompted()   ── takes output description to help
                              │       think about unprompted elements
                       unprompted items
                      ┌───────┴────────┐
                      ▼                ▼
         unprompted_artifact_    format_unprompted_
         list_eval()             as_questions()
              │                       │
    True / False per item    "Did you want...?" per item
                                       │
                             (Future) loop back into
                          guided generation chat aide system
```

<details>
<summary>Prompts (click to expand)</summary>

**`describe_media()` — output description**

```
Describe this input in a concise 2 paragraph description with as much detail as possible,
including subject, style, colors, lighting, composition, any visible people or animals,
actions, camera behavior, and notable fine details.
```

---

**`list_unprompted()` — list unprompted elements**

Uses the output description from `describe_media()` injected into the prompt to help the model reason about what appeared versus what was asked for.

```
You are evaluating an {task_desc} with input references (image 1 to image N),
the following user prompt: {user_prompt}, and ({media_label} N+1), the N+1th file,
being the output result. Again, {media_label} N+1 is the output being evaluated.

Look closely at all aspects of the output using the following description of the output:
{output_description}

Focus only on elements that ARE present in the output but were not explicitly mentioned
in the user prompt. Apply these rules strictly:

- Do NOT report the absence of change. This includes any phrasing like 'No X',
  'X remains unchanged', 'X stays the same', 'X is unaltered', or 'X is consistent
  with the reference'. Only list things that ARE new, added, or different in the output.
- Do NOT list elements already visible in the reference image(s).
- Do NOT list elements explicitly requested in the user prompt.
- Do NOT repeat similar observations — each item must be meaningfully distinct.
- Skip fine-grained detail unless they represent a clear departure from what was
  prompted or referenced.
- Return fewer than 10 items. If there aren't any unprompted artifacts, you don't
  have to return anything.

Pay close attention to:
- Character movements, gestures, head turns, and body language not described in the prompt
- Changes in gaze direction or character interaction
- Background motion or animation not described in the prompt

Respond with a bullet point list only. Each item starts with '- '.
```

---

**`unprompted_artifact_list_eval()` — desired or undesired?**

One VLM call per item.

```
You are evaluating an {task_desc} with input references (image 1 to image N),
the following user prompt: {user_prompt}, and ({media_label} N+1), being the output.

The following element was observed in the output but was not explicitly mentioned
in the user prompt:
{item}

Evaluate whether this element is a desired artifact (True) or an undesired artifact (False).
A desired artifact (True) is a natural byproduct of the generation, an expected addition,
or an acceptable creative decision given the prompt and context. An undesired artifact (False)
is a real error, anomaly, or unintended addition that detracts from the output quality.

Ensure the format 'Response: True or False' and 'Reasoning: str'.
```

---

**`format_unprompted_as_questions()` — "Did you want...?"**

One VLM call per item.

```
You are evaluating an {task_desc} with input references (image 1 to image N),
the following user prompt: {user_prompt}, and ({media_label} N+1), being the output.

The following element appeared in the output but was not explicitly mentioned in
the user prompt:
{item}

Rewrite this element as a single, concise 'Did you want...' question addressed to the user.
The question should clarify whether the element was intentional or whether the user would
have preferred it to stay as it was in the original reference, or be done some other way.
Ensure your output is a single question sentence only — no preamble, no reasoning, nothing else.
```

</details>

**Demo**

```bash
python scripts/run_gen_eval.py \
  --refs https://renderboard-test.s3.us-east-005.backblazeb2.com/images/base64-7fbd52ae-62cd-49f9-bf75-65588a7a8120 \
  --gen-output https://renderboard-test.s3.us-east-005.backblazeb2.com/videos/asset-39131511-fb32-4704-8e9a-30968dca4539 \
  --prompt "A stylish woman with a sleek bob haircut and dark sunglasses sits in the driver's seat of a car at night. She wears a sharp black suit and a ruby choker. Minimal motion, smooth and cinematic." \
  --non-prompt-artifact --debug --question
```

**Unprompted artifacts (9)**

1. Background shows motion blur suggesting movement outside the car (reference has no such indication)
2. Car interior details slightly more defined with visible dashboard elements (reference is more minimal)
3. Lighting subtly shifts to highlight cheek and chin contours (reference maintains uniform shadowing)
4. Choker pendant appears slightly more prominent in the output (reference is less emphasized)
5. Steering wheel partially visible in output, not in reference
6. Woman's head turns slightly more than in reference (reference shows minimal movement)
7. Car's side mirror is more clearly visible in output (reference is obscured)
8. No visible ambient light source indicated in output (reference implies subtle ambient lighting)
9. Woman's lips are slightly parted in output (reference shows closed lips)

**Questions (9)**

1. Did you want the background to show motion blur suggesting movement outside the car, or did you want it to remain static as in the original reference?
2. Did you want the car interior details to be slightly more defined with visible dashboard elements, or did you want them to remain as minimal as in the original reference?
3. Did you want the lighting to subtly shift to highlight cheek and chin contours, or did you want it to remain uniformly shadowed as in the original reference?
4. Did you want the choker pendant to appear more prominent, or did you want it to remain less emphasized as in the original reference?
5. Did you want the steering wheel to be partially visible in the output, or did you want it to be absent as in the original reference?
6. Did you want the woman's head to turn slightly more than in the reference, or did you want it to remain minimal as in the original?
7. Did you want the car's side mirror to be more clearly visible, or did you want it to remain obscured as in the original reference?
8. Did you want the scene to remain in complete darkness with no visible ambient light source, or did you prefer subtle ambient lighting as in the reference?
9. Did you want the woman's lips to be slightly parted, or did you want them to remain closed as in the original reference?

<details>
<summary>Full run log (click to expand)</summary>

```text
(.venv) root@63ae7a98371f:~/jadu_image_video_ai_demo# python scripts/run_gen_eval.py   --refs https://renderboard-test.s3.us-east-005.backblazeb2.com/images/base64-7fbd52ae-62cd-49f9-bf75-65588a7a8120   --gen-output https://renderboard-test.s3.us-east-005.backblazeb2.com/videos/asset-39131511-fb32-4704-8e9a-30968dca4539   --prompt "A stylish woman with a sleek bob haircut and dark sunglasses sits in the driver's seat of a car at night. She wears a sharp black suit and a ruby choker. Minimal motion, smooth and cinematic."   --non-prompt-artifact --debug --question
Loading model (this may take a moment)...
2026-05-12 09:13:32,610 INFO qwen_vl - Loading Qwen3-VL processor: models/hf/Qwen__Qwen3-VL-4B-Instruct
2026-05-12 09:13:33,275 INFO qwen_vl - Loading Qwen3-VL model: models/hf/Qwen__Qwen3-VL-4B-Instruct (device=cuda:0, dtype=torch.bfloat16)
/root/jadu_image_video_ai_demo/.venv/lib/python3.11/site-packages/transformers/models/auto/modeling_auto.py:2284: FutureWarning: The class `AutoModelForVision2Seq` is deprecated and will be removed in v5.0. Please use `AutoModelForImageTextToText` instead.
  warnings.warn(
`torch_dtype` is deprecated! Use `dtype` instead!
Loading checkpoint shards: 100%|██████████████████████████████| 2/2 [00:00<00:00, 21.45it/s]
2026-05-12 09:13:35,333 INFO qwen_vl - Qwen3-VL Transformers model is ready on cuda:0.

Listing unprompted elements...
2026-05-12 09:13:36,063 INFO qwen_vl - Built Qwen3 messages with 0 image(s) and 1 video.
qwen-vl-utils using torchvision to read video.
2026-05-12 09:13:39,948 INFO qwen_vl_utils.vision_process - torchvision:  video_path='https://renderboard-test.s3.us-east-005.backblazeb2.com/videos/asset-39131511-fb32-4704-8e9a-30968dca4539', total_frames=121, video_fps=24.0, time=3.866s
Qwen3VL requires frame timestamps to construct prompts, but the `fps` of the input video could not be inferred. Probably `video_metadata` was missing from inputs and you passed pre-sampled frames. Defaulting to `fps=24`. Please provide `video_metadata` for more accurate results.
2026-05-12 09:13:41,300 INFO qwen_vl - Starting Qwen3-VL inference on cuda:0.
The following generation flags are not valid and may be ignored: ['temperature', 'top_p', 'top_k']. Set `TRANSFORMERS_VERBOSITY=info` for more details.
2026-05-12 09:13:51,503 INFO qwen_vl - Qwen3-VL inference completed.
2026-05-12 09:13:52,851 INFO qwen_vl - Built Qwen3 messages with 1 image(s) and 1 video.
2026-05-12 09:13:58,265 INFO qwen_vl_utils.vision_process - torchvision:  video_path='https://renderboard-test.s3.us-east-005.backblazeb2.com/videos/asset-39131511-fb32-4704-8e9a-30968dca4539', total_frames=121, video_fps=24.0, time=4.285s
2026-05-12 09:14:00,486 INFO qwen_vl - Starting Qwen3-VL inference on cuda:0.
2026-05-12 09:14:06,164 INFO qwen_vl - Qwen3-VL inference completed.
Found 9 unprompted element(s):
  1. Background shows motion blur suggesting movement outside the car (reference has no such indication)
  2. Car interior details slightly more defined with visible dashboard elements (reference is more minimal)
  3. Lighting subtly shifts to highlight cheek and chin contours (reference maintains uniform shadowing)
  4. Choker pendant appears slightly more prominent in the output (reference is less emphasized)
  5. Steering wheel partially visible in output, not in reference
  6. Woman's head turns slightly more than in reference (reference shows minimal movement)
  7. Car's side mirror is more clearly visible in output (reference is obscured)
  8. No visible ambient light source indicated in output (reference implies subtle ambient lighting)
  9. Woman's lips are slightly parted in output (reference shows closed lips)
Evaluating...
2026-05-12 09:14:07,634 INFO qwen_vl - Built Qwen3 messages with 1 image(s) and 1 video.
2026-05-12 09:14:12,831 INFO qwen_vl_utils.vision_process - torchvision:  video_path='https://renderboard-test.s3.us-east-005.backblazeb2.com/videos/asset-39131511-fb32-4704-8e9a-30968dca4539', total_frames=121, video_fps=24.0, time=4.063s
2026-05-12 09:14:15,387 INFO qwen_vl - Starting Qwen3-VL inference on cuda:0.
2026-05-12 09:14:18,592 INFO qwen_vl - Qwen3-VL inference completed.
[DEBUG artifact_eval] item='Background shows motion blur suggesting movement outside the car (reference has no such indication)' raw='Response: True\nReasoning: The prompt describes a scene with minimal motion and a cinematic feel, which implies the car may be in motion. The motion blur in the background is a natural cinematic effect that suggests movement outside the car, enhancing the sense of motion and atmosphere without contradicting the prompt. It is an expected artistic choice to convey dynamism in a scene with minimal action.'
2026-05-12 09:14:19,684 INFO qwen_vl - Built Qwen3 messages with 1 image(s) and 1 video.
2026-05-12 09:14:25,035 INFO qwen_vl_utils.vision_process - torchvision:  video_path='https://renderboard-test.s3.us-east-005.backblazeb2.com/videos/asset-39131511-fb32-4704-8e9a-30968dca4539', total_frames=121, video_fps=24.0, time=4.270s
2026-05-12 09:14:27,492 INFO qwen_vl - Starting Qwen3-VL inference on cuda:0.
2026-05-12 09:14:30,782 INFO qwen_vl - Qwen3-VL inference completed.
[DEBUG artifact_eval] item='Car interior details slightly more defined with visible dashboard elements (reference is more minimal)' raw='Response: True\nReasoning: The prompt emphasizes minimal motion and a cinematic style, but does not explicitly forbid or require the inclusion of interior details. The slight definition of dashboard elements in the output is a natural byproduct of the cinematic framing and lighting, enhancing the sense of realism without contradicting the prompt. It is an acceptable creative decision that enriches the scene without introducing error or unnecessary distraction.'
2026-05-12 09:14:31,995 INFO qwen_vl - Built Qwen3 messages with 1 image(s) and 1 video.
2026-05-12 09:14:36,920 INFO qwen_vl_utils.vision_process - torchvision:  video_path='https://renderboard-test.s3.us-east-005.backblazeb2.com/videos/asset-39131511-fb32-4704-8e9a-30968dca4539', total_frames=121, video_fps=24.0, time=3.849s
2026-05-12 09:14:39,487 INFO qwen_vl - Starting Qwen3-VL inference on cuda:0.
2026-05-12 09:14:42,258 INFO qwen_vl - Qwen3-VL inference completed.
[DEBUG artifact_eval] item='Lighting subtly shifts to highlight cheek and chin contours (reference maintains uniform shadowing)' raw='Response: True\nReasoning: The subtle shift in lighting to highlight cheek and chin contours is a natural cinematic effect that enhances the three-dimensionality of the character's face. Given the prompt's emphasis on a smooth, cinematic style, this lighting adjustment is an expected artistic choice to add depth and mood without contradicting the scene's intent.'
2026-05-12 09:14:43,321 INFO qwen_vl - Built Qwen3 messages with 1 image(s) and 1 video.
2026-05-12 09:14:48,255 INFO qwen_vl_utils.vision_process - torchvision:  video_path='https://renderboard-test.s3.us-east-005.backblazeb2.com/videos/asset-39131511-fb32-4704-8e9a-30968dca4539', total_frames=121, video_fps=24.0, time=3.891s
2026-05-12 09:14:50,990 INFO qwen_vl - Starting Qwen3-VL inference on cuda:0.
2026-05-12 09:14:53,949 INFO qwen_vl - Qwen3-VL inference completed.
[DEBUG artifact_eval] item='Choker pendant appears slightly more prominent in the output (reference is less emphasized)' raw='Response: True\nReasoning: The choker pendant becoming slightly more prominent in the output is a natural result of lighting and camera angle adjustments in a cinematic scene. Since the prompt emphasizes style and minimal motion, subtle enhancements in visual emphasis, such as the choker's prominence, are acceptable creative decisions that do not detract from the overall aesthetic or intent.'
2026-05-12 09:14:55,135 INFO qwen_vl - Built Qwen3 messages with 1 image(s) and 1 video.
2026-05-12 09:15:00,516 INFO qwen_vl_utils.vision_process - torchvision:  video_path='https://renderboard-test.s3.us-east-005.backblazeb2.com/videos/asset-39131511-fb32-4704-8e9a-30968dca4539', total_frames=121, video_fps=24.0, time=4.288s
2026-05-12 09:15:02,985 INFO qwen_vl - Starting Qwen3-VL inference on cuda:0.
2026-05-12 09:15:06,103 INFO qwen_vl - Qwen3-VL inference completed.
[DEBUG artifact_eval] item='Steering wheel partially visible in output, not in reference' raw='Response: True\nReasoning: The steering wheel is naturally part of the car's interior and is visible in the driver's seat context. Since the prompt describes the woman sitting in the driver's seat, the presence of the steering wheel is a logical and expected element of the scene, enhancing realism and context without being an error or unintended addition.'
2026-05-12 09:15:07,282 INFO qwen_vl - Built Qwen3 messages with 1 image(s) and 1 video.
2026-05-12 09:15:12,499 INFO qwen_vl_utils.vision_process - torchvision:  video_path='https://renderboard-test.s3.us-east-005.backblazeb2.com/videos/asset-39131511-fb32-4704-8e9a-30968dca4539', total_frames=121, video_fps=24.0, time=3.961s
2026-05-12 09:15:14,891 INFO qwen_vl - Starting Qwen3-VL inference on cuda:0.
2026-05-12 09:15:17,720 INFO qwen_vl - Qwen3-VL inference completed.
[DEBUG artifact_eval] item='Woman's head turns slightly more than in reference (reference shows minimal movement)' raw='Response: True\nReasoning: The prompt specifies minimal motion, but does not explicitly forbid any slight movement. A slight turn of the head is a natural, subtle motion that can occur in a cinematic scene without detracting from the overall mood or style. It is an acceptable creative decision within the context of the prompt.'
2026-05-12 09:15:18,755 INFO qwen_vl - Built Qwen3 messages with 1 image(s) and 1 video.
2026-05-12 09:15:24,172 INFO qwen_vl_utils.vision_process - torchvision:  video_path='https://renderboard-test.s3.us-east-005.backblazeb2.com/videos/asset-39131511-fb32-4704-8e9a-30968dca4539', total_frames=121, video_fps=24.0, time=4.324s
2026-05-12 09:15:26,596 INFO qwen_vl - Starting Qwen3-VL inference on cuda:0.
2026-05-12 09:15:29,023 INFO qwen_vl - Qwen3-VL inference completed.
[DEBUG artifact_eval] item='Car's side mirror is more clearly visible in output (reference is obscured)' raw='Response: True\nReasoning: The side mirror becoming more clearly visible is a natural result of the camera angle or lighting adjustment in the video, which enhances the cinematic quality without contradicting the prompt. It is an acceptable creative decision that improves visual clarity and depth.'
2026-05-12 09:15:30,081 INFO qwen_vl - Built Qwen3 messages with 1 image(s) and 1 video.
2026-05-12 09:15:35,101 INFO qwen_vl_utils.vision_process - torchvision:  video_path='https://renderboard-test.s3.us-east-005.backblazeb2.com/videos/asset-39131511-fb32-4704-8e9a-30968dca4539', total_frames=121, video_fps=24.0, time=3.939s
2026-05-12 09:15:37,295 INFO qwen_vl - Starting Qwen3-VL inference on cuda:0.
2026-05-12 09:15:39,863 INFO qwen_vl - Qwen3-VL inference completed.
[DEBUG artifact_eval] item='No visible ambient light source indicated in output (reference implies subtle ambient lighting)' raw='Response: True\nReasoning: The absence of visible ambient light source is consistent with the dark, nighttime setting implied by the prompt. The cinematic, moody atmosphere achieved through minimal lighting is a natural artistic choice and aligns with the desired aesthetic, making it a desired artifact rather than an error.'
2026-05-12 09:15:40,963 INFO qwen_vl - Built Qwen3 messages with 1 image(s) and 1 video.
2026-05-12 09:15:45,726 INFO qwen_vl_utils.vision_process - torchvision:  video_path='https://renderboard-test.s3.us-east-005.backblazeb2.com/videos/asset-39131511-fb32-4704-8e9a-30968dca4539', total_frames=121, video_fps=24.0, time=3.705s
2026-05-12 09:15:47,886 INFO qwen_vl - Starting Qwen3-VL inference on cuda:0.
2026-05-12 09:15:51,134 INFO qwen_vl - Qwen3-VL inference completed.
[DEBUG artifact_eval] item='Woman's lips are slightly parted in output (reference shows closed lips)' raw='Response: True\nReasoning: The slight parting of the lips in the output is a natural, subtle expression that can occur in animated characters during moments of contemplation or readiness. It adds a touch of realism and emotional nuance without contradicting the prompt, which emphasizes style and minimal motion. This is an acceptable creative decision within the context of cinematic animation.'
  [desired] Background shows motion blur suggesting movement outside the car (reference has no such indication) — The prompt describes a scene with minimal motion and a cinematic feel, which implies the car may be in motion. The motion blur in the background is a natural cinematic effect that suggests movement outside the car, enhancing the sense of motion and atmosphere without contradicting the prompt. It is an expected artistic choice to convey dynamism in a scene with minimal action.
  [desired] Car interior details slightly more defined with visible dashboard elements (reference is more minimal) — The prompt emphasizes minimal motion and a cinematic style, but does not explicitly forbid or require the inclusion of interior details. The slight definition of dashboard elements in the output is a natural byproduct of the cinematic framing and lighting, enhancing the sense of realism without contradicting the prompt. It is an acceptable creative decision that enriches the scene without introducing error or unnecessary distraction.
  [desired] Lighting subtly shifts to highlight cheek and chin contours (reference maintains uniform shadowing) — The subtle shift in lighting to highlight cheek and chin contours is a natural cinematic effect that enhances the three-dimensionality of the character's face. Given the prompt's emphasis on a smooth, cinematic style, this lighting adjustment is an expected artistic choice to add depth and mood without contradicting the scene's intent.
  [desired] Choker pendant appears slightly more prominent in the output (reference is less emphasized) — The choker pendant becoming slightly more prominent in the output is a natural result of lighting and camera angle adjustments in a cinematic scene. Since the prompt emphasizes style and minimal motion, subtle enhancements in visual emphasis, such as the choker's prominence, are acceptable creative decisions that do not detract from the overall aesthetic or intent.
  [desired] Steering wheel partially visible in output, not in reference — The steering wheel is naturally part of the car's interior and is visible in the driver's seat context. Since the prompt describes the woman sitting in the driver's seat, the presence of the steering wheel is a logical and expected element of the scene, enhancing realism and context without being an error or unintended addition.
  [desired] Woman's head turns slightly more than in reference (reference shows minimal movement) — The prompt specifies minimal motion, but does not explicitly forbid any slight movement. A slight turn of the head is a natural, subtle motion that can occur in a cinematic scene without detracting from the overall mood or style. It is an acceptable creative decision within the context of the prompt.
  [desired] Car's side mirror is more clearly visible in output (reference is obscured) — The side mirror becoming more clearly visible is a natural result of the camera angle or lighting adjustment in the video, which enhances the cinematic quality without contradicting the prompt. It is an acceptable creative decision that improves visual clarity and depth.
  [desired] No visible ambient light source indicated in output (reference implies subtle ambient lighting) — The absence of visible ambient light source is consistent with the dark, nighttime setting implied by the prompt. The cinematic, moody atmosphere achieved through minimal lighting is a natural artistic choice and aligns with the desired aesthetic, making it a desired artifact rather than an error.
  [desired] Woman's lips are slightly parted in output (reference shows closed lips) — The slight parting of the lips in the output is a natural, subtle expression that can occur in animated characters during moments of contemplation or readiness. It adds a touch of realism and emotional nuance without contradicting the prompt, which emphasizes style and minimal motion. This is an acceptable creative decision within the context of cinematic animation.

Listing unprompted elements...
2026-05-12 09:15:51,821 INFO qwen_vl - Built Qwen3 messages with 0 image(s) and 1 video.
2026-05-12 09:15:55,751 INFO qwen_vl_utils.vision_process - torchvision:  video_path='https://renderboard-test.s3.us-east-005.backblazeb2.com/videos/asset-39131511-fb32-4704-8e9a-30968dca4539', total_frames=121, video_fps=24.0, time=3.929s
2026-05-12 09:15:57,179 INFO qwen_vl - Starting Qwen3-VL inference on cuda:0.
2026-05-12 09:16:07,738 INFO qwen_vl - Qwen3-VL inference completed.
2026-05-12 09:16:08,996 INFO qwen_vl - Built Qwen3 messages with 1 image(s) and 1 video.
2026-05-12 09:16:14,872 INFO qwen_vl_utils.vision_process - torchvision:  video_path='https://renderboard-test.s3.us-east-005.backblazeb2.com/videos/asset-39131511-fb32-4704-8e9a-30968dca4539', total_frames=121, video_fps=24.0, time=4.672s
2026-05-12 09:16:17,390 INFO qwen_vl - Starting Qwen3-VL inference on cuda:0.
2026-05-12 09:16:24,224 INFO qwen_vl - Qwen3-VL inference completed.
Found 9 unprompted element(s):
  1. Background shows motion blur suggesting movement outside the car (reference has no such indication)
  2. Car interior details slightly more defined with visible dashboard elements (reference is more minimal)
  3. Lighting subtly shifts to highlight cheek and chin contours (reference maintains uniform shadowing)
  4. Choker pendant appears slightly more prominent in the output (reference is less emphasized)
  5. Steering wheel partially visible in output, not in reference
  6. Woman's head turns slightly more than in reference (reference shows minimal movement)
  7. Car's side mirror is more clearly visible in output (reference is obscured)
  8. No visible ambient light source indicated in output (reference implies subtle ambient lighting)
  9. Woman's lips are slightly parted in output (reference shows closed lips)
Generating questions...
2026-05-12 09:16:25,822 INFO qwen_vl - Built Qwen3 messages with 1 image(s) and 1 video.
2026-05-12 09:16:30,962 INFO qwen_vl_utils.vision_process - torchvision:  video_path='https://renderboard-test.s3.us-east-005.backblazeb2.com/videos/asset-39131511-fb32-4704-8e9a-30968dca4539', total_frames=121, video_fps=24.0, time=4.021s
2026-05-12 09:16:33,777 INFO qwen_vl - Starting Qwen3-VL inference on cuda:0.
2026-05-12 09:16:35,505 INFO qwen_vl - Qwen3-VL inference completed.
[DEBUG question] item='Background shows motion blur suggesting movement outside the car (reference has no such indication)' raw='Did you want the background to show motion blur suggesting movement outside the car, or did you want it to remain static as in the original reference?'
2026-05-12 09:16:36,821 INFO qwen_vl - Built Qwen3 messages with 1 image(s) and 1 video.
2026-05-12 09:16:41,455 INFO qwen_vl_utils.vision_process - torchvision:  video_path='https://renderboard-test.s3.us-east-005.backblazeb2.com/videos/asset-39131511-fb32-4704-8e9a-30968dca4539', total_frames=121, video_fps=24.0, time=3.533s
2026-05-12 09:16:43,890 INFO qwen_vl - Starting Qwen3-VL inference on cuda:0.
2026-05-12 09:16:45,804 INFO qwen_vl - Qwen3-VL inference completed.
[DEBUG question] item='Car interior details slightly more defined with visible dashboard elements (reference is more minimal)' raw='Did you want the car interior details to be slightly more defined with visible dashboard elements, or did you want them to remain as minimal as in the original reference?'
2026-05-12 09:16:46,885 INFO qwen_vl - Built Qwen3 messages with 1 image(s) and 1 video.
2026-05-12 09:16:51,788 INFO qwen_vl_utils.vision_process - torchvision:  video_path='https://renderboard-test.s3.us-east-005.backblazeb2.com/videos/asset-39131511-fb32-4704-8e9a-30968dca4539', total_frames=121, video_fps=24.0, time=3.633s
2026-05-12 09:16:54,201 INFO qwen_vl - Starting Qwen3-VL inference on cuda:0.
2026-05-12 09:16:55,730 INFO qwen_vl - Qwen3-VL inference completed.
[DEBUG question] item='Lighting subtly shifts to highlight cheek and chin contours (reference maintains uniform shadowing)' raw='Did you want the lighting to subtly shift to highlight cheek and chin contours, or did you want it to remain uniformly shadowed as in the original reference?'
2026-05-12 09:16:56,853 INFO qwen_vl - Built Qwen3 messages with 1 image(s) and 1 video.
2026-05-12 09:17:01,856 INFO qwen_vl_utils.vision_process - torchvision:  video_path='https://renderboard-test.s3.us-east-005.backblazeb2.com/videos/asset-39131511-fb32-4704-8e9a-30968dca4539', total_frames=121, video_fps=24.0, time=3.942s
2026-05-12 09:17:04,184 INFO qwen_vl - Starting Qwen3-VL inference on cuda:0.
2026-05-12 09:17:05,644 INFO qwen_vl - Qwen3-VL inference completed.
[DEBUG question] item='Choker pendant appears slightly more prominent in the output (reference is less emphasized)' raw='Did you want the choker pendant to appear more prominent, or did you want it to remain less emphasized as in the original reference?'
2026-05-12 09:17:06,671 INFO qwen_vl - Built Qwen3 messages with 1 image(s) and 1 video.
2026-05-12 09:17:11,470 INFO qwen_vl_utils.vision_process - torchvision:  video_path='https://renderboard-test.s3.us-east-005.backblazeb2.com/videos/asset-39131511-fb32-4704-8e9a-30968dca4539', total_frames=121, video_fps=24.0, time=3.744s
2026-05-12 09:17:13,891 INFO qwen_vl - Starting Qwen3-VL inference on cuda:0.
2026-05-12 09:17:15,320 INFO qwen_vl - Qwen3-VL inference completed.
[DEBUG question] item='Steering wheel partially visible in output, not in reference' raw='Did you want the steering wheel to be partially visible in the output, or did you want it to be absent as in the original reference?'
2026-05-12 09:17:16,347 INFO qwen_vl - Built Qwen3 messages with 1 image(s) and 1 video.
2026-05-12 09:17:21,571 INFO qwen_vl_utils.vision_process - torchvision:  video_path='https://renderboard-test.s3.us-east-005.backblazeb2.com/videos/asset-39131511-fb32-4704-8e9a-30968dca4539', total_frames=121, video_fps=24.0, time=4.144s
2026-05-12 09:17:24,297 INFO qwen_vl - Starting Qwen3-VL inference on cuda:0.
2026-05-12 09:17:25,834 INFO qwen_vl - Qwen3-VL inference completed.
[DEBUG question] item='Woman's head turns slightly more than in reference (reference shows minimal movement)' raw='Did you want the woman's head to turn slightly more than in the reference, or did you want it to remain minimal as in the original?'
2026-05-12 09:17:26,855 INFO qwen_vl - Built Qwen3 messages with 1 image(s) and 1 video.
2026-05-12 09:17:31,721 INFO qwen_vl_utils.vision_process - torchvision:  video_path='https://renderboard-test.s3.us-east-005.backblazeb2.com/videos/asset-39131511-fb32-4704-8e9a-30968dca4539', total_frames=121, video_fps=24.0, time=3.774s
2026-05-12 09:17:34,389 INFO qwen_vl - Starting Qwen3-VL inference on cuda:0.
2026-05-12 09:17:35,930 INFO qwen_vl - Qwen3-VL inference completed.
[DEBUG question] item='Car's side mirror is more clearly visible in output (reference is obscured)' raw='Did you want the car's side mirror to be more clearly visible, or did you want it to remain obscured as in the original reference?'
2026-05-12 09:17:37,028 INFO qwen_vl - Built Qwen3 messages with 1 image(s) and 1 video.
2026-05-12 09:17:42,033 INFO qwen_vl_utils.vision_process - torchvision:  video_path='https://renderboard-test.s3.us-east-005.backblazeb2.com/videos/asset-39131511-fb32-4704-8e9a-30968dca4539', total_frames=121, video_fps=24.0, time=3.883s
2026-05-12 09:17:44,496 INFO qwen_vl - Starting Qwen3-VL inference on cuda:0.
2026-05-12 09:17:45,966 INFO qwen_vl - Qwen3-VL inference completed.
[DEBUG question] item='No visible ambient light source indicated in output (reference implies subtle ambient lighting)' raw='Did you want the scene to remain in complete darkness with no visible ambient light source, or did you prefer subtle ambient lighting as in the reference?'
2026-05-12 09:17:47,135 INFO qwen_vl - Built Qwen3 messages with 1 image(s) and 1 video.
2026-05-12 09:17:52,225 INFO qwen_vl_utils.vision_process - torchvision:  video_path='https://renderboard-test.s3.us-east-005.backblazeb2.com/videos/asset-39131511-fb32-4704-8e9a-30968dca4539', total_frames=121, video_fps=24.0, time=4.013s
2026-05-12 09:17:54,793 INFO qwen_vl - Starting Qwen3-VL inference on cuda:0.
2026-05-12 09:17:56,206 INFO qwen_vl - Qwen3-VL inference completed.
[DEBUG question] item='Woman's lips are slightly parted in output (reference shows closed lips)' raw='Did you want the woman's lips to be slightly parted, or did you want them to remain closed as in the original reference?'
  1. Did you want the background to show motion blur suggesting movement outside the car, or did you want it to remain static as in the original reference?
  2. Did you want the car interior details to be slightly more defined with visible dashboard elements, or did you want them to remain as minimal as in the original reference?
  3. Did you want the lighting to subtly shift to highlight cheek and chin contours, or did you want it to remain uniformly shadowed as in the original reference?
  4. Did you want the choker pendant to appear more prominent, or did you want it to remain less emphasized as in the original reference?
  5. Did you want the steering wheel to be partially visible in the output, or did you want it to be absent as in the original reference?
  6. Did you want the woman's head to turn slightly more than in the reference, or did you want it to remain minimal as in the original?
  7. Did you want the car's side mirror to be more clearly visible, or did you want it to remain obscured as in the original reference?
  8. Did you want the scene to remain in complete darkness with no visible ambient light source, or did you prefer subtle ambient lighting as in the reference?
  9. Did you want the woman's lips to be slightly parted, or did you want them to remain closed as in the original reference?

--- Result ---
{
  "non_prompt_artifact": {
    "items": [
      {
        "artifact": "Background shows motion blur suggesting movement outside the car (reference has no such indication)",
        "desired": true,
        "reasoning": "The prompt describes a scene with minimal motion and a cinematic feel, which implies the car may be in motion. The motion blur in the background is a natural cinematic effect that suggests movement outside the car, enhancing the sense of motion and atmosphere without contradicting the prompt. It is an expected artistic choice to convey dynamism in a scene with minimal action."
      },
      {
        "artifact": "Car interior details slightly more defined with visible dashboard elements (reference is more minimal)",
        "desired": true,
        "reasoning": "The prompt emphasizes minimal motion and a cinematic style, but does not explicitly forbid or require the inclusion of interior details. The slight definition of dashboard elements in the output is a natural byproduct of the cinematic framing and lighting, enhancing the sense of realism without contradicting the prompt. It is an acceptable creative decision that enriches the scene without introducing error or unnecessary distraction."
      },
      {
        "artifact": "Lighting subtly shifts to highlight cheek and chin contours (reference maintains uniform shadowing)",
        "desired": true,
        "reasoning": "The subtle shift in lighting to highlight cheek and chin contours is a natural cinematic effect that enhances the three-dimensionality of the character’s face. Given the prompt’s emphasis on a smooth, cinematic style, this lighting adjustment is an expected artistic choice to add depth and mood without contradicting the scene’s intent."
      },
      {
        "artifact": "Choker pendant appears slightly more prominent in the output (reference is less emphasized)",
        "desired": true,
        "reasoning": "The choker pendant becoming slightly more prominent in the output is a natural result of lighting and camera angle adjustments in a cinematic scene. Since the prompt emphasizes style and minimal motion, subtle enhancements in visual emphasis, such as the choker’s prominence, are acceptable creative decisions that do not detract from the overall aesthetic or intent."
      },
      {
        "artifact": "Steering wheel partially visible in output, not in reference",
        "desired": true,
        "reasoning": "The steering wheel is naturally part of the car’s interior and is visible in the driver’s seat context. Since the prompt describes the woman sitting in the driver’s seat, the presence of the steering wheel is a logical and expected element of the scene, enhancing realism and context without being an error or unintended addition."
      },
      {
        "artifact": "Woman’s head turns slightly more than in reference (reference shows minimal movement)",
        "desired": true,
        "reasoning": "The prompt specifies minimal motion, but does not explicitly forbid any slight movement. A slight turn of the head is a natural, subtle motion that can occur in a cinematic scene without detracting from the overall mood or style. It is an acceptable creative decision within the context of the prompt."
      },
      {
        "artifact": "Car’s side mirror is more clearly visible in output (reference is obscured)",
        "desired": true,
        "reasoning": "The side mirror becoming more clearly visible is a natural result of the camera angle or lighting adjustment in the video, which enhances the cinematic quality without contradicting the prompt. It is an acceptable creative decision that improves visual clarity and depth."
      },
      {
        "artifact": "No visible ambient light source indicated in output (reference implies subtle ambient lighting)",
        "desired": true,
        "reasoning": "The absence of visible ambient light source is consistent with the dark, nighttime setting implied by the prompt. The cinematic, moody atmosphere achieved through minimal lighting is a natural artistic choice and aligns with the desired aesthetic, making it a desired artifact rather than an error."
      },
      {
        "artifact": "Woman’s lips are slightly parted in output (reference shows closed lips)",
        "desired": true,
        "reasoning": "The slight parting of the lips in the output is a natural, subtle expression that can occur in animated characters during moments of contemplation or readiness. It adds a touch of realism and emotional nuance without contradicting the prompt, which emphasizes style and minimal motion. This is an acceptable creative decision within the context of cinematic animation."
      }
    ]
  },
  "questions": [
    "Did you want the background to show motion blur suggesting movement outside the car, or did you want it to remain static as in the original reference?",
    "Did you want the car interior details to be slightly more defined with visible dashboard elements, or did you want them to remain as minimal as in the original reference?",
    "Did you want the lighting to subtly shift to highlight cheek and chin contours, or did you want it to remain uniformly shadowed as in the original reference?",
    "Did you want the choker pendant to appear more prominent, or did you want it to remain less emphasized as in the original reference?",
    "Did you want the steering wheel to be partially visible in the output, or did you want it to be absent as in the original reference?",
    "Did you want the woman’s head to turn slightly more than in the reference, or did you want it to remain minimal as in the original?",
    "Did you want the car’s side mirror to be more clearly visible, or did you want it to remain obscured as in the original reference?",
    "Did you want the scene to remain in complete darkness with no visible ambient light source, or did you prefer subtle ambient lighting as in the reference?",
    "Did you want the woman’s lips to be slightly parted, or did you want them to remain closed as in the original reference?"
  ]
}
```

</details>
