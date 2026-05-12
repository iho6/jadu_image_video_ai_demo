"""Evaluator classes for assessing generated image/video outputs."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from qwen_vl import QwenVL
from utils.prompt_utils import (
    build_ref_comf_req_check_prompt,
    build_ref_consistency_eval_prompt,
)
from utils.vlm_utils import parse_yes_no_eval_output, parse_out_of_5_eval_output

_VIDEO_EXTS = {".mp4", ".mov", ".mkv", ".avi", ".webm", ".m4v"}


def detect_output_type(path: str) -> str:
    """Return 'video' or 'image' based on the output path extension."""
    return "video" if Path(path).suffix.lower() in _VIDEO_EXTS else "image"



class RefConsistencyEval:
    """Evaluates whether a generated output maintains visual consistency with input references.

    Two-step evaluation:
    1. ref_comf_required_check — VLM decides if consistency should be expected given the prompt.
    2. ref_consistency_eval    — VLM scores consistency 0–5, grounded by the check's reasoning.
    """

    def ref_comf_required_check(
        self,
        runner: QwenVL,
        ref_paths: list[str],
        user_prompt: str,
        output_path: str,
    ) -> dict[str, Any]:
        """Call VLM to determine whether reference consistency evaluation is needed.

        Returns {"required": bool | None, "reasoning": str}.
        """
        output_type = detect_output_type(output_path)
        n = len(ref_paths)
        prompt_text = build_ref_comf_req_check_prompt(
            user_prompt=user_prompt,
            ref_idx_range=(1, n),
            output_idx=n + 1,
            output_type=output_type,
        )
        if output_type == "video":
            response = runner.vl_eval(ref_paths, prompt_text, video_source=output_path)
        else:
            response = runner.vl_eval([*ref_paths, output_path], prompt_text)
        return parse_yes_no_eval_output(response)

    def ref_consistency_eval(
        self,
        runner: QwenVL,
        ref_paths: list[str],
        user_prompt: str,
        output_path: str,
        prior_analysis: str,
    ) -> dict[str, Any]:
        """Score reference consistency 0–5, grounded by the prior check's reasoning.

        Returns {"score": int | None, "reasoning": str}.
        """
        output_type = detect_output_type(output_path)
        n = len(ref_paths)
        prompt_text = build_ref_consistency_eval_prompt(
            user_prompt=user_prompt,
            ref_idx_range=(1, n),
            output_idx=n + 1,
            output_type=output_type,
            prior_analysis=prior_analysis,
        )
        if output_type == "video":
            response = runner.vl_eval(ref_paths, prompt_text, video_source=output_path)
        else:
            response = runner.vl_eval([*ref_paths, output_path], prompt_text)
        return parse_out_of_5_eval_output(response)


class PromptAdherenceEval:
    """Evaluates how well the generated output adheres to the user prompt."""

    pass  # placeholder


class UnpromptedArtifactCheckEval:
    """Checks for unprompted artifacts or anomalies in the generated output."""

    pass  # placeholder
