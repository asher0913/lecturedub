"""Choose MLX on Apple Silicon, or PyTorch on an NVIDIA GPU."""

from __future__ import annotations

import os
import platform
import sys

MLX_ASR = "Qwen/Qwen3-ASR-1.7B"
CUDA_ASR = "Qwen/Qwen3-ASR-1.7B"
MLX_LLM = "mlx-community/Qwen3-8B-4bit"
CUDA_LLM = "Qwen/Qwen3-8B"
MLX_TTS = "mlx-community/Qwen3-TTS-12Hz-1.7B-CustomVoice-bf16"
CUDA_TTS = "Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice"
CUDA_ALIGNER = "Qwen/Qwen3-ForcedAligner-0.6B"


def backend() -> str:
    """``mlx`` on Apple Silicon, ``cuda`` on Windows and Linux."""
    choice = os.environ.get("LECTUREDUB_BACKEND", "").strip().lower()
    if choice in {"mlx", "cuda"}:
        return choice
    if sys.platform == "darwin" and platform.machine() in {"arm64", "aarch64"}:
        return "mlx"
    return "cuda"


def default_asr() -> str:
    return MLX_ASR if backend() == "mlx" else CUDA_ASR


def default_llm() -> str:
    return MLX_LLM if backend() == "mlx" else CUDA_LLM


def default_tts() -> str:
    return MLX_TTS if backend() == "mlx" else CUDA_TTS


def cuda_device() -> str:
    return os.environ.get("LECTUREDUB_CUDA_DEVICE", "cuda:0")


def torch_dtype():
    import torch

    if torch.cuda.is_available() and getattr(torch.cuda, "is_bf16_supported", lambda: False)():
        return torch.bfloat16
    return torch.float16


def require_cuda() -> str:
    try:
        import torch
    except ImportError as exc:
        raise RuntimeError(
            "NVIDIA support is not installed. Run: pip install 'lecturedub[nvidia]'"
        ) from exc
    if not torch.cuda.is_available():
        raise RuntimeError(
            "No NVIDIA GPU was found. Install a current NVIDIA driver, then reinstall PyTorch with CUDA."
        )
    return cuda_device()
