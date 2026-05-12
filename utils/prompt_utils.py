"""Prompt constants and builders for all model-facing text in the pipeline.

Sections
--------
- Edit prompt enhancement  (scripts/run_enhance_edit_prompt.py)
- Ref-guided generation    (code/ref_guided_gen.py)
- Character sheet creation (scripts/run_character_sheet_creation.py)
- Chat REPL                (scripts/run_qwen_chat.py)
- Generation evaluation    (code/gen_eval.py)

Runtime code should import from here; never embed prompt literals in business logic.
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
ANGLE_PROMPT_RIGHT_90 = "Rotate the camera 90 degrees to the right. Show only 1 single character in the output image."
ANGLE_PROMPT_LEFT_90 = "Rotate the camera 90 degrees to the left. Show only 1 single character in the output image."
ANGLE_PROMPT_BACK_180 = "Rotate the camera 180 degrees to the back of the character. Show only 1 single character in the output image."
ANGLE_PROMPT_CLOSE_UP = "Turn the camera to a close-up. Show only 1 single character in the output image."

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


# =============================================================================
# Chat REPL (scripts/run_qwen_chat.py)
# =============================================================================

CHAT_SYSTEM_PROMPT = (
    "You are a character art assistant for a pipeline that generates character sheets "
    "and image edits. You can analyze images, answer questions about characters, and "
    "advise on the workflow.\n\n"
    "When the user wants to act on something, suggest the exact command:\n"
    "  Create a character sheet : /sheet <name> <image_path>\n"
    "  Describe a character     : /describe <image_path>\n"
    "  Save transcript          : /export\n"
    "  End the session          : /quit"
)


# =============================================================================
# Generation evaluation (code/gen_eval.py)
# =============================================================================

_GEN_TASK_DESC = {
    "image": "image-to-image generation task",
    "video": "reference-to-video generation task",
}


def build_ref_comf_req_check_prompt(
    user_prompt: str,
    ref_idx_range: tuple[int, int],
    output_idx: int,
    output_type: str,
) -> str:
    """Build the VLM prompt that decides whether ref-consistency eval is needed.

    Dynamic fields: task description, ref index range, output index, user prompt.
    The yes/no criteria and few-shot examples are static.
    Returns 'required' (bool) and 'reasoning' (str) when parsed.
    """
    task_desc = _GEN_TASK_DESC.get(output_type, _GEN_TASK_DESC["image"])
    media_label = "video" if output_type == "video" else "image"
    ref_start, ref_end = ref_idx_range
    return (
        f"You are evaluating an {task_desc} with input references "
        f"(image {ref_start} to image {ref_end}), the following user prompt: {user_prompt} "
        f"and ({media_label} {output_idx}), the {output_idx}th file, being the output result.\n\n"
        f"Think about the task the user is trying to accomplish via the prompt and references. "
        f"In this {task_desc}, is this a task where people/scenes/items in the reference should "
        f"keep layout/appearance consistent and unchanged? If specific items in the reference "
        f"should appear the same in the output, Response: Yes. Else if the user is using the "
        f"reference vaguely as a stylistic or concept guide, without specific things needing to "
        f"look exactly the same as in the reference, then Response: No.\n\n"
        "In addition to Yes/No response, return a Reasoning why, based on the user prompt, "
        "references may/may not expect to be consistent in the output. If consistency is "
        "expected, provide a brief description of what specific things from the reference are "
        "expected to be consistent. Refer to examples below:\n\n"
        "User Prompt: Turn the person in the first reference image into a cartoon character\n"
        "Image Ref (via description only): <girl with blonde hair, blue eyes, blue shirt>\n"
        "Response: Yes\n"
        "Reasoning: while the user doesn't expect the person in the reference image to be kept "
        "exactly the same, since the prompt demands changing of style, key traits, apperance, "
        "pose, and layout of the original reference such as the girl's blonde hair, blue eyes, "
        "and blue shirt, should be kept the same.\n\n"
        "User Prompt: Use this image as a style reference and output a city scene in the same style.\n"
        "Image Ref (via description only): <80s Japanese city pop album cover with neon, "
        "vibrantly-colored, sunset beach scene.>\n"
        "Response: No\n"
        "Reasoning: The user is using the reference image loosely for a style transfer task, so "
        "no specific item, person, or layout from the reference needs to be preserved.\n\n"
        "User Prompt: Put the person in image 1 on the sofa in the room shown in image 3, and "
        "the person in image 2 standing beside the sofa.\n"
        "Image Ref (via description only, in that order): <a cartoon character of an middle-aged "
        "male doctor in a white lab coat>, <a cartoon character of a girl with long curly black "
        "hair>, <a realistic image of a lab with table filled with equipments and a green sofa "
        "against the right wall>\n"
        "Response: Yes\n"
        "Reasoning: This task ask for the cartoon characters in image 1 and 2 to be edited "
        "directly into reference image 3, meaning that all visible aspect of the references "
        "should be kept the same. The appearance of the girl, the doctor, the distinct stylistic "
        "difference between the environment and characters, and the details of items on the table "
        "in the lab should be kept consistent."
    )


def build_ref_consistency_eval_prompt(
    user_prompt: str,
    ref_idx_range: tuple[int, int],
    output_idx: int,
    output_type: str,
    prior_analysis: str,
) -> str:
    """Build the VLM prompt that scores reference consistency 0–5.

    Dynamic fields: task description, ref index range, output index, media label,
    user prompt, prior evaluator analysis.
    The scoring rubric and few-shot examples are static.
    Returns 'score' (int 0-5) and 'reasoning' (str) when parsed.
    """
    task_desc = _GEN_TASK_DESC.get(output_type, _GEN_TASK_DESC["image"])
    media_label = "video" if output_type == "video" else "image"
    ref_start, ref_end = ref_idx_range
    return (
        f"You are evaluating an {task_desc} with input image {ref_start} to image {ref_end} being the "
        f"input references used for the generation task. This is the user's prompt: {user_prompt}. "
        f"({media_label} {output_idx}), the {output_idx}th file, is the output result from the generation task. Again, "
        f"{media_label} {output_idx} is the outputted result from the previous generation task "
        f"that you are evaluating against the reference(s) and the prompt.\n\n"
        f"In this image-editing/ref-to-video task, items in the reference should remain "
        f"consistent. Here is an analysis of what should be consistent by another evaluator:\n"
        f"{prior_analysis}\n\n"
        "Based on what should be kept consistent, evaluate every aspect of the appearance, "
        "layout, proportion, lighting/color, and other aspects between input reference(s) and "
        "output img/video to give a score out of 5, 5/5 being perfect consistency across "
        "elements; 4/5 being mild, unnoticeable inconsistencies; 3/5 being noticeable "
        "inconsistencies present; 2/5 being many noticeable inconsistencies; 1/5 being output "
        "is mostly inconsistent with the references; 0/5 is completely inconsistent.\n\n"
        "Also return a 'Reasoning' for the evaluation. Refer to below for example format:\n\n"
        "User Prompt: Turn the person in the first reference image into a cartoon character\n"
        "Image Ref (via description only): <girl with blonde hair, blue eyes, blue shirt>\n"
        "Output: <cartoon character, girl with blonde hair, slightly darker blue eyes, blue shirt>\n"
        "Prior Evaluator Analysis: while the user doesn't expect the person in the reference "
        "image to be kept exactly the same, since the prompt demands changing of style, key "
        "traits, apperance, pose, and layout of the original reference such as the girl's blonde "
        "hair, blue eyes, and blue shirt, should be kept the same.\n"
        "Response: 4/5\n"
        "Reasoning: In the acceptable realm of a style change, the character's features are "
        "mostly consistent, from clothing, age, hairstyle, color, and proportion. However, the "
        "color of the eye seems to be slightly off, though not noticeably. So 4/5.\n\n"
        "User Prompt: Put the person in image 1 on the sofa in the room shown in image 3, and "
        "the person in image 2 standing beside the sofa.\n"
        "Image Ref (via description only, in that order): <a cartoon character of an middle-aged "
        "male doctor in a white lab coat with stethoscope>, <a cartoon character of a girl with "
        "long curly black hair>, <a realistic image of a lab with table filled with equipments "
        "and a green sofa against the right wall>\n"
        "Output: <cartoon male doctor in white lab coat sitting on realistic couch, legs "
        "outstretched on the green sofa, girl with long curly black hair standing besides it, "
        "empty table in the lab.>\n"
        "Prior Evaluator Analysis: This task ask for the cartoon characters in image 1 and 2 to "
        "be edited directly into reference image 3, meaning that all visible aspect of the "
        "references should be kept the same. The appearance of the girl, the doctor, the "
        "distinct stylistic difference between the environment and characters, and the details "
        "of items on the table in the lab should be kept consistent.\n"
        "Response: 3/5\n"
        "Reasoning: Items in the lab should be kept consistent, but the previously cluttered "
        "table is now empty. There is a slight deformation with the doctor character because the "
        "cartoon leg is longer in seating position than in the reference. Otherwise, the doctor's "
        "face and the girls' whole appearance are consistent, and the stylistic differentiation "
        "between backdrop and character is kept the same."
    )
