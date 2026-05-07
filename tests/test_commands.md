# Test Commands (Placeholder)

Run all commands from repo root: `d:\Work\Jadu Interview\jadu_image_video_ai_demo`

For **`run_qwen_vl` with `--video`**: extensionless or odd-container inputs are downloaded/transcoded to MP4 via **ffmpeg** (install e.g. `apt install ffmpeg`; cache: `output/.qwen-vl-video-cache/`).

## 1) Reusable variables

```powershell
$CAT_IMG="https://renderboard-test.s3.us-east-005.backblazeb2.com/images/base64-ea3a392a-23de-43c4-a915-83ebcc2a2725"
$VET_IMG="https://renderboard-test.s3.us-east-005.backblazeb2.com/images/base64-0c187082-bcd0-48b4-9fd6-9b8ca699b33a"
$GIRL_IMG="https://renderboard-test.s3.us-east-005.backblazeb2.com/images/base64-f38842e4-a365-479d-aa6c-c67e76ccc234"
$ROOM_IMG="https://renderboard-test.s3.us-east-005.backblazeb2.com/images/base64-6f9167f5-0d6e-4b2a-b02f-cebb165435a2"
$SCENE_VIDEO="https://renderboard-test.s3.us-east-005.backblazeb2.com/videos/asset-ee0e77cc-d735-4d35-bcbe-ef89eaa23789"
```


## 6) Ref-guided generation (character sheets + run_ref_guided_gen)

```powershell
# Use existing demo images as character refs (you can replace these with your own)

# 1) Create character sheets first (writes to storage/<name>/)
# Default: does NOT run VLM full-body gating.
python scripts/run_character_sheet_creation.py --image $VET_IMG --character-name "Eli"
python scripts/run_character_sheet_creation.py --image $GIRL_IMG --character-name "Beth"

# Optional: strict full-body gate (uses VLM). If NOT full-body, prints a corrected full-body
# image path and exits non-zero.
python scripts/run_character_sheet_creation.py --image $VET_IMG --character-name "Eli" --full-body-check
python scripts/run_character_sheet_creation.py --image $GIRL_IMG --character-name "Beth" --full-body-check


# 2) Run ref-guided generation
# With backdrop/scene reference:
python scripts/run_ref_guided_gen.py --prompt "@Eli sitting on the couch, staring at @Beth's phone" --backdrop-img $ROOM_IMG --output-dir output/ref-guided-gen

# Without backdrop:
python scripts/run_ref_guided_gen.py --prompt "@Eli sitting on the couch, staring at @Beth's phone" --output-dir output/ref-guided-gen
```

Notes:
- This requires `storage/Eli/Eli_character_sheet.png` and `storage/Beth/Beth_character_sheet.png` to exist (created by the commands above).
- `run_ref_guided_gen.py` supports up to **2** unique `@CharacterName` refs

## 2) img_edit (1, 2, 3 image inputs)

```powershell
# 1 image input (identity-preserving enhancement)
python services/img_edit_service/img_edit.py --images $CAT_IMG --prompt "Enhance detail and lighting while preserving the cat's identity and pose." --output-dir output/img-edit

# 2 image inputs (style/compositional blend)
python services/img_edit_service/img_edit.py --images $VET_IMG $ROOM_IMG --prompt "Place the vet naturally in the room with realistic scale, soft cinematic lighting, and coherent shadows." --output-dir output/img-edit

# 3 image inputs (scene composition)
python services/img_edit_service/img_edit.py --images $CAT_IMG $GIRL_IMG $ROOM_IMG --prompt "Compose a natural indoor scene with the girl and cat inside the room, preserving each subject's identity and realistic proportions." --output-dir output/img-edit
```

## 3) edit_angle (single image, provided angle prompt set)

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

## 4) run_qwen_vl (image-only, video-only, mixed)

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
```


