# Test Commands (Placeholder)

Run all commands from repo root: `/root/jadu_image_video_ai_demo`

For **`run_qwen_vl` with `--video`**: extensionless or odd-container inputs are downloaded/transcoded to MP4 via **ffmpeg** (install e.g. `apt install ffmpeg`; cache: `output/.qwen-vl-video-cache/`).

## 1) Reusable variables

```powershell
#Copy paste without $ in Linux terminal
$CAT_IMG="https://renderboard-test.s3.us-east-005.backblazeb2.com/images/base64-ea3a392a-23de-43c4-a915-83ebcc2a2725"
$VET_IMG="https://renderboard-test.s3.us-east-005.backblazeb2.com/images/base64-0c187082-bcd0-48b4-9fd6-9b8ca699b33a"
$GIRL_IMG="https://renderboard-test.s3.us-east-005.backblazeb2.com/images/base64-f38842e4-a365-479d-aa6c-c67e76ccc234"
$ROOM_IMG="https://renderboard-test.s3.us-east-005.backblazeb2.com/images/base64-6f9167f5-0d6e-4b2a-b02f-cebb165435a2"
$SCENE_VIDEO="https://renderboard-test.s3.us-east-005.backblazeb2.com/videos/asset-ee0e77cc-d735-4d35-bcbe-ef89eaa23789"
```


## 1) Character sheet creation (`run_character_sheet_creation`)

```powershell
# Use existing demo images as character refs (you can replace these with your own)

# Writes to storage/<character-name>/
# Default: does NOT run VLM full-body gating.
python scripts/run_character_sheet_creation.py --image $VET_IMG --character-name "Eli"
python scripts/run_character_sheet_creation.py --image $GIRL_IMG --character-name "Beth"

# Optional: strict full-body gate (uses VLM). If NOT full-body, prints a corrected full-body
# image path and exits non-zero.
python scripts/run_character_sheet_creation.py --image $VET_IMG --character-name "Eli" --full-body-check
python scripts/run_character_sheet_creation.py --image $GIRL_IMG --character-name "Beth" --full-body-check
```

## 2) Ref-guided generation (`run_ref_guided_gen`)

```powershell
# This requires `storage/Eli/Eli_character_sheet.png` and `storage/Beth/Beth_character_sheet.png` to exist
# (created by the commands in the section above).

# With backdrop/scene reference:
python scripts/run_ref_guided_gen.py --prompt "@Eli sitting on the couch, staring at @Beth's phone" --backdrop-img $ROOM_IMG --output-dir output/ref-guided-gen

# Without backdrop:
python scripts/run_ref_guided_gen.py --prompt "@Eli sitting on the couch, staring at @Beth's phone" --output-dir output/ref-guided-gen
```

## 3) run_qwen_vl (image-only, video-only, mixed)

vLLM context length is set by **`MAX_MODEL_LEN` in** [`code/qwen_vl.py`](../code/qwen_vl.py) (not a CLI flag). For a one-off override, construct `QwenVL(max_model_len=...)` in Python.

For **`--video`**, `qwen_vl_utils` needs **`decord`** (in `requirements.txt`) or **`av`** (PyAV) when `torchvision.io.read_video` is unavailable; **`ffmpeg`** is still required on `PATH` for extensionless-URL normalization (see top of this file).

```powershell
# image-only (1 image)
python scripts/run_qwen_vl.py --images $CAT_IMG --prompt "Describe this input with as much detail as possible, including subject, style, colors, lighting, composition, and notable fine details."

# image-only (2 images)
python scripts/run_qwen_vl.py --images $VET_IMG $GIRL_IMG --prompt "Describe both inputs with as much detail as possible, then compare them in terms of subject, style, color palette, and scene context."

# image-only (3 images)
python scripts/run_qwen_vl.py --images $CAT_IMG $GIRL_IMG $ROOM_IMG --prompt "Describe all inputs with as much detail as possible and explain relationships between subjects, environment, and likely narrative."

# video-only attempt
python scripts/run_qwen_vl.py --video $SCENE_VIDEO --prompt "Describe this video with as much detail as possible, including setting, objects, any visible people/animals, actions, camera behavior, and temporal changes."

# image + video combined attempt
python scripts/run_qwen_vl.py --images $ROOM_IMG --video $SCENE_VIDEO --prompt "Describe both the image and the video with as much detail as possible, then explain what visual details are consistent or different between them."

# image + video combined attempt (local files)
# NOTE: Requires `input/scene_video.mp4` to exist (downloaded separately) and `input/room.png` to exist.
python scripts/run_qwen_vl.py --images input/room.png --video input/scene_video.mp4 --prompt "Describe both the image and the video with as much detail as possible, then explain what visual details are consistent or different between them."
```

