"""
Local on-device LLM client (llama.cpp) — the true offline inference lane.

Runs a compact, quantized GGUF model fully on-device via llama-cpp-python. No
network, no Ollama daemon, no cloud. This is what makes the paper's
"compact, on-device, quantized, no-internet" claim literally true.

Default model: Qwen2.5-3B-Instruct Q4_K_M (~1.8 GB) at
``models/llm/Qwen2.5-3B-Instruct-Q4_K_M.gguf``. Runs on CPU everywhere and
offloads to GPU when a CUDA/Metal build of llama-cpp-python is installed
(set ``LOCAL_LLM_GPU_LAYERS=-1``).

Exposes the SAME ``generate()`` contract as ``OllamaClient`` —
``{success, response, error, metadata}`` — so it is a drop-in offline provider.
"""

from __future__ import annotations

import logging
import os
import threading
import time
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

DEFAULT_MODEL_PATH = os.getenv(
    "LOCAL_LLM_PATH",
    str(
        Path(__file__).resolve().parents[2]
        / "models" / "llm" / "Qwen2.5-3B-Instruct-Q4_K_M.gguf"
    ),
)


class LocalLLMClient:
    """Thread-safe wrapper around a llama.cpp GGUF model."""

    def __init__(
        self,
        model_path: str = DEFAULT_MODEL_PATH,
        n_ctx: int = 4096,
        n_threads: Optional[int] = None,
        n_gpu_layers: Optional[int] = None,
        temperature: float = 0.1,
        max_tokens: int = 800,
    ):
        self.model_path = model_path
        self.n_ctx = n_ctx
        self.n_threads = n_threads or os.cpu_count() or 4
        # -1 offloads all layers to GPU (needs a CUDA/Metal build); 0 = CPU.
        self.n_gpu_layers = (
            n_gpu_layers
            if n_gpu_layers is not None
            else int(os.getenv("LOCAL_LLM_GPU_LAYERS", "0"))
        )
        self.temperature = temperature
        self.max_tokens = max_tokens
        self._llm = None
        self._lock = threading.Lock()
        self._load_error: Optional[str] = None

    # ---- availability ------------------------------------------------------

    def is_available(self) -> bool:
        """True if the model file exists and llama_cpp is importable."""
        if not Path(self.model_path).exists():
            return False
        try:
            import llama_cpp  # noqa: F401,WPS433
            return True
        except Exception:  # noqa: BLE001
            return False

    def _ensure_loaded(self) -> bool:
        if self._llm is not None:
            return True
        if self._load_error is not None:
            return False
        with self._lock:
            if self._llm is not None:
                return True
            try:
                from llama_cpp import Llama  # noqa: WPS433

                logger.info("Loading local LLM: %s", self.model_path)
                t0 = time.time()
                self._llm = Llama(
                    model_path=self.model_path,
                    n_ctx=self.n_ctx,
                    n_threads=self.n_threads,
                    n_gpu_layers=self.n_gpu_layers,
                    verbose=False,
                )
                logger.info("Local LLM loaded in %.1fs", time.time() - t0)
                return True
            except Exception as e:  # noqa: BLE001
                self._load_error = str(e)
                logger.error("Failed to load local LLM: %s", e)
                return False

    # ---- generation --------------------------------------------------------

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Generate a completion fully offline.

        Returns the same shape as the cloud/Ollama client:
        ``{success, response, error, metadata}``.
        """
        if not prompt or not prompt.strip():
            raise ValueError("Prompt cannot be empty")

        if not self._ensure_loaded():
            return {
                "success": False,
                "response": "",
                "error": f"local_llm_unavailable: {self._load_error}",
                "metadata": {"backend": "llama.cpp"},
            }

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        t0 = time.time()
        try:
            with self._lock:
                out = self._llm.create_chat_completion(
                    messages=messages,
                    temperature=self.temperature if temperature is None else temperature,
                    max_tokens=self.max_tokens if max_tokens is None else max_tokens,
                )
        except Exception as e:  # noqa: BLE001
            return {
                "success": False,
                "response": "",
                "error": f"local_llm_error: {e}",
                "metadata": {"backend": "llama.cpp"},
            }

        text = out["choices"][0]["message"]["content"].strip()
        usage = out.get("usage", {})
        return {
            "success": True,
            "response": text,
            "error": "",
            "metadata": {
                "backend": "llama.cpp",
                "model": Path(self.model_path).name,
                "latency_s": round(time.time() - t0, 3),
                "prompt_tokens": usage.get("prompt_tokens"),
                "completion_tokens": usage.get("completion_tokens"),
                "offline": True,
            },
        }


# ---- module singleton ------------------------------------------------------

_local_client: Optional[LocalLLMClient] = None


def get_local_llm() -> LocalLLMClient:
    global _local_client
    if _local_client is None:
        _local_client = LocalLLMClient()
    return _local_client
