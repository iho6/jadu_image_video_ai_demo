"""Qwen-Image-Edit Plus: load from Hugging Face and run edits (PIL inputs only)."""

from __future__ import annotations

from typing import List, Optional, Sequence

import torch
from diffusers import QwenImageEditPlusPipeline
from PIL import Image


class LoadModel:
    """Loads a diffusers pipeline from a Hugging Face model id.

    On CUDA, uses model CPU offload (no full `pipe.to(cuda)`) to reduce VRAM use.
    """

    @staticmethod
    def load_model(
        model_id: str,
        *,
        device: str,
        dtype: torch.dtype,
    ) -> QwenImageEditPlusPipeline:
        pipe = QwenImageEditPlusPipeline.from_pretrained(
            model_id, torch_dtype=dtype
        )
        if device == "cuda" or device.startswith("cuda:"):
            pipe.enable_model_cpu_offload()
        else:
            pipe.to(device)
        pipe.set_progress_bar_config(disable=None)
        return pipe


class QwenImgEdit:
    """Inference wrapper; defaults match models/qwen_image/README.md Qwen-Image-Edit-2511 snippet."""

    def __init__(
        self,
        model_id: str = "Qwen/Qwen-Image-Edit-2511",
        device: Optional[str] = None,
        dtype: torch.dtype = torch.bfloat16,
    ) -> None:
        self.model_id = model_id
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.dtype = dtype
        self.pipe = LoadModel.load_model(
            model_id, device=self.device, dtype=dtype
        )

    def torch_generator(self, seed: Optional[int]) -> torch.Generator:
        g = torch.Generator(device=self.device)
        if seed is None:
            seed = int(torch.randint(0, 2**31 - 1, (1,)).item())
        g.manual_seed(seed)
        return g

    def edit(
        self,
        images: Sequence[Image.Image],
        prompt: str,
        *,
        seed: Optional[int] = None,
        num_inference_steps: int = 40,
        true_cfg_scale: float = 4.0,
        guidance_scale: float = 1.0,
        negative_prompt: str = " ",
        num_images_per_prompt: int = 1,  # number of images outputted (diffusers parameter name)
    ) -> List[Image.Image]:
        if not images:
            raise ValueError("images must be non-empty")
        inputs = {
            "image": list(images),
            "prompt": prompt,
            "generator": self.torch_generator(seed),
            "true_cfg_scale": true_cfg_scale,
            "negative_prompt": negative_prompt,
            "num_inference_steps": num_inference_steps,
            "guidance_scale": guidance_scale,
            "num_images_per_prompt": num_images_per_prompt,  # number of images outputted
        }
        with torch.inference_mode():
            out = self.pipe(**inputs)
        return list(out.images)
