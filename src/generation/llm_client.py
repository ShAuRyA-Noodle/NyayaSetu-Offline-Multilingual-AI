"""
Production-grade LLM Client for NyayaSetu-GovAgent
Supports Groq cloud API (primary) with Ollama local fallback.
Same interface as before — all existing callers work unchanged.
"""

import os
import requests
import time
import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

@dataclass
class LLMConfig:
    """Configuration for LLM inference"""
    # Groq settings (primary)
    groq_api_key: str = ""
    groq_model: str = "llama-3.3-70b-versatile"
    groq_base_url: str = "https://api.groq.com/openai/v1"

    # Ollama settings (local fallback)
    model: str = "qwen2.5:14b-instruct-q4_0"
    base_url: str = "http://localhost:11434"

    # Shared generation settings
    temperature: float = 0.1
    max_tokens: int = 150
    timeout: int = 90
    max_retries: int = 3
    retry_delay: float = 1.0

    def __post_init__(self):
        # Pull Groq key from env if not set directly
        if not self.groq_api_key:
            self.groq_api_key = os.getenv("GROQ_API_KEY", "")


# ---------------------------------------------------------------------------
# Unified Client — tries Groq first, falls back to Ollama
# ---------------------------------------------------------------------------

class OllamaClient:
    """
    Unified LLM client.
    - If GROQ_API_KEY is set → uses Groq cloud (fast, no GPU needed).
    - Otherwise → uses local Ollama as before.
    Keeps the same .generate() interface so nothing else changes.
    """

    def __init__(self, config: Optional[LLMConfig] = None):
        self.config = config or LLMConfig()
        self._validate_configuration()
        self._use_groq = bool(self.config.groq_api_key)
        backend = "Groq Cloud" if self._use_groq else "Ollama Local"
        model = self.config.groq_model if self._use_groq else self.config.model
        logger.info(f"Initialized LLMClient → {backend} ({model})")

    def _validate_configuration(self) -> None:
        if not 0 <= self.config.temperature <= 1:
            raise ValueError("Temperature must be between 0 and 1")
        if self.config.max_tokens < 1:
            raise ValueError("max_tokens must be positive")
        if self.config.timeout < 1:
            raise ValueError("timeout must be at least 1 second")
        logger.info("Configuration validated successfully")

    # ------------------------------------------------------------------
    # Health check
    # ------------------------------------------------------------------

    def health_check(self) -> bool:
        if self._use_groq:
            return self._groq_health_check()
        return self._ollama_health_check()

    def _groq_health_check(self) -> bool:
        try:
            response = requests.get(
                f"{self.config.groq_base_url}/models",
                headers={"Authorization": f"Bearer {self.config.groq_api_key}"},
                timeout=10,
            )
            if response.status_code == 200:
                logger.info(f"Health check passed. Groq model {self.config.groq_model} is available")
                return True
            logger.error(f"Groq health check failed: HTTP {response.status_code}")
            return False
        except Exception as e:
            logger.error(f"Groq health check failed: {e}")
            return False

    def _ollama_health_check(self) -> bool:
        try:
            response = requests.get(
                f"{self.config.base_url}/api/tags", timeout=5
            )
            if response.status_code == 200:
                models = response.json().get("models", [])
                model_names = [m["name"] for m in models]
                if self.config.model in model_names:
                    logger.info(f"Health check passed. Model {self.config.model} is available")
                    return True
                logger.error(f"Model {self.config.model} not found. Available: {model_names}")
                return False
            logger.error(f"Health check failed with status {response.status_code}")
            return False
        except requests.exceptions.RequestException as e:
            logger.error(f"Health check failed: {e}")
            return False

    # ------------------------------------------------------------------
    # Generate
    # ------------------------------------------------------------------

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Generate text. Same return shape as before:
        {success: bool, response: str, error: str, metadata: dict}
        """
        if not prompt or not prompt.strip():
            raise ValueError("Prompt cannot be empty")

        if self._use_groq:
            return self._generate_groq(prompt, system_prompt, temperature, max_tokens)
        return self._generate_ollama(prompt, system_prompt, temperature, max_tokens)

    # ---- Groq (OpenAI-compatible) -----------------------------------

    def _generate_groq(
        self, prompt: str, system_prompt: Optional[str],
        temperature: Optional[float], max_tokens: Optional[int],
    ) -> Dict[str, Any]:
        temp = temperature if temperature is not None else self.config.temperature
        max_tok = max_tokens if max_tokens is not None else self.config.max_tokens

        logger.info(f"Generating via Groq (temp={temp}, max_tokens={max_tok})")

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self.config.groq_model,
            "messages": messages,
            "temperature": temp,
            "max_tokens": max_tok,
            "top_p": 0.9,
        }

        for attempt in range(self.config.max_retries):
            try:
                start = time.time()
                response = requests.post(
                    f"{self.config.groq_base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.config.groq_api_key}",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                    timeout=self.config.timeout,
                )
                elapsed = time.time() - start

                if response.status_code == 200:
                    data = response.json()
                    text = data["choices"][0]["message"]["content"].strip()
                    usage = data.get("usage", {})
                    logger.info(f"Generation successful in {elapsed:.2f}s")
                    return {
                        "success": True,
                        "response": text,
                        "metadata": {
                            "model": self.config.groq_model,
                            "elapsed_time": elapsed,
                            "total_duration": elapsed,
                            "prompt_eval_count": usage.get("prompt_tokens", 0),
                            "eval_count": usage.get("completion_tokens", 0),
                        },
                    }

                # Rate limit — Groq returns 429
                if response.status_code == 429:
                    retry_after = float(response.headers.get("retry-after", 2))
                    logger.warning(f"Groq rate limited. Retrying in {retry_after}s...")
                    time.sleep(retry_after)
                    continue

                error_msg = f"HTTP {response.status_code}: {response.text[:300]}"
                logger.warning(f"Attempt {attempt+1} failed: {error_msg}")

            except requests.exceptions.Timeout:
                error_msg = f"Request timeout after {self.config.timeout}s"
                logger.warning(f"Attempt {attempt+1} timed out")

            except requests.exceptions.RequestException as e:
                error_msg = f"Request failed: {e}"
                logger.error(f"Attempt {attempt+1} failed: {error_msg}")

            except Exception as e:
                error_msg = f"Unexpected error: {e}"
                logger.error(error_msg)
                return {"success": False, "error": error_msg, "metadata": {}}

            if attempt < self.config.max_retries - 1:
                delay = self.config.retry_delay * (2 ** attempt)
                time.sleep(delay)

        return {"success": False, "error": error_msg, "metadata": {}}

    # ---- Ollama (local fallback) ------------------------------------

    def _generate_ollama(
        self, prompt: str, system_prompt: Optional[str],
        temperature: Optional[float], max_tokens: Optional[int],
    ) -> Dict[str, Any]:
        temp = temperature if temperature is not None else self.config.temperature
        max_tok = max_tokens if max_tokens is not None else self.config.max_tokens

        logger.info(f"Generating via Ollama (temp={temp}, max_tokens={max_tok})")

        payload = {
            "model": self.config.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temp,
                "num_predict": max_tok,
                "top_p": 0.9,
                "top_k": 40,
                "repeat_penalty": 1.1,
            },
        }
        if system_prompt:
            payload["system"] = system_prompt

        for attempt in range(self.config.max_retries):
            try:
                start = time.time()
                response = requests.post(
                    f"{self.config.base_url}/api/generate",
                    json=payload,
                    timeout=self.config.timeout,
                )
                elapsed = time.time() - start

                if response.status_code == 200:
                    result = response.json()
                    if "response" not in result:
                        return {"success": False, "error": "Invalid response structure", "metadata": {}}

                    logger.info(f"Generation successful in {elapsed:.2f}s")
                    return {
                        "success": True,
                        "response": result["response"].strip(),
                        "metadata": {
                            "model": self.config.model,
                            "elapsed_time": elapsed,
                            "total_duration": result.get("total_duration", 0) / 1e9,
                            "prompt_eval_count": result.get("prompt_eval_count", 0),
                            "eval_count": result.get("eval_count", 0),
                        },
                    }

                error_msg = f"HTTP {response.status_code}: {response.text}"
                logger.warning(f"Attempt {attempt+1} failed: {error_msg}")

            except requests.exceptions.Timeout:
                error_msg = f"Request timeout after {self.config.timeout}s"
                logger.warning(f"Attempt {attempt+1} timed out")

            except requests.exceptions.RequestException as e:
                error_msg = f"Request failed: {e}"
                logger.error(f"Attempt {attempt+1} failed: {error_msg}")

            except Exception as e:
                error_msg = f"Unexpected error: {e}"
                logger.error(error_msg)
                return {"success": False, "error": error_msg, "metadata": {}}

            if attempt < self.config.max_retries - 1:
                delay = self.config.retry_delay * (2 ** attempt)
                time.sleep(delay)

        return {"success": False, "error": error_msg, "metadata": {}}


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

def create_client(model: str = "qwen2.5:14b-instruct-q4_0") -> OllamaClient:
    """Factory function — creates configured client.
    If GROQ_API_KEY env var is set, uses Groq regardless of model param.
    """
    config = LLMConfig(model=model)
    return OllamaClient(config)


if __name__ == "__main__":
    print("Testing LLM Client...")
    client = create_client()
    if client.health_check():
        print("✓ LLM is available")
        result = client.generate(
            prompt="What is 2+2?",
            system_prompt="You are a helpful assistant. Answer concisely.",
        )
        if result["success"]:
            print(f"✓ Response: {result['response']}")
            print(f"  Time: {result['metadata']['elapsed_time']:.2f}s")
        else:
            print(f"✗ Failed: {result['error']}")
    else:
        print("✗ LLM not available")
