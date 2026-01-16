"""
OpenAI LLM Provider Implementation
Supports GPT models via OpenAI API
"""

import os
import time
import logging
from typing import Optional, Dict, Any

from .base import BaseLLMProvider, GenerationResult, ModelConfig

logger = logging.getLogger(__name__)


class OpenAIProvider(BaseLLMProvider):
    """OpenAI provider for GPT models"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.api_key = os.getenv('OPENAI_API_KEY')
        self._client = None
        
    @property
    def provider_name(self) -> str:
        return "openai"
    
    def _get_client(self):
        """Lazy initialization of OpenAI client"""
        if self._client is None:
            try:
                from openai import OpenAI
                self._client = OpenAI(api_key=self.api_key)
            except ImportError:
                logger.error("OpenAI package not installed. Run: pip install openai")
                return None
            except Exception as e:
                logger.error(f"Failed to initialize OpenAI client: {e}")
                return None
        return self._client
    
    def is_available(self) -> bool:
        """Check if OpenAI is configured and accessible"""
        if not self.enabled:
            return False
        if not self.api_key or self.api_key == 'your_openai_api_key_here':
            logger.info("OpenAI API key not configured")
            return False
        
        client = self._get_client()
        if client is None:
            return False
            
        try:
            # Quick test to verify API key
            client.models.list()
            return True
        except Exception as e:
            logger.warning(f"OpenAI not available: {e}")
            return False
    
    def generate(self, prompt: str, model_config: Optional[ModelConfig] = None) -> GenerationResult:
        """Generate text using OpenAI"""
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
        
        client = self._get_client()
        if client is None:
            return GenerationResult(
                text="",
                model=model_config.name,
                provider=self.provider_name,
                generation_time=0,
                success=False,
                error="OpenAI client not initialized"
            )
        
        start_time = time.time()
        
        try:
            response = client.chat.completions.create(
                model=model_config.name,
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that generates realistic product reviews."},
                    {"role": "user", "content": prompt}
                ],
                temperature=model_config.temperature,
                max_tokens=model_config.max_tokens,
                top_p=model_config.top_p
            )
            
            generation_time = time.time() - start_time
            text = response.choices[0].message.content.strip()
            
            self._record_request(generation_time, True)
            
            return GenerationResult(
                text=text,
                model=model_config.name,
                provider=self.provider_name,
                generation_time=generation_time,
                tokens_used=response.usage.total_tokens if response.usage else None,
                success=True,
                metadata={
                    "prompt_tokens": response.usage.prompt_tokens if response.usage else None,
                    "completion_tokens": response.usage.completion_tokens if response.usage else None,
                    "finish_reason": response.choices[0].finish_reason
                }
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
        """Generate multiple texts"""
        results = []
        for prompt in prompts:
            result = self.generate(prompt, model_config)
            results.append(result)
        return results
