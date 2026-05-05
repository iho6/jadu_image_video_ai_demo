# Test Commands (Placeholder)

Run all commands from repo root: `d:\Work\Jadu Interview\jadu_image_video_ai_demo`

## 1) Reusable variables

```powershell
$CAT_IMG = "https://renderboard-test.s3.us-east-005.backblazeb2.com/images/base64-ea3a392a-23de-43c4-a915-83ebcc2a2725"
$VET_IMG = "https://renderboard-test.s3.us-east-005.backblazeb2.com/images/base64-0c187082-bcd0-48b4-9fd6-9b8ca699b33a"
$GIRL_IMG = "https://renderboard-test.s3.us-east-005.backblazeb2.com/images/base64-f38842e4-a365-479d-aa6c-c67e76ccc234"
$ROOM_IMG = "https://renderboard-test.s3.us-east-005.backblazeb2.com/images/base64-6f9167f5-0d6e-4b2a-b02f-cebb165435a2"
$SCENE_VIDEO = "https://renderboard-test.s3.us-east-005.backblazeb2.com/videos/asset-ee0e77cc-d735-4d35-bcbe-ef89eaa23789"
```

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

## 5) Optional Comfy URL override (if not default 8188)

```powershell
python services/img_edit_service/img_edit.py --images $CAT_IMG --prompt "Enhance details." --comfy-url "http://127.0.0.1:8188"
python services/edit_angle_service/edit_angle.py --image $CAT_IMG --prompt "Turn the camera to a close-up." --comfy-url "http://127.0.0.1:8188"
```
