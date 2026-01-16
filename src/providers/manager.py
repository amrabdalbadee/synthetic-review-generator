"""
LLM Provider Manager
Coordinates between different LLM providers and handles fallback logic
"""

import logging
from typing import Dict, Any, List, Optional

from .base import BaseLLMProvider, GenerationResult, ModelConfig
from .ollama_provider import OllamaProvider
from .openai_provider import OpenAIProvider
from .anthropic_provider import AnthropicProvider

logger = logging.getLogger(__name__)


class ProviderManager:
    """
    Manages multiple LLM providers and handles:
    - Provider initialization
    - Model selection
    - Fallback between providers
    - Statistics aggregation
    """
    
    PROVIDER_CLASSES = {
        'ollama': OllamaProvider,
        'openai': OpenAIProvider,
        'anthropic': AnthropicProvider
    }
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.providers: Dict[str, BaseLLMProvider] = {}
        self.primary_provider_name = config.get('primary', 'ollama')
        self.fallback_provider_name = config.get('fallback', 'ollama')
        
        self._initialize_providers()
        
    def _initialize_providers(self):
        """Initialize all configured providers"""
        for provider_name, provider_class in self.PROVIDER_CLASSES.items():
            if provider_name in self.config:
                provider_config = self.config[provider_name]
                try:
                    provider = provider_class(provider_config)
                    self.providers[provider_name] = provider
                    logger.info(f"Initialized provider: {provider_name} (enabled: {provider.enabled})")
                except Exception as e:
                    logger.error(f"Failed to initialize provider {provider_name}: {e}")
    
    def get_available_providers(self) -> List[str]:
        """Get list of providers that are currently available"""
        available = []
        for name, provider in self.providers.items():
            if provider.is_available():
                available.append(name)
        return available
    
    def get_provider(self, name: str) -> Optional[BaseLLMProvider]:
        """Get a specific provider by name"""
        return self.providers.get(name)
    
    def get_primary_provider(self) -> Optional[BaseLLMProvider]:
        """Get the primary provider if available"""
        provider = self.providers.get(self.primary_provider_name)
        if provider and provider.is_available():
            return provider
        return None
    
    def get_fallback_provider(self) -> Optional[BaseLLMProvider]:
        """Get the fallback provider if available"""
        provider = self.providers.get(self.fallback_provider_name)
        if provider and provider.is_available():
            return provider
        return None
    
    def get_any_available_provider(self) -> Optional[BaseLLMProvider]:
        """Get any available provider"""
        # Try primary first
        provider = self.get_primary_provider()
        if provider:
            return provider
            
        # Try fallback
        provider = self.get_fallback_provider()
        if provider:
            return provider
            
        # Try any available
        for provider in self.providers.values():
            if provider.is_available():
                return provider
                
        return None
    
    def generate(
        self, 
        prompt: str, 
        provider_name: Optional[str] = None,
        model_name: Optional[str] = None,
        use_fallback: bool = True
    ) -> GenerationResult:
        """
        Generate text using the specified or default provider
        
        Args:
            prompt: The prompt to generate from
            provider_name: Specific provider to use (optional)
            model_name: Specific model to use (optional)
            use_fallback: Whether to try fallback provider on failure
        """
        # Determine provider
        if provider_name:
            provider = self.get_provider(provider_name)
            if not provider or not provider.is_available():
                return GenerationResult(
                    text="",
                    model="unknown",
                    provider=provider_name,
                    generation_time=0,
                    success=False,
                    error=f"Provider {provider_name} is not available"
                )
        else:
            provider = self.get_any_available_provider()
            if not provider:
                return GenerationResult(
                    text="",
                    model="unknown",
                    provider="none",
                    generation_time=0,
                    success=False,
                    error="No providers available"
                )
        
        # Find model config if specific model requested
        model_config = None
        if model_name:
            for m in provider.models:
                if m.name == model_name:
                    model_config = m
                    break
        
        # Generate
        result = provider.generate_with_retry(prompt, model_config=model_config)
        
        # Try fallback if failed and enabled
        if not result.success and use_fallback:
            fallback = self.get_fallback_provider()
            if fallback and fallback.provider_name != provider.provider_name:
                logger.info(f"Falling back from {provider.provider_name} to {fallback.provider_name}")
                result = fallback.generate_with_retry(prompt)
        
        return result
    
    def generate_with_multiple_models(
        self, 
        prompt: str,
        providers_models: Optional[List[tuple]] = None
    ) -> List[GenerationResult]:
        """
        Generate using multiple models for diversity
        
        Args:
            prompt: The prompt to generate from
            providers_models: List of (provider_name, model_name) tuples
                            If None, uses first model from each available provider
        """
        results = []
        
        if providers_models is None:
            # Use first model from each available provider
            for provider in self.providers.values():
                if provider.is_available() and provider.models:
                    result = provider.generate_with_retry(prompt, model_config=provider.models[0])
                    results.append(result)
        else:
            for provider_name, model_name in providers_models:
                result = self.generate(
                    prompt, 
                    provider_name=provider_name, 
                    model_name=model_name,
                    use_fallback=False
                )
                results.append(result)
        
        return results
    
    def get_all_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get statistics from all providers"""
        stats = {}
        for name, provider in self.providers.items():
            stats[name] = provider.get_stats()
        return stats
    
    def get_configured_models(self) -> Dict[str, List[str]]:
        """Get all configured models per provider"""
        models = {}
        for name, provider in self.providers.items():
            models[name] = [m.name for m in provider.models]
        return models
    
    def status_report(self) -> str:
        """Generate a status report of all providers"""
        lines = ["LLM Provider Status:", "=" * 40]
        
        for name, provider in self.providers.items():
            available = provider.is_available()
            status = "✓ Available" if available else "✗ Unavailable"
            lines.append(f"\n{name.upper()}:")
            lines.append(f"  Status: {status}")
            lines.append(f"  Enabled: {provider.enabled}")
            lines.append(f"  Models: {[m.name for m in provider.models]}")
            
            if hasattr(provider, 'get_available_models') and available:
                actual_models = provider.get_available_models()
                lines.append(f"  Available Models: {actual_models}")
        
        lines.append("\n" + "=" * 40)
        lines.append(f"Primary: {self.primary_provider_name}")
        lines.append(f"Fallback: {self.fallback_provider_name}")
        
        return "\n".join(lines)
