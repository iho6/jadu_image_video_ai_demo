"""Qwen3-VL wrapper for multi-image + single-prompt evaluation via Transformers."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Optional, Sequence

import torch
from qwen_vl_utils import process_vision_info
from transformers import AutoModelForVision2Seq, AutoProcessor

from utils.image_utils import load_image

LOGGER = logging.getLogger(__name__)


class QwenVL:
    """Orchestrates Qwen3-VL Transformers input preparation and inference."""

    def __init__(
        self,
        model_id: str = "models/hf/Qwen__Qwen3-VL-4B-Instruct",
    ) -> None:
        self.model_id = model_id

        if ("/" in model_id or model_id.startswith(".")) and not Path(model_id).exists():
            raise RuntimeError(
                f"Qwen3-VL weights not found at '{model_id}'.\n"
                "Download them first, e.g.:\n"
                "  python utils/download_hf_weights.py --repo-id Qwen/Qwen3-VL-4B-Instruct "
                "--local-dir models/hf/Qwen__Qwen3-VL-4B-Instruct\n"
                "Or pass a valid local path / HF repo id."
            )

        if not torch.cuda.is_available():
            raise RuntimeError(
                "CUDA is not available for QwenVL. "
                f"torch.version.cuda={torch.version.cuda}. "
                "Verify the NVIDIA driver matches this torch CUDA build."
            )
        self.device = torch.device("cuda:0")
        dtype = torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16

        LOGGER.info("Loading Qwen3-VL processor: %s", model_id)
        try:
            self.processor = AutoProcessor.from_pretrained(model_id, trust_remote_code=True)
        except Exception as exc:
            LOGGER.exception("Failed to load Qwen3-VL processor for %s", model_id)
            raise RuntimeError(
                f"Failed to initialize Qwen3-VL processor '{model_id}'."
            ) from exc

        LOGGER.info("Loading Qwen3-VL model: %s (device=%s, dtype=%s)", model_id, self.device, dtype)
        try:
            self.model = (
                AutoModelForVision2Seq.from_pretrained(
                    model_id,
                    trust_remote_code=True,
                    torch_dtype=dtype,
                    low_cpu_mem_usage=True,
                )
                .to(self.device)
                .eval()
            )
        except Exception as exc:
            LOGGER.exception("Failed to load Qwen3-VL model for %s", model_id)
            raise RuntimeError(f"Failed to initialize Qwen3-VL model '{model_id}'.") from exc
        LOGGER.info("Qwen3-VL Transformers model is ready on %s.", self.device)

    def build_messages(
        self,
        image_sources: Sequence[str],
        prompt: str,
        video_source: Optional[str] = None,
        *,
        max_pixels: int = 1280 * 28 * 28,
    ) -> list[dict[str, Any]]:
        """Build Qwen3 chat-format messages from image sources and prompt."""
        content: list[dict[str, str]] = []
        for source in image_sources:
            load_image(source)
            content.append({"type": "image", "image": source, "max_pixels": max_pixels})
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

    def vl_eval(
        self,
        image_sources: Sequence[str],
        prompt: str,
        video_source: Optional[str] = None,
        *,
        max_new_tokens: int = 1024,
    ) -> str:
        """Run one Qwen3-VL multimodal evaluation and return the generated response text."""
        messages = self.build_messages(image_sources, prompt, video_source=video_source)

        try:
            prompt_text = self.processor.apply_chat_template(
                list(messages),
                tokenize=False,
                add_generation_prompt=True,
            )
            image_inputs, video_inputs, video_kwargs = process_vision_info(
                messages,
                return_video_kwargs=True,
            )
        except Exception as exc:
            LOGGER.exception("Qwen3-VL input preparation failed")
            raise RuntimeError("Failed to prepare Qwen3-VL input payload.") from exc

        proc_kwargs: dict[str, Any] = dict(video_kwargs) if isinstance(video_kwargs, dict) else {}
        inputs = self.processor(
            text=[prompt_text],
            images=image_inputs,
            videos=video_inputs,
            padding=True,
            return_tensors="pt",
            **proc_kwargs,
        ).to(self.device)

        LOGGER.info("Starting Qwen3-VL inference on %s.", self.device)
        try:
            with torch.inference_mode():
                out = self.model.generate(**inputs, max_new_tokens=max_new_tokens, do_sample=False)
        except Exception as exc:
            LOGGER.exception("Qwen3-VL inference failed")
            raise RuntimeError("Qwen3-VL inference failed.") from exc

        generated = out[:, inputs.input_ids.shape[1]:]
        text = self.processor.batch_decode(generated, skip_special_tokens=True)[0]
        LOGGER.info("Qwen3-VL inference completed.")
        return str(text).strip()

    def chat(
        self,
        messages: list[dict],
        *,
        max_new_tokens: int = 1024,
    ) -> str:
        """Run multi-turn inference over a full messages list; return only the new assistant text."""
        if not messages:
            raise ValueError("messages must be non-empty")

        try:
            prompt_text = self.processor.apply_chat_template(
                messages,
                tokenize=False,
                add_generation_prompt=True,
            )
            image_inputs, video_inputs, video_kwargs = process_vision_info(
                messages,
                return_video_kwargs=True,
            )
        except Exception as exc:
            LOGGER.exception("Qwen3-VL chat input preparation failed")
            raise RuntimeError("Failed to prepare Qwen3-VL chat input.") from exc

        proc_kwargs: dict[str, Any] = dict(video_kwargs) if isinstance(video_kwargs, dict) else {}
        inputs = self.processor(
            text=[prompt_text],
            images=image_inputs,
            videos=video_inputs,
            padding=True,
            return_tensors="pt",
            **proc_kwargs,
        ).to(self.device)

        LOGGER.info("Starting Qwen3-VL chat inference (turn depth=%d).", len(messages))
        try:
            with torch.inference_mode():
                out = self.model.generate(**inputs, max_new_tokens=max_new_tokens, do_sample=False)
        except Exception as exc:
            LOGGER.exception("Qwen3-VL chat inference failed")
            raise RuntimeError("Qwen3-VL chat inference failed.") from exc

        generated = out[:, inputs.input_ids.shape[1]:]
        text = self.processor.batch_decode(generated, skip_special_tokens=True)[0]
        LOGGER.info("Qwen3-VL chat inference completed.")
        return str(text).strip()
