"""Evaluator classes for assessing generated image/video outputs."""

from __future__ import annotations

from typing import Any

from qwen_vl import QwenVL
from describe_media import describe_media
from utils.prompt_utils import (
    build_ref_comf_req_check_prompt,
    build_ref_consistency_eval_prompt,
    build_prompt_adherence_eval_prompt,
    build_list_unprompted_prompt,
    build_unprompted_artifact_eval_prompt,
    build_format_unprompted_question_prompt,
)
from utils.vlm_utils import (
    detect_output_type,
    parse_yes_no_eval_output,
    parse_out_of_5_eval_output,
    parse_bullet_list,
    parse_artifact_eval,
    extract_assistant_text,
)



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
    """Evaluates how well the generated output adheres to the user prompt.

    Always runs — no required-check gate. Always looks at both references and output.
    """

    def prompt_adherence_eval(
        self,
        runner: QwenVL,
        ref_paths: list[str],
        user_prompt: str,
        output_path: str,
    ) -> dict[str, Any]:
        """Score prompt adherence 0–5.

        Returns {"score": int | None, "reasoning": str}.
        """
        output_type = detect_output_type(output_path)
        n = len(ref_paths)
        prompt_text = build_prompt_adherence_eval_prompt(
            user_prompt=user_prompt,
            ref_idx_range=(1, n),
            output_idx=n + 1,
            output_type=output_type,
        )
        if output_type == "video":
            response = runner.vl_eval(ref_paths, prompt_text, video_source=output_path)
        else:
            response = runner.vl_eval([*ref_paths, output_path], prompt_text)
        return parse_out_of_5_eval_output(response)


class UnpromptedArtifactCheckEval:
    """Checks for unprompted elements and artifacts in the generated output.

    Two-step: describe_media() first, then list_unprompted() uses that description
    to enumerate output elements not mentioned in the user prompt.
    """

    def list_unprompted(
        self,
        runner: QwenVL,
        ref_paths: list[str],
        user_prompt: str,
        output_path: str,
    ) -> dict[str, Any]:
        """List all output elements not specified in the user prompt.

        Step 1: describe_media() — detailed description of the output.
        Step 2: VLM call with description injected — produces bullet list.

        Returns {"description": str, "unprompted_items": list[str]}.
        """
        output_type = detect_output_type(output_path)
        n = len(ref_paths)

        description = describe_media(runner, output_path)

        prompt_text = build_list_unprompted_prompt(
            user_prompt=user_prompt,
            ref_idx_range=(1, n),
            output_idx=n + 1,
            output_type=output_type,
            output_description=description,
        )
        if output_type == "video":
            response = runner.vl_eval(ref_paths, prompt_text, video_source=output_path)
        else:
            response = runner.vl_eval([*ref_paths, output_path], prompt_text)

        return {
            "description": description,
            "unprompted_items": parse_bullet_list(response),
        }

    def unprompted_artifact_list_eval(
        self,
        runner: QwenVL,
        ref_paths: list[str],
        user_prompt: str,
        output_path: str,
        unprompted_items: list[str],
    ) -> list[dict[str, Any]]:
        """Evaluate each unprompted item as desired (True) or undesired (False).

        One VLM call per item. Returns list of
        {"artifact": str, "desired": bool | None, "reasoning": str}.
        """
        output_type = detect_output_type(output_path)
        n = len(ref_paths)
        results = []
        for item in unprompted_items[:10]:
            prompt_text = build_unprompted_artifact_eval_prompt(
                user_prompt=user_prompt,
                ref_idx_range=(1, n),
                output_idx=n + 1,
                output_type=output_type,
                item=item,
            )
            if output_type == "video":
                response = runner.vl_eval(ref_paths, prompt_text, video_source=output_path)
            else:
                response = runner.vl_eval([*ref_paths, output_path], prompt_text)
            results.append(parse_artifact_eval(response))
        return results

    def format_unprompted_as_questions(
        self,
        runner: QwenVL,
        ref_paths: list[str],
        user_prompt: str,
        output_path: str,
        unprompted_items: list[str],
    ) -> list[str]:
        """Reformat each unprompted item as a 'Did you want...' question.

        One VLM call per item. Returns questions in the same order as unprompted_items.
        """
        output_type = detect_output_type(output_path)
        n = len(ref_paths)
        questions = []
        for item in unprompted_items:
            prompt_text = build_format_unprompted_question_prompt(
                user_prompt=user_prompt,
                ref_idx_range=(1, n),
                output_idx=n + 1,
                output_type=output_type,
                item=item,
            )
            if output_type == "video":
                response = runner.vl_eval(ref_paths, prompt_text, video_source=output_path)
            else:
                response = runner.vl_eval([*ref_paths, output_path], prompt_text)
            questions.append(extract_assistant_text(response).strip())
        return questions
