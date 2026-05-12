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
  - [Reference Coherence Check](#reference-coherence-check---ref-coherence)
  - [Prompt Adherence](#prompt-adherence---prompt-adherence)
- [Chat](#chat)

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


<img src="input/room.png" width="220" /> https://renderboard-test.s3.us-east-005.backblazeb2.com/videos/asset-ee0e77cc-d735-4d35-bcbe-ef89eaa23789



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

`scripts/run_gen_eval.py` — VLM evaluation of a generated output against reference inputs. Flags: `--ref-coherence`, `--prompt-adherence`, `--non-prompt-artifact`, `--question`, `--all` (default), `--debug`.

**Batch testing (future)** — `scripts/run_batch_gen_eval.py` batch-runs the eval against Jadu's past QC results for both image and video. `--vs-jadu-eval` puts Jadu's existing QC score side by side with the VLM scores in the output JSON, for direct comparison between the two eval systems.

CLI field limit select first few entry form qc_results for testing.

```bash
python scripts/run_batch_gen_eval.py \
  --input input/jadu_qc_results/qc_results.json \
  --limit 10 \
  --vs-jadu-eval

python scripts/run_batch_gen_eval.py \
  --input input/jadu_qc_results/qc_results_video.json \
  --limit 5 \
  --vs-jadu-eval
```

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
the following user prompt: {user_prompt}, and ({media_label} N+1), the generated
{media_label}, being the output result. Again, {media_label} N+1 is the output
being evaluated.

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
- Skip fine-grained detail (textures, minor lighting variation) unless they represent
  a clear departure from what was prompted or referenced.
- Return fewer than 10 items. If there aren't any unprompted artifacts, you don't
  have to return anything.

Pay close attention to:
- Character movements, gestures, head turns, and body language not described in the prompt
- Changes in gaze direction or character interaction
- Background motion or animation not described in the prompt

Respond with a bullet point list only. Each item starts with '- '.
Ensure your output contains only bullet point items — no preamble, no summary, no trailing text.
Refer to the examples below for format:

User Prompt: Turn the person in the first reference image into a cartoon character
Reference: woman with blonde hair, blue eyes, blue shirt, standing against white background
Output Description: A cartoon-style illustration of a young woman with blonde hair
and blue eyes wearing a blue shirt. She is smiling slightly and standing in front
of a pale yellow background with a faint drop shadow behind her figure.
Response:
- Background changed from white to pale yellow
- Drop shadow added behind the figure
- Slight smile (reference expression was neutral)

User Prompt: Put the person in image 1 on the sofa in the room shown in image 3,
and the person in image 2 standing beside the sofa.
Reference: doctor in white lab coat; girl with curly black hair; lab room with green sofa and cluttered table
Output Description: A composite scene showing a cartoon male doctor in a white lab
coat seated on a green sofa in a realistic lab setting. A cartoon girl with long
black curly hair stands to the right of the sofa. The lab table in the background
is empty. A ceiling light casts a warm tone over the scene. The doctor has his arms
resting on his knees and is looking slightly downward.
Response:
- Lab table is empty (reference showed it cluttered)
- Warm color tone cast by ceiling light (not in reference or prompt)
```

---

**`unprompted_artifact_list_eval()` — desired or undesired?**

One VLM call per item.

```
You are evaluating an {task_desc} with input references (image 1 to image N),
the following user prompt: {user_prompt}, and ({media_label} N+1), the generated
{media_label}, being the output result. Again, {media_label} N+1 is the output
being evaluated.

The following element was observed in the output but was not explicitly mentioned
in the user prompt:
{item}

Evaluate whether this element is a desired artifact (True) or an undesired artifact
(False). A desired artifact (True) is a natural byproduct of the generation, an
expected addition, or an acceptable creative decision given the prompt and context.
An undesired artifact (False) is a real error, anomaly, or unintended addition that
detracts from the output quality.

Ensure the format 'Response: True or False' and 'Reasoning: str'. Do not include an
'Artifact:' line. Refer to the examples below:

User Prompt: The woman in the car talking to herself
Item: Faint shadow beneath the car
Response: True
Reasoning: A ground shadow under a vehicle is a natural lighting byproduct in realistic
scenes. It does not conflict with the prompt or references.

User Prompt: The woman in the car talking to herself
Item: Car gliding down the street
Response: False
Reasoning: The prompt focuses solely on the woman talking; no vehicle movement was
requested. The car moving is an unintended addition to the scene.

User Prompt: Turn the person in the reference image into a cartoon character
Item: Background changed from white to blue gradient
Response: False
Reasoning: The prompt requested a style conversion only. The background color and
gradient were not asked for and represent an unintended modification.

User Prompt: Turn the person in the reference image into a cartoon character
Item: Character shown half-body with arms raised; reference showed full body with hands in pockets
Response: False
Reasoning: The reference shows a full-body standing pose with hands in pockets. The
output drastically changes both the framing and the pose without any instruction to do
so. This is not a natural byproduct of a style conversion.

User Prompt: Put the doctor on the sofa in the room shown in image 2
Item: Doctor's arms resting at sides rather than raised as in reference
Response: True
Reasoning: The reference shows the doctor in a T-pose with arms raised. When placed
in a seated position as prompted, arms lowering and resting is a natural consequence
of the posture change. This is an expected adaptation, not an error.
```

---

**`format_unprompted_as_questions()` — "Did you want...?"**

One VLM call per item.

```
You are evaluating an {task_desc} with input references (image 1 to image N),
the following user prompt: {user_prompt}, and ({media_label} N+1), the generated
{media_label}, being the output result. Again, {media_label} N+1 is the output
being evaluated.

The following element appeared in the output but was not explicitly mentioned in
the user prompt:
{item}

Rewrite this element as a single, concise 'Did you want...' question addressed to the
user. The question should clarify whether the element was intentional or whether the
user would have preferred it to stay as it was in the original reference, or be done
some other way. Ensure your output is a single question sentence only — no preamble,
no reasoning, nothing else.

Refer to examples below for format:

User Prompt: Turn the person in the reference image into a cartoon character
Item: Background switched from white to yellow
Question: Did you want the background to be switched to yellow, or did you want it to
stay the same as in the original reference?

User Prompt: The woman in the car talking to herself
Item: Car gliding down the street
Question: Did you want the car to be moving, or did you want it to remain stationary?

User Prompt: Turn the person in the reference image into a cartoon character
Item: Character shown half-body with arms raised; reference showed full body with hands in pockets
Question: Did you want the character to be cropped to half-body with arms raised, or did
you want the full-body standing pose from the reference to be preserved?
```

</details>

#### Demo

**Inputs**

<img src="https://renderboard-test.s3.us-east-005.backblazeb2.com/images/base64-7fbd52ae-62cd-49f9-bf75-65588a7a8120" width="220" />

[Generated video](https://renderboard-test.s3.us-east-005.backblazeb2.com/videos/asset-39131511-fb32-4704-8e9a-30968dca4539)

**Command**

```bash
python scripts/run_gen_eval.py \
  --refs https://renderboard-test.s3.us-east-005.backblazeb2.com/images/base64-7fbd52ae-62cd-49f9-bf75-65588a7a8120 \
  --gen-output https://renderboard-test.s3.us-east-005.backblazeb2.com/videos/asset-39131511-fb32-4704-8e9a-30968dca4539 \
  --prompt "A stylish woman with a sleek bob haircut and dark sunglasses sits in the driver's seat of a car at night. She wears a sharp black suit and a ruby choker. Minimal motion, smooth and cinematic." \
  --non-prompt-artifact --debug --question
```

**Output**

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

---

#### Demo 2

**Inputs**

<img src="https://renderboard-test.s3.us-east-005.backblazeb2.com/images/asset-21484c98-ec53-4aae-b714-3d2fdaec9dd9" width="220" />

[Generated video](https://renderboard-test.s3.us-east-005.backblazeb2.com/videos/asset-f47fb629-b791-4b82-b753-54e871d4ec2b)

**Command**

```bash
python scripts/run_gen_eval.py \
  --refs https://renderboard-test.s3.us-east-005.backblazeb2.com/images/asset-21484c98-ec53-4aae-b714-3d2fdaec9dd9 \
  --gen-output https://renderboard-test.s3.us-east-005.backblazeb2.com/videos/asset-f47fb629-b791-4b82-b753-54e871d4ec2b \
  --prompt "Cuddles and Koyal are relaxed. Both gaze out over the balcony, sitting closely but comfortably. Camera Angle: WIDE_SHOT" \
  --non-prompt-artifact --question
```

**Output**

**Unprompted artifacts (5)**

1. Puppy turns its head to face the crow
2. Crow opens its beak as if speaking
3. Crow turns its head slightly to the left
4. Puppy’s eyes widen in reaction to the crow
5. Crow’s feet shift slightly on the railing

**Questions (5)**

1. Did you want the puppy to turn its head to face the crow, or did you want it to remain facing away as in the original reference?
2. Did you want the crow to open its beak as if speaking, or did you want it to remain silent as in the original reference?
3. Did you want the crow to turn its head slightly to the left, or did you want it to remain facing forward as in the original reference?
4. Did you want the puppy’s eyes to widen in reaction to the crow, or did you want it to remain as it was in the original reference?
5. Did you want the crow’s feet to shift slightly on the railing, or did you want them to remain still as in the original reference?

<details>
<summary>Full run log (click to expand)</summary>

```text
(.venv) root@63ae7a98371f:~/jadu_image_video_ai_demo# python scripts/run_gen_eval.py   --refs https://renderboard-test.s3.us-east-005.backblazeb2.com/images/asset-21484c98-ec53-4aae-b714-3d2fdaec9dd9   --gen-output https://renderboard-test.s3.us-east-005.backblazeb2.com/videos/asset-f47fb629-b791-4b82-b753-54e871d4ec2b   --prompt "Cuddles and Koyal are relaxed. Both gaze out over the balcony, sitting closely but comfortably. Camera Angle: WIDE_SHOT"   --non-prompt-artifact --question
Loading model (this may take a moment)...
2026-05-12 09:55:58,490 INFO qwen_vl - Loading Qwen3-VL processor: models/hf/Qwen__Qwen3-VL-4B-Instruct
2026-05-12 09:55:59,170 INFO qwen_vl - Loading Qwen3-VL model: models/hf/Qwen__Qwen3-VL-4B-Instruct (device=cuda:0, dtype=torch.bfloat16)
/root/jadu_image_video_ai_demo/.venv/lib/python3.11/site-packages/transformers/models/auto/modeling_auto.py:2284: FutureWarning: The class `AutoModelForVision2Seq` is deprecated and will be removed in v5.0. Please use `AutoModelForImageTextToText` instead.
  warnings.warn(
`torch_dtype` is deprecated! Use `dtype` instead!
Loading checkpoint shards: 100%|███████████████████████████████████████████████████████████████████████| 2/2 [00:00<00:00, 22.67it/s]
2026-05-12 09:56:01,232 INFO qwen_vl - Qwen3-VL Transformers model is ready on cuda:0.

Listing unprompted elements...
2026-05-12 09:56:02,968 INFO qwen_vl - Built Qwen3 messages with 0 image(s) and 1 video.
qwen-vl-utils using torchvision to read video.
2026-05-12 09:56:10,358 INFO qwen_vl_utils.vision_process - torchvision:  video_path=’https://renderboard-test.s3.us-east-005.backblazeb2.com/videos/asset-f47fb629-b791-4b82-b753-54e871d4ec2b’, total_frames=121, video_fps=24.0, time=7.370s
Qwen3VL requires frame timestamps to construct prompts, but the `fps` of the input video could not be inferred. Probably `video_metadata` was missing from inputs and you passed pre-sampled frames. Defaulting to `fps=24`. Please provide `video_metadata` for more accurate results.
2026-05-12 09:56:12,196 INFO qwen_vl - Starting Qwen3-VL inference on cuda:0.
The following generation flags are not valid and may be ignored: [‘temperature’, ‘top_p’, ‘top_k’]. Set `TRANSFORMERS_VERBOSITY=info` for more details.
2026-05-12 09:56:27,396 INFO qwen_vl - Qwen3-VL inference completed.
2026-05-12 09:56:31,456 INFO qwen_vl - Built Qwen3 messages with 1 image(s) and 1 video.
2026-05-12 09:56:41,238 INFO qwen_vl_utils.vision_process - torchvision:  video_path=’https://renderboard-test.s3.us-east-005.backblazeb2.com/videos/asset-f47fb629-b791-4b82-b753-54e871d4ec2b’, total_frames=121, video_fps=24.0, time=6.818s
2026-05-12 09:56:43,930 INFO qwen_vl - Starting Qwen3-VL inference on cuda:0.
2026-05-12 09:56:46,414 INFO qwen_vl - Qwen3-VL inference completed.
[list_unprompted] 5 item(s): [‘Puppy turns its head to face the crow’, ‘Crow opens its beak as if speaking’, ‘Crow turns its head slightly to the left’, ‘Puppy’s eyes widen in reaction to the crow’, ‘Crow’s feet shift slightly on the railing’]
Found 5 unprompted element(s):
  1. Puppy turns its head to face the crow
  2. Crow opens its beak as if speaking
  3. Crow turns its head slightly to the left
  4. Puppy’s eyes widen in reaction to the crow
  5. Crow’s feet shift slightly on the railing
Evaluating...
2026-05-12 09:56:49,366 INFO qwen_vl - Built Qwen3 messages with 1 image(s) and 1 video.
2026-05-12 09:57:02,692 INFO qwen_vl_utils.vision_process - torchvision:  video_path=’https://renderboard-test.s3.us-east-005.backblazeb2.com/videos/asset-f47fb629-b791-4b82-b753-54e871d4ec2b’, total_frames=121, video_fps=24.0, time=10.606s
2026-05-12 09:57:05,281 INFO qwen_vl - Starting Qwen3-VL inference on cuda:0.
2026-05-12 09:57:09,227 INFO qwen_vl - Qwen3-VL inference completed.
2026-05-12 09:57:11,593 INFO qwen_vl - Built Qwen3 messages with 1 image(s) and 1 video.
2026-05-12 09:57:31,224 INFO qwen_vl_utils.vision_process - torchvision:  video_path=’https://renderboard-test.s3.us-east-005.backblazeb2.com/videos/asset-f47fb629-b791-4b82-b753-54e871d4ec2b’, total_frames=121, video_fps=24.0, time=17.286s
2026-05-12 09:57:33,600 INFO qwen_vl - Starting Qwen3-VL inference on cuda:0.
2026-05-12 09:57:36,838 INFO qwen_vl - Qwen3-VL inference completed.
2026-05-12 09:57:39,349 INFO qwen_vl - Built Qwen3 messages with 1 image(s) and 1 video.
2026-05-12 09:57:53,238 INFO qwen_vl_utils.vision_process - torchvision:  video_path=’https://renderboard-test.s3.us-east-005.backblazeb2.com/videos/asset-f47fb629-b791-4b82-b753-54e871d4ec2b’, total_frames=121, video_fps=24.0, time=7.211s
2026-05-12 09:57:55,895 INFO qwen_vl - Starting Qwen3-VL inference on cuda:0.
2026-05-12 09:57:59,347 INFO qwen_vl - Qwen3-VL inference completed.
2026-05-12 09:58:01,467 INFO qwen_vl - Built Qwen3 messages with 1 image(s) and 1 video.
2026-05-12 09:58:09,538 INFO qwen_vl_utils.vision_process - torchvision:  video_path=’https://renderboard-test.s3.us-east-005.backblazeb2.com/videos/asset-f47fb629-b791-4b82-b753-54e871d4ec2b’, total_frames=121, video_fps=24.0, time=5.261s
2026-05-12 09:58:12,282 INFO qwen_vl - Starting Qwen3-VL inference on cuda:0.
2026-05-12 09:58:15,781 INFO qwen_vl - Qwen3-VL inference completed.
2026-05-12 09:58:20,384 INFO qwen_vl - Built Qwen3 messages with 1 image(s) and 1 video.
2026-05-12 09:58:32,990 INFO qwen_vl_utils.vision_process - torchvision:  video_path=’https://renderboard-test.s3.us-east-005.backblazeb2.com/videos/asset-f47fb629-b791-4b82-b753-54e871d4ec2b’, total_frames=121, video_fps=24.0, time=10.306s
2026-05-12 09:58:35,496 INFO qwen_vl - Starting Qwen3-VL inference on cuda:0.
2026-05-12 09:58:38,623 INFO qwen_vl - Qwen3-VL inference completed.
  [desired] Puppy turns its head to face the crow — The prompt describes the characters as "relaxed" and "gazing out over the balcony," which implies they are engaged in a quiet, contemplative moment. The puppy turning its head to face the crow is a natural, subtle interaction that enhances the sense of companionship and relaxation, fitting the mood of the scene. It is not an error but a plausible, contextually appropriate behavior.
  [desired] Crow opens its beak as if speaking — The prompt describes Cuddles and Koyal as relaxed and gazing out over the balcony. The crow opening its beak as if speaking is a natural, subtle expression of interaction or communication that fits the relaxed, contemplative mood of the scene. It enhances the narrative without contradicting the prompt, making it a creative and acceptable addition.
  [desired] Crow turns its head slightly to the left — The prompt describes the characters as "relaxed" and "gazing out over the balcony," which implies a calm, natural posture. The crow turning its head slightly to the left is a subtle, natural movement that fits the relaxed, observational context. It does not contradict the prompt and enhances the sense of realism or animation, making it a desired artifact.
  [desired] Puppy’s eyes widen in reaction to the crow — The prompt describes the characters as "relaxed" and "gazing out," which implies a calm, observational moment. The puppy’s eyes widening in reaction to the crow is a natural, subtle expression of surprise or curiosity that fits the context of a relaxed interaction. It enhances the emotional nuance of the scene without contradicting the prompt, making it a desired artistic addition.
  [desired] Crow’s feet shift slightly on the railing — The crow’s feet shifting slightly on the railing is a subtle, natural movement that could occur in a relaxed, static scene. It adds realism and liveliness without contradicting the prompt, which describes the characters as "relaxed" and "gazing out." This is an acceptable creative decision that enhances the scene’s believability.

Listing unprompted elements...
2026-05-12 09:58:39,507 INFO qwen_vl - Built Qwen3 messages with 0 image(s) and 1 video.
2026-05-12 09:58:56,286 INFO qwen_vl_utils.vision_process - torchvision:  video_path=’https://renderboard-test.s3.us-east-005.backblazeb2.com/videos/asset-f47fb629-b791-4b82-b753-54e871d4ec2b’, total_frames=121, video_fps=24.0, time=16.778s
2026-05-12 09:58:57,992 INFO qwen_vl - Starting Qwen3-VL inference on cuda:0.
2026-05-12 09:59:11,260 INFO qwen_vl - Qwen3-VL inference completed.
2026-05-12 09:59:13,345 INFO qwen_vl - Built Qwen3 messages with 1 image(s) and 1 video.
2026-05-12 09:59:26,591 INFO qwen_vl_utils.vision_process - torchvision:  video_path=’https://renderboard-test.s3.us-east-005.backblazeb2.com/videos/asset-f47fb629-b791-4b82-b753-54e871d4ec2b’, total_frames=121, video_fps=24.0, time=10.956s
2026-05-12 09:59:29,094 INFO qwen_vl - Starting Qwen3-VL inference on cuda:0.
2026-05-12 09:59:31,477 INFO qwen_vl - Qwen3-VL inference completed.
[list_unprompted] 5 item(s): [‘Puppy turns its head to face the crow’, ‘Crow opens its beak as if speaking’, ‘Crow turns its head slightly to the left’, ‘Puppy’s eyes widen in reaction to the crow’, ‘Crow’s feet shift slightly on the railing’]
Found 5 unprompted element(s):
  1. Puppy turns its head to face the crow
  2. Crow opens its beak as if speaking
  3. Crow turns its head slightly to the left
  4. Puppy’s eyes widen in reaction to the crow
  5. Crow’s feet shift slightly on the railing
Generating questions...
2026-05-12 09:59:37,186 INFO qwen_vl - Built Qwen3 messages with 1 image(s) and 1 video.
2026-05-12 09:59:53,866 INFO qwen_vl_utils.vision_process - torchvision:  video_path=’https://renderboard-test.s3.us-east-005.backblazeb2.com/videos/asset-f47fb629-b791-4b82-b753-54e871d4ec2b’, total_frames=121, video_fps=24.0, time=10.407s
2026-05-12 09:59:56,405 INFO qwen_vl - Starting Qwen3-VL inference on cuda:0.
2026-05-12 09:59:57,944 INFO qwen_vl - Qwen3-VL inference completed.
2026-05-12 09:59:59,971 INFO qwen_vl - Built Qwen3 messages with 1 image(s) and 1 video.
2026-05-12 10:00:08,434 INFO qwen_vl_utils.vision_process - torchvision:  video_path=’https://renderboard-test.s3.us-east-005.backblazeb2.com/videos/asset-f47fb629-b791-4b82-b753-54e871d4ec2b’, total_frames=121, video_fps=24.0, time=6.478s
2026-05-12 10:00:11,278 INFO qwen_vl - Starting Qwen3-VL inference on cuda:0.
2026-05-12 10:00:12,761 INFO qwen_vl - Qwen3-VL inference completed.
2026-05-12 10:00:14,946 INFO qwen_vl - Built Qwen3 messages with 1 image(s) and 1 video.
2026-05-12 10:00:26,482 INFO qwen_vl_utils.vision_process - torchvision:  video_path=’https://renderboard-test.s3.us-east-005.backblazeb2.com/videos/asset-f47fb629-b791-4b82-b753-54e871d4ec2b’, total_frames=121, video_fps=24.0, time=9.429s
2026-05-12 10:00:28,891 INFO qwen_vl - Starting Qwen3-VL inference on cuda:0.
2026-05-12 10:00:30,432 INFO qwen_vl - Qwen3-VL inference completed.
2026-05-12 10:00:32,893 INFO qwen_vl - Built Qwen3 messages with 1 image(s) and 1 video.
2026-05-12 10:00:43,838 INFO qwen_vl_utils.vision_process - torchvision:  video_path=’https://renderboard-test.s3.us-east-005.backblazeb2.com/videos/asset-f47fb629-b791-4b82-b753-54e871d4ec2b’, total_frames=121, video_fps=24.0, time=9.199s
2026-05-12 10:00:46,487 INFO qwen_vl - Starting Qwen3-VL inference on cuda:0.
2026-05-12 10:00:48,092 INFO qwen_vl - Qwen3-VL inference completed.
2026-05-12 10:00:49,361 INFO qwen_vl - Built Qwen3 messages with 1 image(s) and 1 video.
2026-05-12 10:00:55,170 INFO qwen_vl_utils.vision_process - torchvision:  video_path=’https://renderboard-test.s3.us-east-005.backblazeb2.com/videos/asset-f47fb629-b791-4b82-b753-54e871d4ec2b’, total_frames=121, video_fps=24.0, time=4.424s
2026-05-12 10:00:57,594 INFO qwen_vl - Starting Qwen3-VL inference on cuda:0.
2026-05-12 10:00:59,111 INFO qwen_vl - Qwen3-VL inference completed.
  1. Did you want the puppy to turn its head to face the crow, or did you want it to remain facing away as in the original reference?
  2. Did you want the crow to open its beak as if speaking, or did you want it to remain silent as in the original reference?
  3. Did you want the crow to turn its head slightly to the left, or did you want it to remain facing forward as in the original reference?
  4. Did you want the puppy’s eyes to widen in reaction to the crow, or did you want it to remain as it was in the original reference?
  5. Did you want the crow’s feet to shift slightly on the railing, or did you want them to remain still as in the original reference?

--- Result ---
{
  "non_prompt_artifact": {
    "items": [
      {
        "artifact": "Puppy turns its head to face the crow",
        "desired": true,
        "reasoning": "The prompt describes the characters as \"relaxed\" and \"gazing out over the balcony,\" which implies they are engaged in a quiet, contemplative moment. The puppy turning its head to face the crow is a natural, subtle interaction that enhances the sense of companionship and relaxation, fitting the mood of the scene. It is not an error but a plausible, contextually appropriate behavior."
      },
      {
        "artifact": "Crow opens its beak as if speaking",
        "desired": true,
        "reasoning": "The prompt describes Cuddles and Koyal as relaxed and gazing out over the balcony. The crow opening its beak as if speaking is a natural, subtle expression of interaction or communication that fits the relaxed, contemplative mood of the scene. It enhances the narrative without contradicting the prompt, making it a creative and acceptable addition."
      },
      {
        "artifact": "Crow turns its head slightly to the left",
        "desired": true,
        "reasoning": "The prompt describes the characters as \"relaxed\" and \"gazing out over the balcony,\" which implies a calm, natural posture. The crow turning its head slightly to the left is a subtle, natural movement that fits the relaxed, observational context. It does not contradict the prompt and enhances the sense of realism or animation, making it a desired artifact."
      },
      {
        "artifact": "Puppy’s eyes widen in reaction to the crow",
        "desired": true,
        "reasoning": "The prompt describes the characters as \"relaxed\" and \"gazing out,\" which implies a calm, observational moment. The puppy’s eyes widening in reaction to the crow is a natural, subtle expression of surprise or curiosity that fits the context of a relaxed interaction. It enhances the emotional nuance of the scene without contradicting the prompt, making it a desired artistic addition."
      },
      {
        "artifact": "Crow’s feet shift slightly on the railing",
        "desired": true,
        "reasoning": "The crow’s feet shifting slightly on the railing is a subtle, natural movement that could occur in a relaxed, static scene. It adds realism and liveliness without contradicting the prompt, which describes the characters as \"relaxed\" and \"gazing out.\" This is an acceptable creative decision that enhances the scene’s believability."
      }
    ]
  },
  "questions": [
    "Did you want the puppy to turn its head to face the crow, or did you want it to remain facing away as in the original reference?",
    "Did you want the crow to open its beak as if speaking, or did you want it to remain silent as in the original reference?",
    "Did you want the crow to turn its head slightly to the left, or did you want it to remain facing forward as in the original reference?",
    "Did you want the puppy’s eyes to widen in reaction to the crow, or did you want it to remain as it was in the original reference?",
    "Did you want the crow’s feet to shift slightly on the railing, or did you want them to remain still as in the original reference?"
  ]
}
```

</details>

---

### Reference Coherence Check (`--ref-coherence`)

Two-step evaluation that first determines whether consistency between the reference(s) and output should be expected at all, then scores it if so. The check reasoning from step 1 is passed into step 2 to ground the scoring.

**Pipeline**

```
Inputs: ref image(s)  ·  user prompt  ·  generated output
                              │
                              ▼
               ref_comf_required_check()
               ── should consistency be evaluated?
                              │
               ┌──────────────┴──────────────┐
               ▼                             ▼
         required: Yes                 required: No
               │                        skip scoring
               ▼
     ref_consistency_eval()
     ── grounded by required_check reasoning
               │
         score 0–5 + reasoning
```

<details>
<summary>Prompts (click to expand)</summary>

**`ref_comf_required_check()` — is consistency evaluation needed?**

```
You are evaluating an {task_desc} with input references (image 1 to image N),
the following user prompt: {user_prompt}, and ({media_label} N+1), the generated
{media_label}, being the output result. Again, {media_label} N+1 is the output
being evaluated.

Think about the task the user is trying to accomplish via the prompt and references.
In this {task_desc}, is this a task where people/scenes/items in the reference should
keep layout/appearance consistent and unchanged? If specific items in the reference
should appear the same in the output, Response: Yes. Else if the user is using the
reference vaguely as a stylistic or concept guide, without specific things needing to
look exactly the same as in the reference, then Response: No.

Note: even if the output is a video with motion, action, or style change, if the same
character or person from the reference appears in the output, their identity should still
be checked for consistency — face, distinguishing features, clothing, and overall
appearance. Motion and style transformation do not exempt a character from identity
consistency. Only respond No if the reference is used purely as a stylistic or thematic
guide with no specific characters or elements carried over into the output.

In addition to Yes/No response, return a Reasoning why, based on the user prompt,
references may/may not expect to be consistent in the output. If consistency is
expected, provide a brief description of what specific things from the reference are
expected to be consistent. Ensure the format ‘Response: Yes or No’ and ‘Reasoning: str’.
Refer to examples below:

User Prompt: Turn the person in the first reference image into a cartoon character
Image Ref (via description only): <girl with blonde hair, blue eyes, blue shirt>
Response: Yes
Reasoning: while the user doesn’t expect the person in the reference image to be kept
exactly the same, since the prompt demands changing of style, key traits, apperance,
pose, and layout of the original reference such as the girl’s blonde hair, blue eyes,
and blue shirt, should be kept the same.

User Prompt: Use this image as a style reference and output a city scene in the same style.
Image Ref (via description only): <80s Japanese city pop album cover with neon,
vibrantly-colored, sunset beach scene.>
Response: No
Reasoning: The user is using the reference image loosely for a style transfer task, so
no specific item, person, or layout from the reference needs to be preserved.

User Prompt: Put the person in image 1 on the sofa in the room shown in image 3, and
the person in image 2 standing beside the sofa.
Image Ref (via description only, in that order): <a cartoon character of an middle-aged
male doctor in a white lab coat>, <a cartoon character of a girl with long curly black
hair>, <a realistic image of a lab with table filled with equipments and a green sofa
against the right wall>
Response: Yes
Reasoning: This task ask for the cartoon characters in image 1 and 2 to be edited
directly into reference image 3, meaning that all visible aspect of the references
should be kept the same. The appearance of the girl, the doctor, the distinct stylistic
difference between the environment and characters, and the details of items on the table
in the lab should be kept consistent.
```

---

**`ref_consistency_eval()` — score consistency 0–5**

```
You are evaluating an {task_desc} with input image 1 to image N being the input
references used for the generation task. This is the user’s prompt: {user_prompt}.
({media_label} N+1), the generated {media_label}, is the output result from the
generation task. Again, {media_label} N+1 is the outputted result from the previous
generation task that you are evaluating against the reference(s) and the prompt.

In this image-editing/ref-to-video task, items in the reference should remain
consistent. Here is an analysis of what should be consistent by another evaluator:
{prior_analysis}

Based on what should be kept consistent, evaluate every aspect of the appearance,
layout, proportion, lighting/color, and other aspects between input reference(s) and
output img/video to give a score out of 5, 5/5 being perfect consistency across
elements; 4/5 being mild, unnoticeable inconsistencies; 3/5 being noticeable
inconsistencies present; 2/5 being many noticeable inconsistencies; 1/5 being output
is mostly inconsistent with the references; 0/5 is completely inconsistent.

Also return a ‘Reasoning’ for the evaluation. Ensure the format ‘Response: X/5’ and
‘Reasoning: str’. Refer to below for example format:

User Prompt: Turn the person in the first reference image into a cartoon character
Image Ref (via description only): <girl with blonde hair, blue eyes, blue shirt>
Output: <cartoon character, girl with blonde hair, slightly darker blue eyes, blue shirt>
Prior Evaluator Analysis: while the user doesn’t expect the person in the reference
image to be kept exactly the same, since the prompt demands changing of style, key
traits, apperance, pose, and layout of the original reference such as the girl’s blonde
hair, blue eyes, and blue shirt, should be kept the same.
Response: 4/5
Reasoning: In the acceptable realm of a style change, the character’s features are
mostly consistent, from clothing, age, hairstyle, color, and proportion. However, the
color of the eye seems to be slightly off, though not noticeably. So 4/5.

User Prompt: Put the person in image 1 on the sofa in the room shown in image 3, and
the person in image 2 standing beside the sofa.
Image Ref (via description only, in that order): <a cartoon character of an middle-aged
male doctor in a white lab coat with stethoscope>, <a cartoon character of a girl with
long curly black hair>, <a realistic image of a lab with table filled with equipments
and a green sofa against the right wall>
Output: <cartoon male doctor in white lab coat sitting on realistic couch, legs
outstretched on the green sofa, girl with long curly black hair standing besides it,
empty table in the lab.>
Prior Evaluator Analysis: This task ask for the cartoon characters in image 1 and 2 to
be edited directly into reference image 3, meaning that all visible aspect of the
references should be kept the same. The appearance of the girl, the doctor, the
distinct stylistic difference between the environment and characters, and the details
of items on the table in the lab should be kept consistent.
Response: 3/5
Reasoning: Items in the lab should be kept consistent, but the previously cluttered
table is now empty. There is a slight deformation with the doctor character because the
cartoon leg is longer in seating position than in the reference. Otherwise, the doctor’s
face and the girls’ whole appearance are consistent, and the stylistic differentiation
between backdrop and character is kept the same.
```

</details>

#### Demo

**Inputs**

<img src="https://renderboard-test.s3.us-east-005.backblazeb2.com/images/asset-21484c98-ec53-4aae-b714-3d2fdaec9dd9" width="220" />

**Output**
<img src="https://renderboard-test.s3.us-east-005.backblazeb2.com/images/asset-79d772f5-e2d7-4366-ba3a-0b9de9fb6aec" width="220" />



**Command**

```bash
python scripts/run_gen_eval.py \
  --refs https://renderboard-test.s3.us-east-005.backblazeb2.com/images/asset-21484c98-ec53-4aae-b714-3d2fdaec9dd9 \
  --gen-output https://renderboard-test.s3.us-east-005.backblazeb2.com/images/asset-79d772f5-e2d7-4366-ba3a-0b9de9fb6aec \
  --prompt "Cuddles and Koyal are relaxed. Both gaze out over the balcony, sitting closely but comfortably. Camera Angle: WIDE_SHOT" \
  --ref-coherence
```

**Output**

Consistency required: **True**

Reasoning: The user prompt specifies that Cuddles and Koyal are relaxed and sitting closely but comfortably on the balcony, with the camera in a WIDE_SHOT. The references show the characters in this exact setup — Cuddles (the dog) and Koyal (the crow) seated on the balcony railing, facing the cityscape under a full moon. The prompt does not request any stylistic change or reinterpretation; it demands the scene to be preserved as is, with the characters’ positions, expressions (as seen in the close-up), and the environment (city skyline, moon, stars) to remain consistent. Therefore, the layout, appearance, and relative positioning of all elements in the references must be maintained in the output video.

Consistency score: **1/5**

Reasoning: The output image is a close-up of the dog character with an exaggerated, mischievous expression, which is inconsistent with the reference where the dog is shown in a relaxed, neutral posture on the balcony with the crow. The prompt explicitly states that both characters are "relaxed" and the camera is in a "WIDE_SHOT," which is not preserved in the output. The output completely ignores the scene context, character positioning, and environment (cityscape, moon, balcony railing) from the reference, replacing it with a tight, emotionally charged close-up that contradicts the prompt’s requirements.

<details>
<summary>Full run log (click to expand)</summary>

```text
(.venv) root@63ae7a98371f:~/jadu_image_video_ai_demo# python scripts/run_gen_eval.py   --refs https://renderboard-test.s3.us-east-005.backblazeb2.com/images/asset-21484c98-ec53-4aae-b714-3d2fdaec9dd9            --gen-output https://renderboard-test.s3.us-east-005.backblazeb2.com/images/asset-79d772f5-e2d7-4366-ba3a-0b9de9fb6aec   --prompt "Cuddles and Koyal are relaxed. Both gaze out over the balcony, sitting closely but comfortably. Camera Angle: WIDE_SHOT"   --ref-coherence
Loading model (this may take a moment)...
2026-05-12 10:04:06,474 INFO qwen_vl - Loading Qwen3-VL processor: models/hf/Qwen__Qwen3-VL-4B-Instruct
2026-05-12 10:04:07,134 INFO qwen_vl - Loading Qwen3-VL model: models/hf/Qwen__Qwen3-VL-4B-Instruct (device=cuda:0, dtype=torch.bfloat16)
/root/jadu_image_video_ai_demo/.venv/lib/python3.11/site-packages/transformers/models/auto/modeling_auto.py:2284: FutureWarning: The class `AutoModelForVision2Seq` is deprecated and will be removed in v5.0. Please use `AutoModelForImageTextToText` instead.
  warnings.warn(
`torch_dtype` is deprecated! Use `dtype` instead!
Loading checkpoint shards: 100%|███████████████████████████████████████████████████████████████████████| 2/2 [00:00<00:00, 22.11it/s]
2026-05-12 10:04:09,217 INFO qwen_vl - Qwen3-VL Transformers model is ready on cuda:0.

Checking whether reference consistency evaluation is required...
2026-05-12 10:04:17,077 INFO qwen_vl - Built Qwen3 messages with 2 image(s).

2026-05-12 10:04:33,613 INFO qwen_vl_utils.

2026-05-12 10:04:36,416 INFO qwen_vl - Starting Qwen3-VL inference on cuda:0.
The following generation flags are not valid and may be ignored: [‘temperature’, ‘top_p’, ‘top_k’]. Set `TRANSFORMERS_VERBOSITY=info` for more details.
2026-05-12 10:04:42,720 INFO qwen_vl - Qwen3-VL inference completed.
Consistency required: True
Reasoning: The user prompt specifies that Cuddles and Koyal are relaxed and sitting closely but comfortably on the balcony, with the camera in a WIDE_SHOT. The references show the characters in this exact setup — Cuddles (the dog) and Koyal (the crow) seated on the balcony railing, facing the cityscape under a full moon. The prompt does not request any stylistic change or reinterpretation; it demands the scene to be preserved as is, with the characters’ positions, expressions (as seen in the close-up), and the environment (city skyline, moon, stars) to remain consistent. Therefore, the layout, appearance, and relative positioning of all elements in the references must be maintained in the output video.

Running reference consistency scoring...
2026-05-12 10:04:45,550 INFO qwen_vl - Built Qwen3 messages with 2 image(s).
2026-05-12 10:04:53,611 INFO qwen_vl_utils.vision_process - torchvision:  video_path=’https://renderboard-test.s3.us-east-005.backblazeb2.com/videos/asset-f47fb629-b791-4b82-b753-54e871d4ec2b’, total_frames=121, video_fps=24.0, time=5.461s
2026-05-12 10:04:56,392 INFO qwen_vl - Starting Qwen3-VL inference on cuda:0.
2026-05-12 10:05:02,716 INFO qwen_vl - Qwen3-VL inference completed.
Consistency score: 1/5
Reasoning: The output image (image 2) is a close-up of the dog character with an exaggerated, mischievous expression, which is inconsistent with the reference image (image 1) where the dog is shown in a relaxed, neutral posture on the balcony with the crow. The prompt explicitly states that both characters are "relaxed" and the camera is in a "WIDE_SHOT," which is not preserved in the output. The output image completely ignores the scene context, character positioning, and environment (cityscape, moon, balcony railing) from the reference, replacing it with a tight, emotionally charged close-up that contradicts the prompt’s requirements. The lighting, composition, and character interaction are all fundamentally altered, making it inconsistent in every major aspect.

--- Result ---
{
  "ref_consistency": {
    "required": true,
    "reasoning": "The output image (image 2) is a close-up of the dog character with an exaggerated, mischievous expression, which is inconsistent with the reference image (image 1) where the dog is shown in a relaxed, neutral posture on the balcony with the crow. The prompt explicitly states that both characters are \"relaxed\" and the camera is in a \"WIDE_SHOT,\" which is not preserved in the output. The output image completely ignores the scene context, character positioning, and environment (cityscape, moon, balcony railing) from the reference, replacing it with a tight, emotionally charged close-up that contradicts the prompt’s requirements. The lighting, composition, and character interaction are all fundamentally altered, making it inconsistent in every major aspect.",
    "score": 1
  }
}
```

</details>

---

#### Demo 2 — consistency not required

**Inputs**

<img src="https://renderboard-test.s3.us-east-005.backblazeb2.com/images/asset-a41f93e2-0728-4174-8b29-1da1cea72d92" width="220" />

[Generated video](https://renderboard-test.s3.us-east-005.backblazeb2.com/videos/asset-284f7a85-7a45-4c4c-b8e6-c2290fe37f24)

**Command**

```bash
python scripts/run_gen_eval.py \
  --refs https://renderboard-test.s3.us-east-005.backblazeb2.com/images/asset-a41f93e2-0728-4174-8b29-1da1cea72d92 \
  --gen-output https://renderboard-test.s3.us-east-005.backblazeb2.com/videos/asset-284f7a85-7a45-4c4c-b8e6-c2290fe37f24 \
  --prompt "Mohini pummels Vet with wild, flailing energy; both move in comic blur as onomatopoeic text appears with each blow. Camera Angle: INSERT_SHOT" \
  --all
```

**Output**

Consistency required: **False**

Reasoning: The user prompt describes a dynamic action sequence involving "Mohini pummeling Vet with wild, flailing energy," which implies motion, blur, and onomatopoeic text appearing with each blow — elements not present in the static reference image. The reference image is a split-panel comic-style illustration with static poses, so the output video must depict motion and action, not preserve the static layout or appearance. Therefore, the reference is used as a stylistic guide (comic art, bold text, exaggerated expressions) rather than a literal template for unchanged elements.

Reference consistency scoring not required — skipping.

<details>
<summary>Full run log (click to expand)</summary>

```text
(.venv) root@63ae7a98371f:~/jadu_image_video_ai_demo# python scripts/run_gen_eval.py \
  --refs https://renderboard-test.s3.us-east-005.backblazeb2.com/images/asset-a41f93e2-0728-4174-8b29-1da1cea72d92 \
  --gen-output https://renderboard-test.s3.us-east-005.backblazeb2.com/videos/asset-284f7a85-7a45-4c4c-b8e6-c2290fe37f24 \
  --prompt "Mohini pummels Vet with wild, flailing energy; both move in comic blur as onomatopoeic text appears with each blow. Camera Angle: INSERT_SHOT" \
  --all
Loading model (this may take a moment)...
2026-05-12 10:09:01,650 INFO qwen_vl - Loading Qwen3-VL processor: models/hf/Qwen__Qwen3-VL-4B-Instruct
2026-05-12 10:09:02,278 INFO qwen_vl - Loading Qwen3-VL model: models/hf/Qwen__Qwen3-VL-4B-Instruct (device=cuda:0, dtype=torch.bfloat16)
/root/jadu_image_video_ai_demo/.venv/lib/python3.11/site-packages/transformers/models/auto/modeling_auto.py:2284: FutureWarning: The class `AutoModelForVision2Seq` is deprecated and will be removed in v5.0. Please use `AutoModelForImageTextToText` instead.
  warnings.warn(
`torch_dtype` is deprecated! Use `dtype` instead!
Loading checkpoint shards: 100%|███████████████████████████████████████████████████████████████████████| 2/2 [00:00<00:00, 22.67it/s]
2026-05-12 10:09:04,156 INFO qwen_vl - Qwen3-VL Transformers model is ready on cuda:0.

Checking whether reference consistency evaluation is required...
2026-05-12 10:09:06,706 INFO qwen_vl - Built Qwen3 messages with 1 image(s) and 1 video.
qwen-vl-utils using torchvision to read video.
2026-05-12 10:09:22,939 INFO qwen_vl_utils.vision_process - torchvision:  video_path=’https://renderboard-test.s3.us-east-005.backblazeb2.com/videos/asset-284f7a85-7a45-4c4c-b8e6-c2290fe37f24’, total_frames=121, video_fps=24.0, time=14.819s
Qwen3VL requires frame timestamps to construct prompts, but the `fps` of the input video could not be inferred. Probably `video_metadata` was missing from inputs and you passed pre-sampled frames. Defaulting to `fps=24`. Please provide `video_metadata` for more accurate results.
2026-05-12 10:09:25,512 INFO qwen_vl - Starting Qwen3-VL inference on cuda:0.
The following generation flags are not valid and may be ignored: [‘temperature’, ‘top_p’, ‘top_k’]. Set `TRANSFORMERS_VERBOSITY=info` for more details.
2026-05-12 10:09:31,045 INFO qwen_vl - Qwen3-VL inference completed.
Consistency required: False
Reasoning: The user prompt describes a dynamic action sequence involving "Mohini pummeling Vet with wild, flailing energy," which implies motion, blur, and onomatopoeic text appearing with each blow — elements not present in the static reference image. The reference image is a split-panel comic-style illustration with static poses (a man’s angry face and boots hitting a carpet), so the output video must depict motion and action, not preserve the static layout or appearance. Therefore, the reference is used as a stylistic guide (comic art, bold text, exaggerated expressions) rather than a literal template for unchanged elements.
Reference consistency scoring not required — skipping.
```

</details>

---

### Prompt Adherence (`--prompt-adherence`)

Single-step eval that scores how well the generated output fulfills the user prompt (0–5). Always runs — no required-check gate. Considers every specific instruction, subject, action, placement, style, or constraint mentioned in the prompt.

**Pipeline**

```
Inputs: ref image(s)  ·  user prompt  ·  generated output
                              │
                              ▼
               prompt_adherence_eval()
                              │
                         score 0–5 + reasoning
```

<details>
<summary>Prompts (click to expand)</summary>

**`prompt_adherence_eval()` — score 0–5**

```
You are evaluating an {task_desc} out of 5 with input references
(image 1 to image N) and the following user prompt: {user_prompt}.
({media_label} N+1), the generated {media_label}, is the output result from the
generation task. Again, {media_label} N+1 is the output being evaluated.

Evaluate how well the output fulfills what the user prompt asked for out of 5.
Consider every specific instruction, subject, action, placement, style change,
or constraint mentioned in the prompt, and assess whether the output delivers
on each one.

Give a score out of 5: 5/5 means the output fully accomplishes every element
of the prompt; 4/5 means the output mostly fulfills the prompt with only minor
omissions or slight deviations; 3/5 means the output partially fulfills the
prompt with noticeable missing elements or incorrect execution; 2/5 means the
output only addresses a small part of what was asked; 1/5 means the output
barely addresses the prompt; 0/5 means the output completely ignores the prompt.

Also return a 'Reasoning' that identifies specifically what was and wasn't
accomplished. Ensure the format 'Response: int' and 'Reasoning: str'. Refer to
below for example format:

User Prompt: Turn the person in the first reference image into a cartoon character
Image Ref (via description only): <girl with blonde hair, blue eyes, blue shirt>
Output: <cartoon character, girl with blonde hair, slightly darker blue eyes, blue shirt>
Response: 5/5
Reasoning: The prompt asked for a style change to cartoon, which was fully executed.
The subject from the reference is present and identifiable. No additional instructions
were given that were missed.

User Prompt: Put the person in image 1 on the sofa in the room shown in image 3,
and the person in image 2 standing beside the sofa.
Image Ref (via description only, in that order): <a cartoon character of a middle-aged
male doctor in a white lab coat>, <a cartoon character of a girl with long curly black
hair>, <a realistic image of a lab with a green sofa against the right wall>
Output: <cartoon male doctor sitting on the green sofa, empty space beside the sofa,
lab backdrop present>
Response: 2/5
Reasoning: The prompt specified two subjects — the doctor placed on the sofa and the
girl standing beside it. The doctor's placement is correct, but the girl from image 2
is entirely absent from the output. Half of the core instruction was not executed.
```

</details>

#### Demo

**Inputs**

<img src="https://renderboard-test.s3.us-east-005.backblazeb2.com/images/base64-0c187082-bcd0-48b4-9fd6-9b8ca699b33a" width="220" />
<img src="https://renderboard-test.s3.us-east-005.backblazeb2.com/images/base64-6f9167f5-0d6e-4b2a-b02f-cebb165435a2" width="220" />

**Output image**

<img src="output/img-edit/ComfyUI_00002_.png" width="220" />

**Command**

```bash
python scripts/run_gen_eval.py \
  --refs $VET_IMG $ROOM_IMG \
  --gen-output output/img-edit/ComfyUI_00002_.png \
  --prompt "Put vet in room" \
  --prompt-adherence
```

**Output**

Score: **5/5**

Reasoning: The output image correctly places the doctor from image 1 into the room shown in image 2. The doctor is standing in the center of the room, positioned on the green rug, which is consistent with the spatial context of the room. The style of the doctor is preserved from image 1, and the room's elements (door, sofa, rug, framed picture) are all present and correctly rendered from image 2. The prompt did not specify any additional actions, placements, or style changes beyond placing the subject in the room, and the output fully accomplishes this.

<details>
<summary>Full run log (click to expand)</summary>

```text
(.venv) root@63ae7a98371f:~/jadu_image_video_ai_demo# python scripts/run_gen_eval.py   --refs $VET_IMG $ROOM_IMG   --gen-output output/img-edit/ComfyUI_00002_.png   --prompt "Put vet in room"   --prompt-adherence
Loading model (this may take a moment)...
2026-05-12 08:15:05,882 INFO qwen_vl - Loading Qwen3-VL processor: models/hf/Qwen__Qwen3-VL-4B-Instruct
2026-05-12 08:15:06,563 INFO qwen_vl - Loading Qwen3-VL model: models/hf/Qwen__Qwen3-VL-4B-Instruct (device=cuda:0, dtype=torch.bfloat16)
/root/jadu_image_video_ai_demo/.venv/lib/python3.11/site-packages/transformers/models/auto/modeling_auto.py:2284: FutureWarning: The class `AutoModelForVision2Seq` is deprecated and will be removed in v5.0. Please use `AutoModelForImageTextToText` instead.
  warnings.warn(
`torch_dtype` is deprecated! Use `dtype` instead!
Loading checkpoint shards: 100%|█████████████████████████████████████████████████████████████████████████████| 2/2 [00:00<00:00, 24.84it/s]
2026-05-12 08:15:08,533 INFO qwen_vl - Qwen3-VL Transformers model is ready on cuda:0.

Running prompt adherence evaluation...
2026-05-12 08:15:11,220 INFO qwen_vl - Built Qwen3 messages with 3 image(s).
2026-05-12 08:15:15,133 INFO qwen_vl - Starting Qwen3-VL inference on cuda:0.
The following generation flags are not valid and may be ignored: ['temperature', 'top_p', 'top_k']. Set `TRANSFORMERS_VERBOSITY=info` for more details.
2026-05-12 08:15:21,825 INFO qwen_vl - Qwen3-VL inference completed.
Prompt adherence score: 5/5
Reasoning: The user prompt was "Put vet in room." The output image (image 3) correctly places the doctor from image 1 into the room shown in image 2. The doctor is standing in the center of the room, positioned on the green rug, which is consistent with the spatial context of the room. The style of the doctor is preserved from image 1, and the room's elements (door, sofa, rug, framed picture) are all present and correctly rendered from image 2. The prompt did not specify any additional actions, placements, or style changes beyond placing the subject in the room, and the output fully accomplishes this. The doctor is the only subject present, which is consistent with the prompt's minimal instruction.

--- Result ---
{
  "prompt_adherence": {
    "score": 5,
    "reasoning": "The user prompt was \"Put vet in room.\" The output image (image 3) correctly places the doctor from image 1 into the room shown in image 2. The doctor is standing in the center of the room, positioned on the green rug, which is consistent with the spatial context of the room. The style of the doctor is preserved from image 1, and the room's elements (door, sofa, rug, framed picture) are all present and correctly rendered from image 2. The prompt did not specify any additional actions, placements, or style changes beyond placing the subject in the room, and the output fully accomplishes this. The doctor is the only subject present, which is consistent with the prompt's minimal instruction."
  }
}
```

</details>

---

## Chat

`scripts/run_qwen_chat.py` — multi-turn conversational assistant for directing the generative AI pipeline. Accepts image input via bracket syntax (`[path_or_url] message`), maintains turn history, and exports session transcripts. Slash commands: `/quit`, `/reset`, `/export`, `/help`.

Didn't have time to implement tool calling by swapping Qwen3-VL for Qwen3 (text-only); the system prompt instructs the model to respond with exact CLI commands for now.

<details>
<summary>System prompt (click to expand)</summary>

```
You are a directing assistant for a generative AI character pipeline.
You cannot run scripts yourself. When the user wants to do something, output the exact
command to run — short, direct, no tutorials. Local paths, $ENV_VAR references, and
URLs are all valid inputs; never question them or claim you cannot process them.
Keep responses conversational but brief — one line of chat at most, then the command.

## Scripts

Character sheet — multi-view sheet (front, sides, back, close-up) from one reference:
  python scripts/run_character_sheet_creation.py --image <path_or_url> --character-name <name>

Character edit — modify appearance, clothing, expression:
  python services/img_edit_service/img_edit.py --prompt "<instruction>" --images <path_or_url>

Scene creation — place character(s) into a scene or backdrop (1–3 images):
  python services/img_edit_service/img_edit.py --prompt "<instruction>" --images <ref1> <ref2>

Gen eval — evaluate a generated output against references:
  python scripts/run_gen_eval.py --refs <ref1> [ref2 ...] --gen-output <output> --prompt "<prompt>"
  Optional flags: --ref-coherence  --prompt-adherence  --non-prompt-artifact  --question

Shot angles — use the edit angle service:
  python services/edit_angle_service/edit_angle.py --image <path_or_url> --prompt "<angle instruction>"
  Available angles: 45° left, 45° right, 90° left, 90° right, 180° back, close-up

Session commands: /export  /reset  /quit

## Examples

User: [$VET_IMG] describe this character in detail
Assistant: Stocky middle-aged man in a white lab coat, stethoscope around his neck.
Short grey-brown hair, stern expression, slight stubble. Cartoon style with bold outlines.
Dark formal trousers and black shoes.

User: https://s3.../image.png I want him to wear a red jacket
Assistant: Here's the edit command:
  python services/img_edit_service/img_edit.py --prompt "Change the character in the image's jacket to red" --images https://s3.../image.png
  Want me to improve the prompt first for a more precise result?

User: yes improve it
Assistant: Try this: "Replace the character in the image's jacket with a bold red jacket,
matching the original fit and style. Keep all other clothing, features, and background unchanged."

User: yeah looks good now
Assistant: If you're happy with the character, I can give you the command to generate a full character sheet — front, sides, back, close-up.
  python scripts/run_character_sheet_creation.py --image $VET_IMG --character-name Vet

User: the shot looks too close
Assistant: Here are the available angles:
  - 45° left / right — slight turn
  - 90° left / right — full side profile
  - 180° back — rear view
  - close-up — tight on face
  Which do you want?
  python services/edit_angle_service/edit_angle.py --image <path_or_url> --prompt "Rotate the camera 90 degrees to the right. Show only 1 single character in the output image."

User: I want a side angle
Assistant: Left or right?
  python services/edit_angle_service/edit_angle.py --image <path_or_url> --prompt "Rotate the camera 90 degrees to the right. Show only 1 single character in the output image."

User: I want to do something with Koyal but I'm not sure what
Assistant: Want me to suggest a scene — a setting, mood, and action — or do you have a direction in mind?
  Either way it'd look like:
  python services/img_edit_service/img_edit.py --prompt "Place the character in the image on a rooftop at dusk, watching the city lights" --images $KOYAL_IMG

User: yeah give me a scene idea
Assistant: How about: Koyal stands at the edge of a rain-soaked alley, streetlight reflecting off the puddles, looking back over her shoulder.
  Want to run with that?
  python services/img_edit_service/img_edit.py --prompt "Place the character in the image at the edge of a rain-soaked alley, streetlight reflecting off puddles, looking back over her shoulder" --images $KOYAL_IMG

User: I want to put Vet somewhere dramatic
Assistant: A few options — rooftop standoff, collapsed building, dimly lit interrogation room. Which direction?
  Once you pick:
  python services/img_edit_service/img_edit.py --prompt "Place the character in the image on a rooftop at night, city below, coat whipping in the wind" --images $VET_IMG

User: evaluate this output https://s3.../video.mp4 against https://s3.../ref.png, prompt was "Mohini attacks Vet"
Assistant: python scripts/run_gen_eval.py --refs https://s3.../ref.png --gen-output https://s3.../video.mp4 --prompt "Mohini attacks Vet"
  Add --non-prompt-artifact --question to also surface unexpected elements as user-facing questions.
```

</details>

#### Test Plan

To be implemented: a VLM evaluator that scores conversations on helpfulness, percentage of tools utilised, and number of times the user had to clarify their request. Prompts for this evaluator haven't been written yet, but the transcript export function has been added to the chat — transcripts are automatically saved on exit and can be passed to the evaluator when ready.

#### Demo

**Input**

<img src="https://renderboard-test.s3.us-east-005.backblazeb2.com/images/base64-0c187082-bcd0-48b4-9fd6-9b8ca699b33a" width="220" />

**Command**

```bash
python scripts/run_qwen_chat.py
```

<details>
<summary>Session log (click to expand)</summary>

```text
root@63ae7a98371f:~/jadu_image_video_ai_demo# python scripts/run_qwen_chat.py
Loading model (this may take a moment)...
2026-05-12 11:14:47,032 INFO qwen_vl - Loading Qwen3-VL processor: models/hf/Qwen__Qwen3-VL-4B-Instruct
2026-05-12 11:14:47,667 INFO qwen_vl - Loading Qwen3-VL model: models/hf/Qwen__Qwen3-VL-4B-Instruct (device=cuda:0, dtype=torch.bfloat16)
/usr/local/lib/python3.11/dist-packages/transformers/models/auto/modeling_auto.py:2284: FutureWarning: The class `AutoModelForVision2Seq` is deprecated and will be removed in v5.0. Please use `AutoModelForImageTextToText` instead.
  warnings.warn(
`torch_dtype` is deprecated! Use `dtype` instead!
Loading checkpoint shards: 100%|█████████████████████████████████████████████████████████████████████████████| 2/2 [00:00<00:00, 24.52it/s]
2026-05-12 11:14:49,511 INFO qwen_vl - Qwen3-VL Transformers model is ready on cuda:0.
Chat ready. Type /help for commands, /quit to exit.

You: describe thsi cahracter for me https://renderboard-test.s3.us-east-005.backblazeb2.com/images/base64-0c187082-bcd0-48b4-9fd6-9b8ca699b33a
Hint: to pass an image use bracket syntax: [https://...] your message
2026-05-12 11:15:07,342 INFO qwen_vl - Starting Qwen3-VL chat inference (turn depth=2).
The following generation flags are not valid and may be ignored: ['temperature', 'top_p', 'top_k']. Set `TRANSFORMERS_VERBOSITY=info` for more details.
2026-05-12 11:15:09,496 INFO qwen_vl - Qwen3-VL chat inference completed.

A: Stocky middle-aged man in a white lab coat, stethoscope around his neck. Short grey-brown hair, stern expression, slight stubble. Cartoon style with bold outlines. Dark formal trousers and black shoes.

You: change hair to pink bowl cut
2026-05-12 11:15:21,028 INFO qwen_vl - Starting Qwen3-VL chat inference (turn depth=4).
2026-05-12 11:15:24,677 INFO qwen_vl - Qwen3-VL chat inference completed.

A: Here's the edit command:
  python services/img_edit_service/img_edit.py --prompt "Change the character's hair to a bold pink bowl cut, keeping the same style and length as the original" --images https://renderboard-test.s3.us-east-005.backblazeb2.com/images/base64-0c187082-bcd0-48b4-9fd6-9b8ca699b33a

You: improve prompt
2026-05-12 11:15:35,959 INFO qwen_vl - Starting Qwen3-VL chat inference (turn depth=6).
2026-05-12 11:15:37,705 INFO qwen_vl - Qwen3-VL chat inference completed.

A: Try this: "Replace the character's hair with a bold, vibrant pink bowl cut — sharp, clean edges, same length and style as the original, but in a striking pink hue. Keep all other clothing, facial features, and background unchanged."

You: I want to put him in a scene
2026-05-12 11:16:09,176 INFO qwen_vl - Starting Qwen3-VL chat inference (turn depth=8).
2026-05-12 11:16:14,911 INFO qwen_vl - Qwen3-VL chat inference completed.

A: Here's a scene idea:
"Place the character in a dimly lit, cluttered lab at night, surrounded by glowing monitors and scattered medical equipment. He's standing near a broken IV stand, looking tense and focused."

Want to run it?
  python services/img_edit_service/img_edit.py --prompt "Place the character in a dimly lit, cluttered lab at night, surrounded by glowing monitors and scattered medical equipment. He's standing near a broken IV stand, looking tense and focused." --images https://renderboard-test.s3.us-east-005.backblazeb2.com/images/base64-0c187082-bcd0-48b4-9fd6-9b8ca699b33a

You: rotate scene to a new angle
2026-05-12 11:16:28,747 INFO qwen_vl - Starting Qwen3-VL chat inference (turn depth=10).
2026-05-12 11:16:33,070 INFO qwen_vl - Qwen3-VL chat inference completed.

A: Here are the available angles for the scene:
  - 45° left / right — slight turn
  - 90° left / right — full side profile
  - 180° back — rear view
  - close-up — tight on face

Which angle do you want?
Example:
  python services/edit_angle_service/edit_angle.py --image <scene_image> --prompt "Rotate the camera 90 degrees to the right. Show only the character in the lab scene, emphasizing the cluttered monitors and broken IV stand."

You: change some of the details of the scene, make it bright and sunny
2026-05-12 11:17:28,917 INFO qwen_vl - Starting Qwen3-VL chat inference (turn depth=12).
2026-05-12 11:17:35,031 INFO qwen_vl - Qwen3-VL chat inference completed.

A: Here's the improved prompt:
"Place the character in a bright, sunny lab with large windows letting in natural light. The room is clean, modern, and organized — no clutter. He's standing near a whiteboard with diagrams, looking confident and calm."

Run it:
  python services/img_edit_service/img_edit.py --prompt "Place the character in a bright, sunny lab with large windows letting in natural light. The room is clean, modern, and organized — no clutter. He's standing near a whiteboard with diagrams, looking confident and calm." --images https://renderboard-test.s3.us-east-005.backblazeb2.com/images/base64-0c187082-bcd0-48b4-9fd6-9b8ca699b33a

You: let me finalize character design first
2026-05-12 11:18:06,968 INFO qwen_vl - Starting Qwen3-VL chat inference (turn depth=14).
2026-05-12 11:18:11,263 INFO qwen_vl - Qwen3-VL chat inference completed.

A: Got it — let's finalize the character design first.
Here's the command to generate a full character sheet (front, sides, back, close-up) from your image:
  python scripts/run_character_sheet_creation.py --image https://renderboard-test.s3.us-east-005.backblazeb2.com/images/base64-0c187082-bcd0-48b4-9fd6-9b8ca699b33a --character-name "Pink-Haired Lab Tech"

Once you're happy, we can move to scenes or angles.
```

</details>
