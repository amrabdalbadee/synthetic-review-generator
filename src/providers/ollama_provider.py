"""
Ollama LLM Provider Implementation
Supports local LLM models via Ollama
"""

import os
import time
import logging
import httpx
from typing import Optional, Dict, Any

from .base import BaseLLMProvider, GenerationResult, ModelConfig

logger = logging.getLogger(__name__)


class OllamaProvider(BaseLLMProvider):
    """Ollama provider for local LLM inference"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.base_url = config.get('base_url', os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434'))
        self._available_models = None
        
    @property
    def provider_name(self) -> str:
        return "ollama"
    
    def is_available(self) -> bool:
        """Check if Ollama is running and accessible"""
        if not self.enabled:
            return False
        try:
            response = httpx.get(f"{self.base_url}/api/tags", timeout=5.0)
            return response.status_code == 200
        except Exception as e:
            logger.warning(f"Ollama not available: {e}")
            return False
    
    def get_available_models(self) -> list:
        """Get list of models available in Ollama"""
        if self._available_models is not None:
            return self._available_models
            
        try:
            response = httpx.get(f"{self.base_url}/api/tags", timeout=10.0)
            if response.status_code == 200:
                data = response.json()
                self._available_models = [m['name'].split(':')[0] for m in data.get('models', [])]
                return self._available_models
        except Exception as e:
            logger.error(f"Failed to get Ollama models: {e}")
        return []
    
    def pull_model(self, model_name: str) -> bool:
        """Pull a model if not available"""
        try:
            logger.info(f"Pulling model {model_name}...")
            response = httpx.post(
                f"{self.base_url}/api/pull",
                json={"name": model_name},
                timeout=600.0  # 10 minutes timeout for model download
            )
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Failed to pull model {model_name}: {e}")
            return False
    
    def generate(self, prompt: str, model_config: Optional[ModelConfig] = None) -> GenerationResult:
        """Generate text using Ollama"""
        if model_config is None:
            if not self.models:
                return GenerationResult(
                    text="",
                    model="unknown",
                    provider=self.provider_name,
                    generation_time=0,
                    success=False,
                    error="No models configured"
                )
            model_config = self.models[0]
        
        start_time = time.time()
        
        try:
            # Check if model is available, try to use it anyway
            available = self.get_available_models()
            model_name = model_config.name
            
            # Try exact match first, then partial match
            if model_name not in available:
                # Try partial match
                matches = [m for m in available if model_name in m or m in model_name]
                if matches:
                    model_name = matches[0]
                    logger.info(f"Using matched model: {model_name}")
            
            response = httpx.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": model_name,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": model_config.temperature,
                        "num_predict": model_config.max_tokens,
                        "top_p": model_config.top_p
                    }
                },
                timeout=120.0  # 2 minute timeout for generation
            )
            
            generation_time = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                text = data.get('response', '').strip()
                
                self._record_request(generation_time, True)
                
                return GenerationResult(
                    text=text,
                    model=model_name,
                    provider=self.provider_name,
                    generation_time=generation_time,
                    tokens_used=data.get('eval_count'),
                    success=True,
                    metadata={
                        "total_duration": data.get('total_duration'),
                        "load_duration": data.get('load_duration'),
                        "prompt_eval_count": data.get('prompt_eval_count')
                    }
                )
            else:
                error_msg = f"Ollama returned status {response.status_code}: {response.text}"
                self._record_request(generation_time, False)
                return GenerationResult(
                    text="",
                    model=model_config.name,
                    provider=self.provider_name,
                    generation_time=generation_time,
                    success=False,
                    error=error_msg
                )
                
        except httpx.TimeoutException:
            generation_time = time.time() - start_time
            self._record_request(generation_time, False)
            return GenerationResult(
                text="",
                model=model_config.name,
                provider=self.provider_name,
                generation_time=generation_time,
                success=False,
                error="Request timed out"
            )
        except Exception as e:
            generation_time = time.time() - start_time
            self._record_request(generation_time, False)
            return GenerationResult(
                text="",
                model=model_config.name,
                provider=self.provider_name,
                generation_time=generation_time,
                success=False,
                error=str(e)
            )
    
    def generate_batch(
        self, 
        prompts: list[str], 
        model_config: Optional[ModelConfig] = None
    ) -> list[GenerationResult]:
        """Generate multiple texts (sequential for Ollama)"""
        results = []
        for prompt in prompts:
            result = self.generate(prompt, model_config)
            results.append(result)
        return results
