"""
Comparison Module
Compares synthetic reviews against real reviews to measure realism
"""

import logging
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from collections import Counter
import string
import math

logger = logging.getLogger(__name__)


@dataclass
class ComparisonMetrics:
    """Metrics comparing synthetic and real review datasets"""
    # Vocabulary metrics
    synthetic_vocab_size: int = 0
    real_vocab_size: int = 0
    vocab_overlap: float = 0.0
    synthetic_unique_words: int = 0
    real_unique_words: int = 0
    shared_words: int = 0
    
    # Length metrics
    synthetic_avg_length: float = 0.0
    real_avg_length: float = 0.0
    length_difference: float = 0.0
    
    # Sentiment metrics
    synthetic_sentiment_dist: Dict[str, float] = field(default_factory=dict)
    real_sentiment_dist: Dict[str, float] = field(default_factory=dict)
    sentiment_similarity: float = 0.0
    
    # Rating metrics
    synthetic_rating_dist: Dict[int, float] = field(default_factory=dict)
    real_rating_dist: Dict[int, float] = field(default_factory=dict)
    rating_similarity: float = 0.0
    
    # N-gram metrics
    bigram_overlap: float = 0.0
    trigram_overlap: float = 0.0
    
    # Overall realism score
    realism_score: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'vocabulary': {
                'synthetic_vocab_size': self.synthetic_vocab_size,
                'real_vocab_size': self.real_vocab_size,
                'vocab_overlap': round(self.vocab_overlap, 3),
                'synthetic_unique_words': self.synthetic_unique_words,
                'real_unique_words': self.real_unique_words,
                'shared_words': self.shared_words
            },
            'length': {
                'synthetic_avg_length': round(self.synthetic_avg_length, 1),
                'real_avg_length': round(self.real_avg_length, 1),
                'length_difference': round(self.length_difference, 1)
            },
            'sentiment': {
                'synthetic_distribution': {k: round(v, 3) for k, v in self.synthetic_sentiment_dist.items()},
                'real_distribution': {k: round(v, 3) for k, v in self.real_sentiment_dist.items()},
                'similarity': round(self.sentiment_similarity, 3)
            },
            'rating': {
                'synthetic_distribution': {k: round(v, 3) for k, v in self.synthetic_rating_dist.items()},
                'real_distribution': {k: round(v, 3) for k, v in self.real_rating_dist.items()},
                'similarity': round(self.rating_similarity, 3)
            },
            'ngrams': {
                'bigram_overlap': round(self.bigram_overlap, 3),
                'trigram_overlap': round(self.trigram_overlap, 3)
            },
            'realism_score': round(self.realism_score, 3)
        }


