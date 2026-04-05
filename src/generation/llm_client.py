"""
Production-grade Ollama LLM Client for NyayaSetu-GovAgent
Handles all communication with local Ollama server with comprehensive error handling
"""

import requests
import time
import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class LLMConfig:
    """Configuration for LLM inference"""
    model: str = "qwen2.5:14b-instruct-q4_0"
    temperature: float = 0.1  # Near-deterministic for consistency
    max_tokens: int = 150  # Prevents rambling, forces conciseness
    timeout: int = 90  # seconds
    base_url: str = "http://localhost:11434"
    max_retries: int = 3
    retry_delay: float = 1.0  # Initial delay in seconds


class OllamaClient:
    """
    Production-ready Ollama client with:
    - Connection health checks
    - Retry logic with exponential backoff
    - Comprehensive error handling
    - Response validation
    - Detailed logging
    """
    
    def __init__(self, config: Optional[LLMConfig] = None):
        """
        Initialize Ollama client
        
        Args:
            config: LLM configuration (uses defaults if not provided)
        """
        self.config = config or LLMConfig()
        self._validate_configuration()
        logger.info(f"Initialized OllamaClient with model: {self.config.model}")
    
    def _validate_configuration(self) -> None:
        """Validate configuration parameters"""
        if self.config.temperature < 0 or self.config.temperature > 1:
            raise ValueError("Temperature must be between 0 and 1")
        
        if self.config.max_tokens < 1:
            raise ValueError("max_tokens must be positive")
        
        if self.config.timeout < 1:
            raise ValueError("timeout must be at least 1 second")
        
        logger.info("Configuration validated successfully")
    
    def health_check(self) -> bool:
        """
        Check if Ollama server is running and accessible
        
        Returns:
            True if server is healthy, False otherwise
        """
        try:
            response = requests.get(
                f"{self.config.base_url}/api/tags",
                timeout=5
            )
            
            if response.status_code == 200:
                models = response.json().get('models', [])
                model_names = [m['name'] for m in models]
                
                if self.config.model in model_names:
                    logger.info(f"Health check passed. Model {self.config.model} is available")
                    return True
                else:
                    logger.error(f"Model {self.config.model} not found. Available: {model_names}")
                    return False
            else:
                logger.error(f"Health check failed with status {response.status_code}")
                return False
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Health check failed: {e}")
            logger.error("Make sure Ollama is running: 'ollama serve'")
            return False
    
    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Generate text using Ollama with retry logic
        
        Args:
            prompt: User prompt
            system_prompt: System instructions (optional)
            temperature: Override default temperature
            max_tokens: Override default max_tokens
            
        Returns:
            Dictionary with:
                - success: bool
                - response: str (if successful)
                - error: str (if failed)
                - metadata: dict with timing and token info
                
        Raises:
            ValueError: If prompt is empty
        """
        if not prompt or not prompt.strip():
            raise ValueError("Prompt cannot be empty")
        
        # Use provided values or fall back to config
        temp = temperature if temperature is not None else self.config.temperature
        max_tok = max_tokens if max_tokens is not None else self.config.max_tokens
        
        logger.info(f"Generating response (temp={temp}, max_tokens={max_tok})")
        
        # Build request payload
        payload = {
            "model": self.config.model,
            "prompt": prompt,
            "stream": False,  # Disabled for determinism
            "options": {
                "temperature": temp,
                "num_predict": max_tok,
                "top_p": 0.9,  # Nucleus sampling
                "top_k": 40,
                "repeat_penalty": 1.1
            }
        }
        
        # Add system prompt if provided
        if system_prompt:
            payload["system"] = system_prompt
        
        # Retry loop with exponential backoff
        for attempt in range(self.config.max_retries):
            try:
                start_time = time.time()
                
                response = requests.post(
                    f"{self.config.base_url}/api/generate",
                    json=payload,
                    timeout=self.config.timeout
                )
                
                elapsed_time = time.time() - start_time
                
                if response.status_code == 200:
                    result = response.json()
                    
                    # Validate response structure
                    if 'response' not in result:
                        logger.error("Invalid response structure from Ollama")
                        return {
                            'success': False,
                            'error': 'Invalid response structure',
                            'metadata': {}
                        }
                    
                    generated_text = result['response'].strip()
                    
                    logger.info(f"Generation successful in {elapsed_time:.2f}s")
                    
                    return {
                        'success': True,
                        'response': generated_text,
                        'metadata': {
                            'model': self.config.model,
                            'elapsed_time': elapsed_time,
                            'total_duration': result.get('total_duration', 0) / 1e9,  # Convert to seconds
                            'prompt_eval_count': result.get('prompt_eval_count', 0),
                            'eval_count': result.get('eval_count', 0)
                        }
                    }
                else:
                    error_msg = f"HTTP {response.status_code}: {response.text}"
                    logger.warning(f"Attempt {attempt + 1} failed: {error_msg}")
                    
                    if attempt < self.config.max_retries - 1:
                        delay = self.config.retry_delay * (2 ** attempt)
                        logger.info(f"Retrying in {delay}s...")
                        time.sleep(delay)
                    else:
                        return {
                            'success': False,
                            'error': error_msg,
                            'metadata': {}
                        }
                        
            except requests.exceptions.Timeout:
                error_msg = f"Request timeout after {self.config.timeout}s"
                logger.warning(f"Attempt {attempt + 1} failed: {error_msg}")
                
                if attempt < self.config.max_retries - 1:
                    delay = self.config.retry_delay * (2 ** attempt)
                    logger.info(f"Retrying in {delay}s...")
                    time.sleep(delay)
                else:
                    return {
                        'success': False,
                        'error': error_msg,
                        'metadata': {}
                    }
                    
            except requests.exceptions.RequestException as e:
                error_msg = f"Request failed: {str(e)}"
                logger.error(f"Attempt {attempt + 1} failed: {error_msg}")
                
                if attempt < self.config.max_retries - 1:
                    delay = self.config.retry_delay * (2 ** attempt)
                    logger.info(f"Retrying in {delay}s...")
                    time.sleep(delay)
                else:
                    return {
                        'success': False,
                        'error': error_msg,
                        'metadata': {}
                    }
            
            except Exception as e:
                error_msg = f"Unexpected error: {str(e)}"
                logger.error(f"Attempt {attempt + 1} failed: {error_msg}")
                return {
                    'success': False,
                    'error': error_msg,
                    'metadata': {}
                }
        
        # Should never reach here, but safety net
        return {
            'success': False,
            'error': 'All retry attempts exhausted',
            'metadata': {}
        }


# Convenience function for quick usage
def create_client(model: str = "qwen2.5:14b-instruct-q4_0") -> OllamaClient:
    """
    Factory function to create configured Ollama client
    
    Args:
        model: Model name to use
        
    Returns:
        Configured OllamaClient instance
    """
    config = LLMConfig(model=model)
    return OllamaClient(config)


if __name__ == "__main__":
    # Basic test
    print("Testing Ollama Client...")
    client = create_client()
    
    if client.health_check():
        print("✓ Ollama is running")
        
        result = client.generate(
            prompt="What is 2+2?",
            system_prompt="You are a helpful assistant. Answer concisely."
        )
        
        if result['success']:
            print(f"✓ Generation successful")
            print(f"Response: {result['response']}")
            print(f"Time: {result['metadata']['elapsed_time']:.2f}s")
        else:
            print(f"✗ Generation failed: {result['error']}")
    else:
        print("✗ Ollama is not running or model not found")
        print("Run: ollama serve")
        print(f"Then: ollama pull llama3.1:8b-instruct-q4_0")