"""
Anthropic LLM Provider Implementation
Supports Claude models via Anthropic API
"""

import os
import time
import logging
from typing import Optional, Dict, Any

from .base import BaseLLMProvider, GenerationResult, ModelConfig

logger = logging.getLogger(__name__)


class AnthropicProvider(BaseLLMProvider):
    """Anthropic provider for Claude models"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.api_key = os.getenv('ANTHROPIC_API_KEY')
        self._client = None
        
    @property
    def provider_name(self) -> str:
        return "anthropic"
    
    def _get_client(self):
        """Lazy initialization of Anthropic client"""
        if self._client is None:
            try:
                from anthropic import Anthropic
                self._client = Anthropic(api_key=self.api_key)
            except ImportError:
                logger.error("Anthropic package not installed. Run: pip install anthropic")
                return None
            except Exception as e:
                logger.error(f"Failed to initialize Anthropic client: {e}")
                return None
        return self._client
    
    def is_available(self) -> bool:
        """Check if Anthropic is configured and accessible"""
        if not self.enabled:
            return False
        if not self.api_key or self.api_key == 'your_anthropic_api_key_here':
            logger.info("Anthropic API key not configured")
            return False
        
        client = self._get_client()
        if client is None:
            return False
            
        try:
            # Quick test - just verify client initialization
            # Anthropic doesn't have a simple ping endpoint
            return True
        except Exception as e:
            logger.warning(f"Anthropic not available: {e}")
            return False
    
    def generate(self, prompt: str, model_config: Optional[ModelConfig] = None) -> GenerationResult:
        """Generate text using Anthropic Claude"""
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
                error="Anthropic client not initialized"
            )
        
        start_time = time.time()
        
        try:
            response = client.messages.create(
                model=model_config.name,
                max_tokens=model_config.max_tokens,
                messages=[
                    {"role": "user", "content": prompt}
                ],
                system="You are a helpful assistant that generates realistic product reviews. Generate only the review text without any additional commentary or formatting.",
                temperature=model_config.temperature,
                top_p=model_config.top_p
            )
            
            generation_time = time.time() - start_time
            text = response.content[0].text.strip()
            
            self._record_request(generation_time, True)
            
            return GenerationResult(
                text=text,
                model=model_config.name,
                provider=self.provider_name,
                generation_time=generation_time,
                tokens_used=response.usage.input_tokens + response.usage.output_tokens if response.usage else None,
                success=True,
                metadata={
                    "input_tokens": response.usage.input_tokens if response.usage else None,
                    "output_tokens": response.usage.output_tokens if response.usage else None,
                    "stop_reason": response.stop_reason
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