class ReviewComparator:
    """
    Compares synthetic reviews against real reviews
    """
    
    POSITIVE_WORDS = {
        'love', 'excellent', 'amazing', 'fantastic', 'wonderful', 'great', 'best',
        'awesome', 'brilliant', 'perfect', 'outstanding', 'superb', 'exceptional',
        'impressive', 'remarkable', 'incredible', 'highly', 'recommend', 'favorite',
        'seamless', 'intuitive', 'efficient', 'powerful', 'reliable', 'fast'
    }
    
    NEGATIVE_WORDS = {
        'hate', 'terrible', 'awful', 'horrible', 'worst', 'bad', 'poor', 'disappointing',
        'frustrating', 'annoying', 'useless', 'broken', 'buggy', 'slow', 'confusing',
        'complicated', 'expensive', 'overpriced', 'unreliable', 'crashes', 'error'
    }
    
    def __init__(self):
        pass
    
    def _tokenize(self, text: str) -> List[str]:
        """Simple word tokenization"""
        text = text.lower()
        text = text.translate(str.maketrans('', '', string.punctuation))
        words = text.split()
        return [w for w in words if len(w) > 1]
    
    def _get_ngrams(self, words: List[str], n: int) -> List[tuple]:
        """Get n-grams from word list"""
        return [tuple(words[i:i+n]) for i in range(len(words) - n + 1)]
    
    def _calculate_sentiment(self, text: str) -> str:
        """Calculate sentiment of text"""
        words = set(self._tokenize(text))
        positive_count = len(words & self.POSITIVE_WORDS)
        negative_count = len(words & self.NEGATIVE_WORDS)
        
        if positive_count > negative_count + 1:
            return 'positive'
        elif negative_count > positive_count + 1:
            return 'negative'
        return 'neutral'
    
    def _cosine_similarity(self, dist1: Dict, dist2: Dict) -> float:
        """Calculate cosine similarity between two distributions"""
        all_keys = set(dist1.keys()) | set(dist2.keys())
        
        dot_product = sum(dist1.get(k, 0) * dist2.get(k, 0) for k in all_keys)
        norm1 = math.sqrt(sum(v ** 2 for v in dist1.values()))
        norm2 = math.sqrt(sum(v ** 2 for v in dist2.values()))
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return dot_product / (norm1 * norm2)
    
    def compare(
        self, 
        synthetic_reviews: List[Dict[str, Any]], 
        real_reviews: List[Dict[str, Any]]
    ) -> ComparisonMetrics:
        """
        Compare synthetic reviews against real reviews
        """
        metrics = ComparisonMetrics()
        
        if not synthetic_reviews or not real_reviews:
            logger.warning("Empty review lists provided for comparison")
            return metrics
        
        # Extract texts
        synthetic_texts = [r.get('text', '') for r in synthetic_reviews]
        real_texts = [r.get('text', r.get('review_text', '')) for r in real_reviews]
        
        # Vocabulary analysis
        synthetic_words = []
        real_words = []
        
        for text in synthetic_texts:
            synthetic_words.extend(self._tokenize(text))
        for text in real_texts:
            real_words.extend(self._tokenize(text))
        
        synthetic_vocab = set(synthetic_words)
        real_vocab = set(real_words)
        
        metrics.synthetic_vocab_size = len(synthetic_vocab)
        metrics.real_vocab_size = len(real_vocab)
        metrics.shared_words = len(synthetic_vocab & real_vocab)
        metrics.synthetic_unique_words = len(synthetic_vocab - real_vocab)
        metrics.real_unique_words = len(real_vocab - synthetic_vocab)
        
        union_size = len(synthetic_vocab | real_vocab)
        metrics.vocab_overlap = metrics.shared_words / union_size if union_size > 0 else 0
        
        # Length analysis
        synthetic_lengths = [len(t) for t in synthetic_texts]
        real_lengths = [len(t) for t in real_texts]
        
        metrics.synthetic_avg_length = sum(synthetic_lengths) / len(synthetic_lengths) if synthetic_lengths else 0
        metrics.real_avg_length = sum(real_lengths) / len(real_lengths) if real_lengths else 0
        metrics.length_difference = abs(metrics.synthetic_avg_length - metrics.real_avg_length)
        
        # Sentiment analysis
        synthetic_sentiments = Counter(self._calculate_sentiment(t) for t in synthetic_texts)
        real_sentiments = Counter(self._calculate_sentiment(t) for t in real_texts)
        
        total_synthetic = sum(synthetic_sentiments.values())
        total_real = sum(real_sentiments.values())
        
        metrics.synthetic_sentiment_dist = {k: v/total_synthetic for k, v in synthetic_sentiments.items()}
        metrics.real_sentiment_dist = {k: v/total_real for k, v in real_sentiments.items()}
        metrics.sentiment_similarity = self._cosine_similarity(
            metrics.synthetic_sentiment_dist, 
            metrics.real_sentiment_dist
        )
        
        # Rating analysis
        synthetic_ratings = Counter(r.get('rating', 0) for r in synthetic_reviews)
        real_ratings = Counter(r.get('rating', 0) for r in real_reviews)
        
        total_synthetic_ratings = sum(synthetic_ratings.values())
        total_real_ratings = sum(real_ratings.values())
        
        metrics.synthetic_rating_dist = {k: v/total_synthetic_ratings for k, v in synthetic_ratings.items()} if total_synthetic_ratings else {}
        metrics.real_rating_dist = {k: v/total_real_ratings for k, v in real_ratings.items()} if total_real_ratings else {}
        metrics.rating_similarity = self._cosine_similarity(
            metrics.synthetic_rating_dist,
            metrics.real_rating_dist
        )
        
        # N-gram analysis
        synthetic_bigrams = set()
        synthetic_trigrams = set()
        real_bigrams = set()
        real_trigrams = set()
        
        for text in synthetic_texts:
            words = self._tokenize(text)
            synthetic_bigrams.update(self._get_ngrams(words, 2))
            synthetic_trigrams.update(self._get_ngrams(words, 3))
        
        for text in real_texts:
            words = self._tokenize(text)
            real_bigrams.update(self._get_ngrams(words, 2))
            real_trigrams.update(self._get_ngrams(words, 3))
        
        bigram_union = len(synthetic_bigrams | real_bigrams)
        trigram_union = len(synthetic_trigrams | real_trigrams)
        
        metrics.bigram_overlap = len(synthetic_bigrams & real_bigrams) / bigram_union if bigram_union else 0
        metrics.trigram_overlap = len(synthetic_trigrams & real_trigrams) / trigram_union if trigram_union else 0
        
        # Calculate overall realism score
        # Weighted combination of metrics
        length_score = 1.0 - min(metrics.length_difference / 500, 1.0)  # Penalize large differences
        
        metrics.realism_score = (
            metrics.vocab_overlap * 0.25 +
            metrics.sentiment_similarity * 0.20 +
            metrics.rating_similarity * 0.20 +
            length_score * 0.15 +
            metrics.bigram_overlap * 0.10 +
            metrics.trigram_overlap * 0.10
        )
        
        return metrics
    
    def generate_comparison_report(
        self, 
        metrics: ComparisonMetrics,
        synthetic_count: int,
        real_count: int
    ) -> str:
        """Generate a text report of the comparison"""
        lines = [
            "# Synthetic vs Real Review Comparison Report",
            "",
            "## Dataset Summary",
            f"- Synthetic reviews: {synthetic_count}",
            f"- Real reviews: {real_count}",
            "",
            "## Vocabulary Analysis",
            f"- Synthetic vocabulary size: {metrics.synthetic_vocab_size:,} unique words",
            f"- Real vocabulary size: {metrics.real_vocab_size:,} unique words",
            f"- Shared vocabulary: {metrics.shared_words:,} words ({metrics.vocab_overlap*100:.1f}% overlap)",
            f"- Synthetic-only words: {metrics.synthetic_unique_words:,}",
            f"- Real-only words: {metrics.real_unique_words:,}",
            "",
            "## Length Analysis",
            f"- Synthetic avg length: {metrics.synthetic_avg_length:.1f} characters",
            f"- Real avg length: {metrics.real_avg_length:.1f} characters",
            f"- Length difference: {metrics.length_difference:.1f} characters",
            "",
            "## Sentiment Distribution",
            "### Synthetic:",
        ]
        
        for sentiment, ratio in sorted(metrics.synthetic_sentiment_dist.items()):
            lines.append(f"  - {sentiment}: {ratio*100:.1f}%")
        
        lines.extend([
            "### Real:",
        ])
        
        for sentiment, ratio in sorted(metrics.real_sentiment_dist.items()):
            lines.append(f"  - {sentiment}: {ratio*100:.1f}%")
        
        lines.append(f"- Sentiment similarity: {metrics.sentiment_similarity*100:.1f}%")
        
        lines.extend([
            "",
            "## Rating Distribution",
            "### Synthetic:",
        ])
        
        for rating, ratio in sorted(metrics.synthetic_rating_dist.items()):
            lines.append(f"  - {rating} stars: {ratio*100:.1f}%")
        
        lines.append("### Real:")
        
        for rating, ratio in sorted(metrics.real_rating_dist.items()):
            lines.append(f"  - {rating} stars: {ratio*100:.1f}%")
        
        lines.append(f"- Rating similarity: {metrics.rating_similarity*100:.1f}%")
        
        lines.extend([
            "",
            "## N-gram Analysis",
            f"- Bigram overlap: {metrics.bigram_overlap*100:.1f}%",
            f"- Trigram overlap: {metrics.trigram_overlap*100:.1f}%",
            "",
            "## Overall Realism Score",
            f"**{metrics.realism_score*100:.1f}%**",
            "",
            self._get_realism_interpretation(metrics.realism_score)
        ])
        
        return "\n".join(lines)
    
    def _get_realism_interpretation(self, score: float) -> str:
        """Get interpretation of realism score"""
        if score >= 0.8:
            return "✓ Excellent: Synthetic reviews closely match real review patterns."
        elif score >= 0.6:
            return "✓ Good: Synthetic reviews show reasonable similarity to real reviews."
        elif score >= 0.4:
            return "⚠ Fair: Synthetic reviews have moderate similarity to real reviews. Consider adjusting generation parameters."
        else:
            return "✗ Poor: Synthetic reviews differ significantly from real reviews. Recommend reviewing generation strategy."