## 4) img_edit (1, 2, 3 image inputs)

```powershell
# 1 image input (identity-preserving enhancement)
python services/img_edit_service/img_edit.py --images $CAT_IMG --prompt "Enhance detail and lighting while preserving the cat's identity and pose." --output-dir output/img-edit

# 2 image inputs (style/compositional blend)
python services/img_edit_service/img_edit.py --images $VET_IMG $ROOM_IMG --prompt "Place the vet naturally in the room with realistic scale, soft cinematic lighting, and coherent shadows." --output-dir output/img-edit

# 3 image inputs (scene composition)
python services/img_edit_service/img_edit.py --images $CAT_IMG $GIRL_IMG $ROOM_IMG --prompt "Compose a natural indoor scene with the girl and cat inside the room, preserving each subject's identity and realistic proportions." --output-dir output/img-edit
```

## 5) edit_angle (single image, provided angle prompt set)

```powershell
python services/edit_angle_service/edit_angle.py --image $CAT_IMG --prompt "Turn the camera to a close-up." --output-dir output/edit-angle
python services/edit_angle_service/edit_angle.py --image $CAT_IMG --prompt "Turn the camera to a wide-angle lens." --output-dir output/edit-angle

python services/edit_angle_service/edit_angle.py --image $VET_IMG --prompt "Rotate the camera 45 degrees to the right." --output-dir output/edit-angle
python services/edit_angle_service/edit_angle.py --image $VET_IMG --prompt "Rotate the camera 90 degrees to the right." --output-dir output/edit-angle

python services/edit_angle_service/edit_angle.py --image $GIRL_IMG --prompt "Turn the camera to an aerial view." --output-dir output/edit-angle
python services/edit_angle_service/edit_angle.py --image $GIRL_IMG --prompt "Turn the camera to a low-angle view." --output-dir output/edit-angle

python services/edit_angle_service/edit_angle.py --image $ROOM_IMG --prompt "Rotate the camera 45 degrees to the left." --output-dir output/edit-angle
python services/edit_angle_service/edit_angle.py --image $ROOM_IMG --prompt "Rotate the camera 90 degrees to the left." --output-dir output/edit-angle
```

## 6) run_gen_eval (per-eval and combined)

Requires `output/img-edit/ComfyUI_00002_.png` and `output/img-edit/ComfyUI_00003_.png` to exist (generated by the img_edit commands in section 4).

