"""Qwen3-VL wrapper for multi-image + single-prompt evaluation via vLLM."""

from __future__ import annotations

import logging
from typing import Any, Optional, Sequence

from qwen_vl_utils import process_vision_info
from transformers import AutoProcessor
from vllm import LLM, SamplingParams

from utils.image_utils import load_image

LOGGER = logging.getLogger(__name__)


class QwenVL:
    """Orchestrates Qwen3-VL vLLM input preparation and inference."""

    def __init__(
        self,
        model_id: str = "Qwen/Qwen3-VL-8B-Thinking",
    ) -> None:
        self.model_id = model_id
        LOGGER.info("Loading Qwen3-VL processor: %s", model_id)
        try:
            self.processor = AutoProcessor.from_pretrained(model_id)
        except Exception as exc:
            raise RuntimeError(
                f"Failed to initialize Qwen3-VL processor '{model_id}'."
            ) from exc

        LOGGER.info("Loading vLLM engine for: %s", model_id)
        try:
            self.llm = LLM(
                model=model_id,
                trust_remote_code=True,
                tensor_parallel_size=1,
                gpu_memory_utilization=0.85,
                enforce_eager=False,
                seed=0,
            )
        except Exception as exc:
            raise RuntimeError(
                f"Failed to initialize vLLM engine for '{model_id}'."
            ) from exc
        LOGGER.info("Qwen3-VL vLLM engine is ready.")

    def build_messages(
        self,
        image_sources: Sequence[str],
        prompt: str,
        video_source: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        """Build Qwen3 chat-format messages from image sources and prompt."""
        content: list[dict[str, str]] = []
        for source in image_sources:
            load_image(source)
            content.append({"type": "image", "image": source})
        if video_source is not None:
            content.append({"type": "video", "video": video_source})
        content.append({"type": "text", "text": prompt})
        messages: list[dict[str, Any]] = [{"role": "user", "content": content}]
        LOGGER.info(
            "Built Qwen3 messages with %d image(s)%s.",
            len(image_sources),
            " and 1 video" if video_source else "",
        )
        return messages

    def prepare_vllm_input(self, messages: Sequence[dict[str, Any]]) -> dict[str, Any]:
        """Convert chat messages into vLLM multimodal input payload."""
        try:
            prompt = self.processor.apply_chat_template(
                list(messages),
                tokenize=False,
                add_generation_prompt=True,
            )
            image_inputs, video_inputs, video_kwargs = process_vision_info(
                messages,
                image_patch_size=self.processor.image_processor.patch_size,
                return_video_kwargs=True,
                return_video_metadata=True,
            )
        except Exception as exc:
            raise RuntimeError("Failed to prepare Qwen3-vLLM input payload.") from exc

        mm_data: dict[str, Any] = {}
        if image_inputs is not None:
            mm_data["image"] = image_inputs
        if video_inputs is not None:
            mm_data["video"] = video_inputs
        return {
            "prompt": prompt,
            "multi_modal_data": mm_data,
            "mm_processor_kwargs": video_kwargs,
        }

    def vl_eval(
        self,
        image_sources: Sequence[str],
        prompt: str,
        video_source: Optional[str] = None,
    ) -> str:
        """Run one Qwen3-vLLM multimodal evaluation and return response text."""
        messages = self.build_messages(image_sources, prompt, video_source=video_source)
        llm_input = self.prepare_vllm_input(messages)

        LOGGER.info("Starting Qwen3-vLLM inference.")
        try:
            outputs = self.llm.generate(
                [llm_input],
                sampling_params=SamplingParams(
                    temperature=0.0,
                    max_tokens=1024,
                    top_k=-1,
                ),
            )
        except Exception as exc:
            raise RuntimeError("Qwen3-vLLM inference failed.") from exc

        if not outputs or not outputs[0].outputs:
            raise RuntimeError("Qwen3-vLLM returned no output.")
        text = outputs[0].outputs[0].text
        LOGGER.info("Qwen3-vLLM inference completed.")
        return str(text)
