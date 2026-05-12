"""Media description using Qwen VL."""

from __future__ import annotations

from utils.vlm_utils import detect_output_type
from qwen_vl import QwenVL
from utils.prompt_utils import DESCRIBE_MEDIA_PROMPT


def describe_media(runner: QwenVL, path: str) -> str:
    """Return a detailed description of an image or video at the given path or URL."""
    if detect_output_type(path) == "video":
        return runner.vl_eval([], DESCRIBE_MEDIA_PROMPT, video_source=path)
    return runner.vl_eval([path], DESCRIBE_MEDIA_PROMPT)