```powershell
# ref coherence only — vet placed in room (2 refs, image output)
python scripts/run_gen_eval.py \
  --refs $VET_IMG $ROOM_IMG \
  --gen-output output/img-edit/ComfyUI_00002_.png \
  --prompt "Put vet in room" \
  --ref-coherence

# prompt adherence only — vet placed in room
python scripts/run_gen_eval.py \
  --refs $VET_IMG $ROOM_IMG \
  --gen-output output/img-edit/ComfyUI_00002_.png \
  --prompt "Put vet in room" \
  --prompt-adherence

# non-prompt artifact check only (not yet implemented — will skip)
python scripts/run_gen_eval.py \
  --refs $VET_IMG $ROOM_IMG \
  --gen-output output/img-edit/ComfyUI_00002_.png \
  --prompt "Put vet in room" \
  --non-prompt-artifact

# all evals — vet placed in room
python scripts/run_gen_eval.py \
  --refs $VET_IMG $ROOM_IMG \
  --gen-output output/img-edit/ComfyUI_00002_.png \
  --prompt "Put vet in room" \
  --all

# all evals — girl and cat placed in room (3 refs, image output)
python scripts/run_gen_eval.py \
  --refs $ROOM_IMG $GIRL_IMG $CAT_IMG \
  --gen-output output/img-edit/ComfyUI_00003_.png \
  --prompt "Put girl and cat in room" \
  --all

# --- Jadu QC data evals ---

# Single reference insufficient: 0af95e0c — ref coherence with original + front-view ref added
python scripts/run_gen_eval.py \
  --refs https://renderboard-test.s3.us-east-005.backblazeb2.com/images/asset-f1a2615a-11fe-4439-9830-3135df45af1a \
        https://renderboard-test.s3.us-east-005.backblazeb2.com/images/asset-79d772f5-e2d7-4366-ba3a-0b9de9fb6aec \
  --gen-output https://renderboard-test.s3.us-east-005.backblazeb2.com/videos/asset-b7ff4013-d03f-4569-bbb0-7eb544893597 \
  --prompt "Cuddles stands, stifling a yawn, and quietly exits. Koyal waves, her expression softened now, and watches him leave. Camera Angle: MEDIUM_SHOT" \
  --ref-coherence

# Single reference insufficient: b00805cf — ref coherence with original + front-view ref added
python scripts/run_gen_eval.py \
  --refs https://renderboard-test.s3.us-east-005.backblazeb2.com/images/asset-21484c98-ec53-4aae-b714-3d2fdaec9dd9 \
        https://renderboard-test.s3.us-east-005.backblazeb2.com/images/asset-79d772f5-e2d7-4366-ba3a-0b9de9fb6aec \
  --gen-output https://renderboard-test.s3.us-east-005.backblazeb2.com/videos/asset-f47fb629-b791-4b82-b753-54e871d4ec2b \
  --prompt "Cuddles and Koyal are relaxed. Both gaze out over the balcony, sitting closely but comfortably. Camera Angle: WIDE_SHOT" \
  --ref-coherence

# Unprompted artifact check: b00805cf — original single ref
python scripts/run_gen_eval.py \
  --refs https://renderboard-test.s3.us-east-005.backblazeb2.com/images/asset-21484c98-ec53-4aae-b714-3d2fdaec9dd9 \
  --gen-output https://renderboard-test.s3.us-east-005.backblazeb2.com/videos/asset-f47fb629-b791-4b82-b753-54e871d4ec2b \
  --prompt "Cuddles and Koyal are relaxed. Both gaze out over the balcony, sitting closely but comfortably. Camera Angle: WIDE_SHOT" \
  --non-prompt-artifact

# All evals: 505debbd — stylish woman in car at night
python scripts/run_gen_eval.py \
  --refs https://renderboard-test.s3.us-east-005.backblazeb2.com/images/base64-7fbd52ae-62cd-49f9-bf75-65588a7a8120 \
  --gen-output https://renderboard-test.s3.us-east-005.backblazeb2.com/videos/asset-39131511-fb32-4704-8e9a-30968dca4539 \
  --prompt "A stylish woman with a sleek bob haircut and dark sunglasses sits in the driver's seat of a car at night. She wears a sharp black suit and a ruby choker. Minimal motion, smooth and cinematic." \
  --non-prompt-artifact

# All evals: 50d1874a — Mohini pummels Vet comic action
python scripts/run_gen_eval.py \
  --refs https://renderboard-test.s3.us-east-005.backblazeb2.com/images/asset-a41f93e2-0728-4174-8b29-1da1cea72d92 \
  --gen-output https://renderboard-test.s3.us-east-005.backblazeb2.com/videos/asset-284f7a85-7a45-4c4c-b8e6-c2290fe37f24 \
  --prompt "Mohini pummels Vet with wild, flailing energy; both move in comic blur as onomatopoeic text appears with each blow. Camera Angle: INSERT_SHOT" \
  --all
```

## 7) run_qwen_chat (sample multi-turn conversation)

Start the session:

```powershell
python scripts/run_qwen_chat.py
```

Then paste the turns below one at a time. Each turn is labelled with the scenario it exercises.

```
# --- Turn 1: Image analysis ---
[$VET_IMG] I'm working on this character — can you describe him in detail?

# --- Turn 2: Shot/angle trigger ---
I want to see his face more clearly, the current shot feels too far back

# --- Turn 3: Prompt recognition trigger ---
Actually, I kind of want his coat to be dark navy instead of white

# --- Turn 4: Scene creation trigger ---
[$VET_IMG, $GIRL_IMG] I want to put both of these characters together in this room [$ROOM_IMG]

# --- Turn 5: Story/scene trigger ---
I want to tell a story with the vet character but I'm not sure what to do with him

# --- Turn 6: Save and exit ---
/export
```

