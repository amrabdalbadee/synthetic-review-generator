"""
Base LLM Provider Abstract Class
Defines the interface for all LLM providers (Ollama, OpenAI, Anthropic)
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, Dict, Any, List
import time
import logging

logger = logging.getLogger(__name__)


@dataclass
class GenerationResult:
    """Result from an LLM generation request"""
    text: str
    model: str
    provider: str
    generation_time: float
    tokens_used: Optional[int] = None
    success: bool = True
    error: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class ModelConfig:
    """Configuration for a specific model"""
    name: str
    priority: int = 1
    temperature: float = 0.8
    max_tokens: int = 500
    top_p: float = 0.9
    

class BaseLLMProvider(ABC):
    """Abstract base class for LLM providers"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.enabled = config.get('enabled', False)
        self.models = self._parse_models(config.get('models', []))
        self._request_count = 0
        self._total_time = 0.0
        self._errors = 0
        
    def _parse_models(self, models_config: List[Dict]) -> List[ModelConfig]:
        """Parse model configurations"""
        models = []
        for m in models_config:
            models.append(ModelConfig(
                name=m['name'],
                priority=m.get('priority', 1),
                temperature=m.get('temperature', 0.8),
                max_tokens=m.get('max_tokens', 500),
                top_p=m.get('top_p', 0.9)
            ))
        # Sort by priority
        return sorted(models, key=lambda x: x.priority)
    
    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return the provider name"""
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """Check if the provider is available and configured"""
        pass
    
    @abstractmethod
    def generate(self, prompt: str, model_config: Optional[ModelConfig] = None) -> GenerationResult:
        """Generate text from a prompt"""
        pass
    
    def generate_with_retry(
        self, 
        prompt: str, 
        max_retries: int = 3,
        model_config: Optional[ModelConfig] = None
    ) -> GenerationResult:
        """Generate with automatic retry on failure"""
        last_error = None
        
        for attempt in range(max_retries):
            try:
                result = self.generate(prompt, model_config)
                if result.success:
                    return result
                last_error = result.error
            except Exception as e:
                last_error = str(e)
                logger.warning(f"Attempt {attempt + 1}/{max_retries} failed: {last_error}")
                time.sleep(1 * (attempt + 1))  # Exponential backoff
                
        return GenerationResult(
            text="",
            model=model_config.name if model_config else "unknown",
            provider=self.provider_name,
            generation_time=0,
            success=False,
            error=f"All {max_retries} attempts failed. Last error: {last_error}"
        )
    
    def get_stats(self) -> Dict[str, Any]:
        """Get provider statistics"""
        return {
            "provider": self.provider_name,
            "total_requests": self._request_count,
            "total_time": self._total_time,
            "avg_time": self._total_time / max(self._request_count, 1),
            "errors": self._errors,
            "success_rate": (self._request_count - self._errors) / max(self._request_count, 1)
        }
    
    def _record_request(self, generation_time: float, success: bool):
        """Record request statistics"""
        self._request_count += 1
        self._total_time += generation_time
        if not success:
            self._errors += 1
