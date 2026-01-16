"""
Synthetic Review Generator
Main module for generating synthetic reviews using LLMs
"""

import random
import logging
import time
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from datetime import datetime
import json

from ..providers import ProviderManager, GenerationResult
from ..guardrails import QualityGuardrails, QualityScore

logger = logging.getLogger(__name__)


@dataclass
class GeneratedReview:
    """A generated synthetic review"""
    id: str
    product_name: str
    product_category: str
    rating: int
    text: str
    persona_id: str
    persona_name: str
    model: str
    provider: str
    generation_time: float
    quality_score: Optional[Dict[str, Any]] = None
    timestamp: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'product_name': self.product_name,
            'product_category': self.product_category,
            'rating': self.rating,
            'text': self.text,
            'persona_id': self.persona_id,
            'persona_name': self.persona_name,
            'model': self.model,
            'provider': self.provider,
            'generation_time': round(self.generation_time, 3),
            'quality_score': self.quality_score,
            'timestamp': self.timestamp,
            'metadata': self.metadata
        }


class ReviewGenerator:
    """
    Main class for generating synthetic reviews
    """
    
    def __init__(
        self, 
        config: Dict[str, Any],
        provider_manager: ProviderManager,
        guardrails: QualityGuardrails
    ):
        self.config = config
        self.provider_manager = provider_manager
        self.guardrails = guardrails
        
        # Parse configuration
        self.products = config.get('products', [])
        self.personas = config.get('personas', [])
        self.rating_dist = config.get('rating_distribution', {})
        self.review_chars = config.get('review_characteristics', {})
        
        # Generation settings
        gen_config = config.get('generation', {})
        self.target_samples = gen_config.get('target_samples', 350)
        self.max_retries = gen_config.get('max_retries_per_sample', 3)
        self.batch_size = gen_config.get('batch_size', 10)
        
        # Statistics
        self.stats = {
            'total_generated': 0,
            'total_accepted': 0,
            'total_rejected': 0,
            'retries': 0,
            'total_time': 0.0,
            'by_model': {},
            'by_persona': {},
            'by_product': {},
            'by_rating': {}
        }
        
        # Review counter for IDs
        self._review_counter = 0
        
    def _select_rating(self) -> int:
        """Select a rating based on configured distribution"""
        ratings = list(self.rating_dist.keys())
        weights = list(self.rating_dist.values())
        return random.choices(ratings, weights=weights)[0]
    
    def _select_persona(self) -> Dict[str, Any]:
        """Select a persona based on configured weights"""
        weights = [p.get('weight', 1.0/len(self.personas)) for p in self.personas]
        return random.choices(self.personas, weights=weights)[0]
    
    def _select_product(self) -> Dict[str, Any]:
        """Select a random product"""
        return random.choice(self.products)
    
    def _select_length_category(self) -> str:
        """Select review length category based on weights"""
        length_config = self.review_chars.get('length', {})
        categories = list(length_config.keys())
        weights = [length_config[c].get('weight', 0.33) for c in categories]
        return random.choices(categories, weights=weights)[0]
    
    def _build_prompt(
        self,
        product: Dict[str, Any],
        persona: Dict[str, Any],
        rating: int,
        length_category: str
    ) -> str:
        """Build the prompt for review generation"""
        
        length_config = self.review_chars.get('length', {}).get(length_category, {})
        min_words = length_config.get('min_words', 50)
        max_words = length_config.get('max_words', 150)
        
        # Determine sentiment guidance based on rating
        if rating >= 4:
            sentiment_tone = "positive and enthusiastic"
            sentiment_focus = "strengths, benefits, and positive experiences"
        elif rating <= 2:
            sentiment_tone = "critical but constructive"
            sentiment_focus = "issues, frustrations, and areas for improvement"
        else:
            sentiment_tone = "balanced and neutral"
            sentiment_focus = "both pros and cons with a fair assessment"
        
        # Select aspects to cover
        aspects = self.review_chars.get('aspects_to_cover', [])
        selected_aspects = random.sample(aspects, min(3, len(aspects)))
        
        prompt = f"""Write a realistic product review for a developer tool.

PRODUCT INFORMATION:
- Name: {product['name']}
- Category: {product['category']}
- Description: {product['description']}
- Key Features: {', '.join(product.get('features', [])[:4])}
- Pricing: {product.get('price_tier', 'paid')}

REVIEWER PROFILE:
- Role: {persona['name']}
- Experience Level: {persona['experience_level']}
- Priorities: {', '.join(persona.get('priorities', [])[:3])}
- Communication Style: {persona['tone']}

REVIEW REQUIREMENTS:
- Rating: {rating} out of 5 stars
- Tone: {sentiment_tone}
- Focus on: {sentiment_focus}
- Touch on these aspects: {', '.join(selected_aspects)}
- Length: {min_words}-{max_words} words

IMPORTANT GUIDELINES:
- Write ONLY the review text, no headers or labels
- Be specific and mention product features by name
- Include realistic details a real user would mention
- Vary sentence structure and vocabulary
- Make it sound natural and authentic
- Do not start with "I" if possible
- Do not use phrases like "As a [role]" at the start

Generate the review now:"""

        return prompt
    
    def _parse_review_text(self, text: str) -> str:
        """Clean and parse the generated review text"""
        # Remove common prefixes
        prefixes_to_remove = [
            "Here is the review:",
            "Here's the review:",
            "Review:",
            "Here is a review:",
            "Here's a review:",
        ]
        
        text = text.strip()
        
        for prefix in prefixes_to_remove:
            if text.lower().startswith(prefix.lower()):
                text = text[len(prefix):].strip()
        
        # Remove quotes if the entire text is quoted
        if text.startswith('"') and text.endswith('"'):
            text = text[1:-1]
        
        # Remove markdown formatting
        text = text.replace('**', '').replace('*', '')
        
        return text.strip()
    
    def generate_review(
        self,
        product: Optional[Dict[str, Any]] = None,
        persona: Optional[Dict[str, Any]] = None,
        rating: Optional[int] = None,
        provider_name: Optional[str] = None,
        model_name: Optional[str] = None
    ) -> Optional[GeneratedReview]:
        """
        Generate a single synthetic review
        
        Returns None if generation fails after all retries
        """
        # Select parameters if not provided
        product = product or self._select_product()
        persona = persona or self._select_persona()
        rating = rating if rating is not None else self._select_rating()
        length_category = self._select_length_category()
        
        # Build prompt
        prompt = self._build_prompt(product, persona, rating, length_category)
        
        # Try generation with retries
        for attempt in range(self.max_retries):
            # Generate
            result = self.provider_manager.generate(
                prompt,
                provider_name=provider_name,
                model_name=model_name
            )
            
            if not result.success:
                logger.warning(f"Generation failed (attempt {attempt + 1}): {result.error}")
                self.stats['retries'] += 1
                continue
            
            # Parse and validate
            text = self._parse_review_text(result.text)
            
            # Quality check
            quality_score = self.guardrails.validate_review(text, rating)
            
            if quality_score.passed:
                # Accept review
                self._review_counter += 1
                review_id = f"syn_{self._review_counter:05d}"
                
                review = GeneratedReview(
                    id=review_id,
                    product_name=product['name'],
                    product_category=product['category'],
                    rating=rating,
                    text=text,
                    persona_id=persona['id'],
                    persona_name=persona['name'],
                    model=result.model,
                    provider=result.provider,
                    generation_time=result.generation_time,
                    quality_score=quality_score.to_dict(),
                    timestamp=datetime.now().isoformat(),
                    metadata={
                        'length_category': length_category,
                        'tokens_used': result.tokens_used,
                        'attempt': attempt + 1
                    }
                )
                
                # Update stats
                self._update_stats(review, quality_score)
                
                # Add to guardrails corpus
                self.guardrails.add_review_to_corpus(text)
                
                return review
            else:
                logger.debug(f"Review rejected (attempt {attempt + 1}): {quality_score.rejection_reasons}")
                self.stats['retries'] += 1
                self.stats['total_rejected'] += 1
        
        return None
    
    def _update_stats(self, review: GeneratedReview, quality: QualityScore):
        """Update generation statistics"""
        self.stats['total_generated'] += 1
        self.stats['total_accepted'] += 1
        self.stats['total_time'] += review.generation_time
        
        # By model
        model_key = f"{review.provider}:{review.model}"
        if model_key not in self.stats['by_model']:
            self.stats['by_model'][model_key] = {
                'count': 0, 'total_time': 0.0, 'avg_quality': 0.0
            }
        self.stats['by_model'][model_key]['count'] += 1
        self.stats['by_model'][model_key]['total_time'] += review.generation_time
        
        # By persona
        if review.persona_id not in self.stats['by_persona']:
            self.stats['by_persona'][review.persona_id] = 0
        self.stats['by_persona'][review.persona_id] += 1
        
        # By product
        if review.product_name not in self.stats['by_product']:
            self.stats['by_product'][review.product_name] = 0
        self.stats['by_product'][review.product_name] += 1
        
        # By rating
        if review.rating not in self.stats['by_rating']:
            self.stats['by_rating'][review.rating] = 0
        self.stats['by_rating'][review.rating] += 1
    
    def generate_batch(
        self,
        count: int,
        provider_name: Optional[str] = None,
        model_name: Optional[str] = None,
        progress_callback: Optional[callable] = None
    ) -> List[GeneratedReview]:
        """
        Generate a batch of reviews
        """
        reviews = []
        
        for i in range(count):
            review = self.generate_review(
                provider_name=provider_name,
                model_name=model_name
            )
            
            if review:
                reviews.append(review)
            
            if progress_callback:
                progress_callback(i + 1, count, len(reviews))
        
        return reviews
    
    def generate_dataset(
        self,
        use_multiple_models: bool = True,
        progress_callback: Optional[callable] = None
    ) -> List[GeneratedReview]:
        """
        Generate the full dataset according to configuration
        """
        reviews = []
        target = self.target_samples
        
        # Get available providers and models
        available_providers = self.provider_manager.get_available_providers()
        
        if not available_providers:
            logger.error("No providers available!")
            return reviews
        
        logger.info(f"Available providers: {available_providers}")
        logger.info(f"Target samples: {target}")
        
        # Distribute generation across providers/models if using multiple
        if use_multiple_models and len(available_providers) > 0:
            provider_configs = []
            
            for provider_name in available_providers:
                provider = self.provider_manager.get_provider(provider_name)
                if provider and provider.models:
                    for model_config in provider.models[:2]:  # Use top 2 models per provider
                        provider_configs.append((provider_name, model_config.name))
            
            if not provider_configs:
                # Fallback to any available
                provider_configs = [(available_providers[0], None)]
            
            # Distribute samples
            samples_per_config = target // len(provider_configs)
            remainder = target % len(provider_configs)
            
            for idx, (provider_name, model_name) in enumerate(provider_configs):
                count = samples_per_config + (1 if idx < remainder else 0)
                logger.info(f"Generating {count} reviews with {provider_name}:{model_name}")
                
                batch = self.generate_batch(
                    count,
                    provider_name=provider_name,
                    model_name=model_name,
                    progress_callback=progress_callback
                )
                reviews.extend(batch)
                
                logger.info(f"Generated {len(batch)} reviews with {provider_name}:{model_name}")
        else:
            # Use single provider
            reviews = self.generate_batch(
                target,
                progress_callback=progress_callback
            )
        
        logger.info(f"Total reviews generated: {len(reviews)}")
        logger.info(f"Generation stats: {json.dumps(self.stats, indent=2)}")
        
        return reviews
    
    def get_stats(self) -> Dict[str, Any]:
        """Get generation statistics"""
        stats = self.stats.copy()
        
        # Calculate averages
        if stats['total_accepted'] > 0:
            stats['avg_time_per_review'] = stats['total_time'] / stats['total_accepted']
        else:
            stats['avg_time_per_review'] = 0.0
        
        # Calculate model performance
        for model_key, model_stats in stats['by_model'].items():
            if model_stats['count'] > 0:
                model_stats['avg_time'] = model_stats['total_time'] / model_stats['count']
        
        stats['acceptance_rate'] = (
            stats['total_accepted'] / 
            max(stats['total_accepted'] + stats['total_rejected'], 1)
        )
        
        return stats
