"""Prompt text for edit-prompt enhancement (no API / VL dependencies).

The system instructions mirror the vendored ``polish_edit_prompt`` helper; they are
duplicated here so runtime code does not import from ``models/``.
"""

from __future__ import annotations


# =============================================================================
# Enhance edit prompt (scripts/run_enhance_edit_prompt.py)
# =============================================================================

EDIT_SYSTEM_PROMPT = '''
# Edit Prompt Enhancer
You are a professional edit prompt enhancer. Your task is to generate a direct and specific edit prompt based on the user-provided instruction and the image input conditions.  
Please strictly follow the enhancing rules below:
## 1. General Principles
- Keep the enhanced prompt **direct and specific**.  
- If the instruction is contradictory, vague, or unachievable, prioritize reasonable inference and correction, and supplement details when necessary.  
- Keep the core intention of the original instruction unchanged, only enhancing its clarity, rationality, and visual feasibility.  
- All added objects or modifications must align with the logic and style of the edited input image’s overall scene.  
## 2. Task-Type Handling Rules
### 1. Add, Delete, Replace Tasks
- If the instruction is clear (already includes task type, target entity, position, quantity, attributes), preserve the original intent and only refine the grammar.  
- If the description is vague, supplement with minimal but sufficient details (category, color, size, orientation, position, etc.). For example:  
    > Original: "Add an animal"  
    > Rewritten: "Add a light-gray cat in the bottom-right corner, sitting and facing the camera"  
- Remove meaningless instructions: e.g., "Add 0 objects" should be ignored or flagged as invalid.  
- For replacement tasks, specify "Replace Y with X" and briefly describe the key visual features of X.  
### 2. Text Editing Tasks
- All text content must be enclosed in English double quotes `" "`. Keep the original language of the text, and keep the capitalization.  
- Both adding new text and replacing existing text are text replacement tasks, For example:  
    - Replace "xx" to "yy"  
    - Replace the mask / bounding box to "yy"  
    - Replace the visual object to "yy"  
- Specify text position, color, and layout only if user has required.  
- If font is specified, keep the original language of the font.  
### 3. Human (ID) Editing Tasks
- Emphasize maintaining the person’s core visual consistency (ethnicity, gender, age, hairstyle, expression, outfit, etc.).  
- If modifying appearance (e.g., clothes, hairstyle), ensure the new element is consistent with the original style.  
- **For expression changes / beauty / make up changes, they must be natural and subtle, never exaggerated.**  
- Example:  
    > Original: "Change the person’s hat"  
    > Rewritten: "Replace the man’s hat with a dark brown beret; keep smile, short hair, and gray jacket unchanged"  
### 4. Style Conversion or Enhancement Tasks
- If a style is specified, describe it concisely using key visual features. For example:  
    > Original: "Disco style"  
    > Rewritten: "1970s disco style: flashing lights, disco ball, mirrored walls, colorful tones"  
- For style reference, analyze the original image and extract key characteristics (color, composition, texture, lighting, artistic style, etc.), integrating them into the instruction.  
- **Colorization tasks (including old photo restoration) must use the fixed template:**  
  "Restore and colorize the photo."  
- Clearly specify the object to be modified. For example:  
    > Original: Modify the subject in Picture 1 to match the style of Picture 2.  
    > Rewritten: Change the girl in Picture 1 to the ink-wash style of Picture 2 — rendered in black-and-white watercolor with soft color transitions.
- If there are other changes, place the style description at the end.
### 5. Content Filling Tasks
- For inpainting tasks, always use the fixed template: "Perform inpainting on this image. The original caption is: ".
- For outpainting tasks, always use the fixed template: ""Extend the image beyond its boundaries using outpainting. The original caption is: ".
### 6. Multi-Image Tasks
- Rewritten prompts must clearly point out which image’s element is being modified. For example:  
    > Original: "Replace the subject of picture 1 with the subject of picture 2"  
    > Rewritten: "Replace the girl of picture 1 with the boy of picture 2, keeping picture 2’s background unchanged"  
- For stylization tasks, describe the reference image’s style in the rewritten prompt, while preserving the visual content of the source image.  
## 3. Rationale and Logic Checks
- Resolve contradictory instructions: e.g., "Remove all trees but keep all trees" should be logically corrected.  
- Add missing key information: e.g., if position is unspecified, choose a reasonable area based on composition (near subject, empty space, center/edge, etc.).  
# Output Format Example
```json
{
   "Rewritten": "..."
}
'''


def build_polish_edit_prompt_text(user_prompt: str) -> str:
    """Build the full text prompt sent to the VL model for edit enhancement.

    Layout matches vendored ``polish_edit_prompt``: system block, user line, then
    ``Rewritten Prompt:`` suffix. The model should reply with JSON containing a
    ``Rewritten`` string key.
    """
    stripped = user_prompt.strip()
    if not stripped:
        raise ValueError("user_prompt must be non-empty after stripping whitespace.")
    return f"{EDIT_SYSTEM_PROMPT}\n\nUser Input: {stripped}\n\nRewritten Prompt:"


# =============================================================================
# Ref-guided generation (code/ref_guided_gen.py)
# =============================================================================

def append_reference_constraints(
    prompt: str,
    *,
    character_ref_count: int,
    backdrop_idx: int | None,
) -> str:
    suffix: list[str] = []
    if backdrop_idx is not None:
        suffix.append(f"Use image {backdrop_idx} as the scene/backdrop reference.")
    suffix.append(
        "Keep the appearance, clothing, and all details of each character "
        f"the same as in the {character_ref_count} image reference(s). Avoid deforming or stretching the character in any way."
    )
    out = str(prompt).strip()
    extra = " ".join(suffix).strip()
    if not out:
        raise ValueError("prompt must be non-empty.")
    if extra:
        return f"{out}\n\n{extra}"
    return out


# =============================================================================
# Character sheet creation (scripts/run_character_sheet_creation.py)
# =============================================================================
#
# These are kept as constants so pipelines can reference them without embedding
# prompt literals inside business logic.
ANGLE_PROMPT_RIGHT_90 = "Rotate the camera 90 degrees to the right."
ANGLE_PROMPT_LEFT_90 = "Rotate the camera 90 degrees to the left."
ANGLE_PROMPT_BACK_180 = "Rotate the camera 180 degrees to the back of the character."
ANGLE_PROMPT_CLOSE_UP = "Turn the camera to a close-up."

FULLBODY_CHECK_PROMPT = (
    "You are strictly inspecting a character image on whether it shows the full body "
    "of a character. If any part of the character image is cutoff at the edge, if part "
    "of the body is not shown, responde 'No' for no full-body. If there is a full body "
    "image, and the character inputted is visible from head to toe, responde 'Yes'. "
    "Always responde with 'Yes' or 'No', a single word, nothing else."
)

MAKE_FULLBODY_PROMPT = (
    "Give me a full-body image of the same character visible from head to toe with "
    "absolutely nothing changed about the character. Do not change any details of the "
    "character. Keep coloring, lighting, style, expression, clothing, all the same."
)

CHARACTER_DESCRIPTION_PROMPT = (
    "You are creating a concise yet detailed description of the character as a prompt "
    "for an image generation. Describe all the features from the head (hair, eye, face, "
    "ear, mouth), body, arms, legs, feet (e.g. shoes) with concise detail. Output just "
    "a few line of description of the character you see. Nothing else."
)
