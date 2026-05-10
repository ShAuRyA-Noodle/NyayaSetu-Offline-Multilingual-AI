"""
Production-grade LLM Client for NyayaSetu-GovAgent
Supports Groq cloud API (primary) with Ollama local fallback.
Same interface as before — all existing callers work unchanged.
"""

import os
import requests
import time
import logging
import threading
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

    # Shared generation settings.
    # NOTE: temperature=0.0 is recommended for deterministic routing /
    # classification (grievance router, intent classifier). Callers can
    # override per-call via .generate(..., temperature=...).
    temperature: float = 0.1
    # Bumped from 150 → 800. The old default truncated answers mid-sentence
    # and was the root cause of "repair_incomplete_json" silently fabricating
    # fields. Callers that want short outputs still pass max_tokens explicitly.
    max_tokens: int = 800
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

    # ------------------------------------------------------------------
    # Class-level circuit breaker
    #
    # If Groq returns 3 consecutive 5xx within 60s, open the breaker for
    # 5 minutes. While open, generate() short-circuits and returns a
    # "service_degraded" error rather than hammering a sick upstream.
    # Shared across instances because all clients hit the same Groq edge.
    # ------------------------------------------------------------------
    _CB_FAILURE_THRESHOLD = 3
    _CB_FAILURE_WINDOW_SEC = 60.0
    _CB_OPEN_DURATION_SEC = 300.0  # 5 min

    _circuit_breaker: Dict[str, Any] = {
        "failures": 0,            # consecutive 5xx count
        "first_failure_at": None,  # timestamp of first failure in window
        "opened_at": None,         # timestamp breaker was opened (None if closed)
        "is_open": False,
    }
    _cb_lock = threading.Lock()

    def __init__(self, config: Optional[LLMConfig] = None):
        self.config = config or LLMConfig()
        self._validate_configuration()
        self._use_groq = bool(self.config.groq_api_key)
        backend = "Groq Cloud" if self._use_groq else "Ollama Local"
        model = self.config.groq_model if self._use_groq else self.config.model
        logger.info(f"Initialized LLMClient → {backend} ({model})")

    # ------------------------------------------------------------------
    # Circuit breaker helpers
    # ------------------------------------------------------------------

    @classmethod
    def _cb_should_short_circuit(cls) -> bool:
        """Return True if breaker is open and we should fail fast."""
        with cls._cb_lock:
            if not cls._circuit_breaker["is_open"]:
                return False
            opened_at = cls._circuit_breaker["opened_at"] or 0.0
            if time.time() - opened_at >= cls._CB_OPEN_DURATION_SEC:
                # Half-open: clear and allow one trial.
                cls._circuit_breaker.update(
                    failures=0,
                    first_failure_at=None,
                    opened_at=None,
                    is_open=False,
                )
                logger.info("LLM circuit breaker reset → half-open trial")
                return False
            return True

    @classmethod
    def _cb_record_failure(cls) -> None:
        """Record a 5xx (or transport) failure and possibly open the breaker."""
        now = time.time()
        with cls._cb_lock:
            first = cls._circuit_breaker["first_failure_at"]
            if first is None or (now - first) > cls._CB_FAILURE_WINDOW_SEC:
                # Start a fresh window
                cls._circuit_breaker["first_failure_at"] = now
                cls._circuit_breaker["failures"] = 1
            else:
                cls._circuit_breaker["failures"] += 1

            if cls._circuit_breaker["failures"] >= cls._CB_FAILURE_THRESHOLD:
                cls._circuit_breaker["is_open"] = True
                cls._circuit_breaker["opened_at"] = now
                logger.error(
                    "LLM circuit breaker OPENED — %d consecutive 5xx in %.0fs window. "
                    "Will short-circuit for %.0fs.",
                    cls._circuit_breaker["failures"],
                    cls._CB_FAILURE_WINDOW_SEC,
                    cls._CB_OPEN_DURATION_SEC,
                )

    @classmethod
    def _cb_record_success(cls) -> None:
        """Reset failure counters on a healthy response."""
        with cls._cb_lock:
            if cls._circuit_breaker["failures"] or cls._circuit_breaker["is_open"]:
                cls._circuit_breaker.update(
                    failures=0,
                    first_failure_at=None,
                    opened_at=None,
                    is_open=False,
                )

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

        # Circuit breaker only applies to the Groq cloud path. Local Ollama
        # is on the same host as the API server — failing fast there has no
        # benefit and would just hide local restarts.
        if self._use_groq and self._cb_should_short_circuit():
            return {
                "success": False,
                "error": "service_degraded",
                "metadata": {
                    "reason": "circuit_breaker_open",
                    "backend": "groq",
                },
            }

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
                    self._cb_record_success()
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

                # Rate limit — Groq returns 429. Don't count toward breaker;
                # 429 is a client-side throttle, not an upstream outage.
                if response.status_code == 429:
                    retry_after = float(response.headers.get("retry-after", 2))
                    logger.warning(f"Groq rate limited. Retrying in {retry_after}s...")
                    time.sleep(retry_after)
                    continue

                # 5xx → upstream failure → feed the circuit breaker.
                if 500 <= response.status_code < 600:
                    self._cb_record_failure()

                error_msg = f"HTTP {response.status_code}: {response.text[:300]}"
                logger.warning(f"Attempt {attempt+1} failed: {error_msg}")

            except requests.exceptions.Timeout:
                error_msg = f"Request timeout after {self.config.timeout}s"
                logger.warning(f"Attempt {attempt+1} timed out")
                # Treat timeouts as upstream failures for breaker purposes.
                self._cb_record_failure()

            except requests.exceptions.RequestException as e:
                error_msg = f"Request failed: {e}"
                logger.error(f"Attempt {attempt+1} failed: {error_msg}")
                self._cb_record_failure()

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


def assert_groq_reachable() -> None:
    """Startup health check for the dependencies layer.

    In production (`ENV=production`), if Groq is configured but unreachable,
    this raises RuntimeError so deployment fails loudly instead of silently
    falling back to Ollama (which is almost certainly NOT installed on the
    serverless host). In dev, we log a warning and let Ollama fallback take
    over.
    """
    env = os.environ.get("ENV", "development").lower()
    groq_key = os.environ.get("GROQ_API_KEY", "")

    if not groq_key:
        if env == "production":
            raise RuntimeError(
                "GROQ_API_KEY is not set in production. "
                "Refusing to start — silent Ollama fallback would crash on "
                "serverless hosts. Set GROQ_API_KEY or explicitly switch to "
                "an environment where Ollama is reachable."
            )
        logger.warning(
            "GROQ_API_KEY not set — LLM client will use local Ollama. "
            "This is fine for development but NOT for production."
        )
        return

    client = OllamaClient(LLMConfig(groq_api_key=groq_key))
    if not client.health_check():
        if env == "production":
            raise RuntimeError(
                "Groq health check failed in production. "
                "Refusing to start with a degraded LLM backend."
            )
        logger.warning("Groq health check failed — falling back to Ollama if available.")


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
