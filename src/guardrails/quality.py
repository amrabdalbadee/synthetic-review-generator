"""
Quality Guardrails Module
Implements various quality checks for synthetic reviews:
- Diversity metrics
- Bias detection
- Domain realism validation
- Automated rejection logic
"""

import re
import logging
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Tuple
from collections import Counter
import string

logger = logging.getLogger(__name__)


@dataclass
class QualityScore:
    """Quality score for a single review"""
    vocabulary_diversity: float = 0.0
    semantic_uniqueness: float = 1.0
    sentiment_alignment: float = 0.0
    domain_relevance: float = 0.0
    length_compliance: float = 0.0
    repetition_score: float = 0.0
    overall_score: float = 0.0
    passed: bool = False
    rejection_reasons: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'vocabulary_diversity': round(self.vocabulary_diversity, 3),
            'semantic_uniqueness': round(self.semantic_uniqueness, 3),
            'sentiment_alignment': round(self.sentiment_alignment, 3),
            'domain_relevance': round(self.domain_relevance, 3),
            'length_compliance': round(self.length_compliance, 3),
            'repetition_score': round(self.repetition_score, 3),
            'overall_score': round(self.overall_score, 3),
            'passed': self.passed,
            'rejection_reasons': self.rejection_reasons
        }


@dataclass
class DatasetQualityMetrics:
    """Aggregate quality metrics for the entire dataset"""
    total_reviews: int = 0
    passed_reviews: int = 0
    rejected_reviews: int = 0
    avg_vocabulary_diversity: float = 0.0
    avg_semantic_uniqueness: float = 0.0
    avg_sentiment_alignment: float = 0.0
    avg_domain_relevance: float = 0.0
    avg_overall_score: float = 0.0
    rating_distribution: Dict[int, int] = field(default_factory=dict)
    sentiment_distribution: Dict[str, int] = field(default_factory=dict)
    rejection_reason_counts: Dict[str, int] = field(default_factory=dict)
    vocabulary_overlap_matrix: Optional[List[List[float]]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'total_reviews': self.total_reviews,
            'passed_reviews': self.passed_reviews,
            'rejected_reviews': self.rejected_reviews,
            'pass_rate': round(self.passed_reviews / max(self.total_reviews, 1), 3),
            'avg_vocabulary_diversity': round(self.avg_vocabulary_diversity, 3),
            'avg_semantic_uniqueness': round(self.avg_semantic_uniqueness, 3),
            'avg_sentiment_alignment': round(self.avg_sentiment_alignment, 3),
            'avg_domain_relevance': round(self.avg_domain_relevance, 3),
            'avg_overall_score': round(self.avg_overall_score, 3),
            'rating_distribution': self.rating_distribution,
            'sentiment_distribution': self.sentiment_distribution,
            'rejection_reason_counts': self.rejection_reason_counts
        }


class QualityGuardrails:
    """
    Quality guardrails for synthetic review validation
    """
    
    # Sentiment word lists
    POSITIVE_WORDS = {
        'love', 'excellent', 'amazing', 'fantastic', 'wonderful', 'great', 'best',
        'awesome', 'brilliant', 'perfect', 'outstanding', 'superb', 'exceptional',
        'impressive', 'remarkable', 'incredible', 'highly', 'recommend', 'favorite',
        'seamless', 'intuitive', 'efficient', 'powerful', 'reliable', 'fast',
        'easy', 'helpful', 'useful', 'valuable', 'solid', 'smooth', 'clean'
    }
    
    NEGATIVE_WORDS = {
        'hate', 'terrible', 'awful', 'horrible', 'worst', 'bad', 'poor', 'disappointing',
        'frustrating', 'annoying', 'useless', 'broken', 'buggy', 'slow', 'confusing',
        'complicated', 'expensive', 'overpriced', 'unreliable', 'crashes', 'error',
        'fail', 'failed', 'failing', 'lack', 'lacking', 'missing', 'difficult',
        'problem', 'issue', 'issues', 'problems', 'waste', 'avoid', 'regret'
    }
    
    def __init__(self, config: Dict[str, Any], domain_keywords: Dict[str, List[str]]):
        self.thresholds = config.get('quality_thresholds', {})
        self.domain_keywords = domain_keywords
        
        # Flatten domain keywords for easy lookup
        self.all_domain_keywords = set()
        for category_keywords in domain_keywords.values():
            self.all_domain_keywords.update(kw.lower() for kw in category_keywords)
        
        # Thresholds
        self.min_vocab_diversity = self.thresholds.get('min_vocabulary_diversity', 0.3)
        self.max_semantic_similarity = self.thresholds.get('max_semantic_similarity', 0.85)
        self.min_length = self.thresholds.get('min_review_length_chars', 50)
        self.max_length = self.thresholds.get('max_review_length_chars', 2000)
        self.domain_keyword_ratio = self.thresholds.get('required_domain_keywords_ratio', 0.1)
        self.sentiment_alignment_threshold = self.thresholds.get('sentiment_rating_alignment', 0.7)
        self.max_repetition = self.thresholds.get('max_repetition_ratio', 0.15)
        
        # Track all reviews for cross-review analysis
        self.all_reviews: List[str] = []
        self.all_review_words: List[set] = []
        
    def _tokenize(self, text: str) -> List[str]:
        """Simple word tokenization"""
        text = text.lower()
        # Remove punctuation
        text = text.translate(str.maketrans('', '', string.punctuation))
        words = text.split()
        return [w for w in words if len(w) > 1]
    
    def _get_ngrams(self, words: List[str], n: int) -> List[tuple]:
        """Get n-grams from word list"""
        return [tuple(words[i:i+n]) for i in range(len(words) - n + 1)]
    
    def calculate_vocabulary_diversity(self, text: str) -> float:
        """
        Calculate vocabulary diversity (type-token ratio)
        Higher is better (more diverse vocabulary)
        """
        words = self._tokenize(text)
        if not words:
            return 0.0
        unique_words = set(words)
        return len(unique_words) / len(words)
    
    def calculate_repetition_score(self, text: str) -> float:
        """
        Calculate repetition ratio based on repeated phrases
        Lower is better (less repetition)
        """
        words = self._tokenize(text)
        if len(words) < 4:
            return 0.0
        
        # Check for repeated bigrams and trigrams
        bigrams = self._get_ngrams(words, 2)
        trigrams = self._get_ngrams(words, 3)
        
        bigram_counts = Counter(bigrams)
        trigram_counts = Counter(trigrams)
        
        repeated_bigrams = sum(1 for count in bigram_counts.values() if count > 1)
        repeated_trigrams = sum(1 for count in trigram_counts.values() if count > 1)
        
        total_ngrams = len(bigrams) + len(trigrams)
        if total_ngrams == 0:
            return 0.0
            
        repetition_ratio = (repeated_bigrams + repeated_trigrams * 2) / total_ngrams
        return min(repetition_ratio, 1.0)
    
    def calculate_semantic_uniqueness(self, text: str, existing_reviews: List[str]) -> float:
        """
        Calculate how unique this review is compared to existing ones
        Uses Jaccard similarity on word sets
        Higher is better (more unique)
        """
        if not existing_reviews:
            return 1.0
        
        words = set(self._tokenize(text))
        if not words:
            return 0.0
        
        max_similarity = 0.0
        for existing in existing_reviews[-50:]:  # Check against last 50 reviews
            existing_words = set(self._tokenize(existing))
            if not existing_words:
                continue
            
            intersection = len(words & existing_words)
            union = len(words | existing_words)
            similarity = intersection / union if union > 0 else 0
            max_similarity = max(max_similarity, similarity)
        
        return 1.0 - max_similarity
    
    def calculate_sentiment(self, text: str) -> Tuple[str, float]:
        """
        Calculate sentiment of text
        Returns (sentiment_label, sentiment_score)
        Score: -1 (very negative) to +1 (very positive)
        """
        words = set(self._tokenize(text))
        
        positive_count = len(words & self.POSITIVE_WORDS)
        negative_count = len(words & self.NEGATIVE_WORDS)
        
        total_sentiment_words = positive_count + negative_count
        if total_sentiment_words == 0:
            return 'neutral', 0.0
        
        score = (positive_count - negative_count) / total_sentiment_words
        
        if score > 0.3:
            label = 'positive'
        elif score < -0.3:
            label = 'negative'
        else:
            label = 'neutral'
        
        return label, score
    
    def calculate_sentiment_alignment(self, text: str, rating: int) -> float:
        """
        Calculate how well sentiment aligns with the rating
        Higher is better (sentiment matches rating)
        """
        sentiment_label, sentiment_score = self.calculate_sentiment(text)
        
        # Expected sentiment based on rating
        if rating >= 4:
            expected = 'positive'
            expected_score_range = (0.2, 1.0)
        elif rating <= 2:
            expected = 'negative'
            expected_score_range = (-1.0, -0.2)
        else:
            expected = 'neutral'
            expected_score_range = (-0.3, 0.3)
        
        # Check alignment
        if sentiment_label == expected:
            return 1.0
        elif expected == 'neutral':
            # Neutral reviews can have slight bias
            return 0.7
        else:
            # Misalignment
            return 0.3
    
    def calculate_domain_relevance(self, text: str) -> float:
        """
        Calculate domain relevance based on keyword presence
        Higher is better (more relevant to domain)
        """
        words = set(self._tokenize(text))
        if not words:
            return 0.0
        
        domain_word_count = len(words & self.all_domain_keywords)
        return min(domain_word_count / len(words), 1.0)
    
    def calculate_length_compliance(self, text: str) -> float:
        """
        Calculate how well the length fits expected range
        Returns 1.0 if within range, lower if outside
        """
        length = len(text)
        
        if self.min_length <= length <= self.max_length:
            return 1.0
        elif length < self.min_length:
            return length / self.min_length
        else:
            return self.max_length / length
    
    def validate_review(
        self, 
        text: str, 
        rating: int,
        existing_reviews: Optional[List[str]] = None
    ) -> QualityScore:
        """
        Validate a single review and return quality score
        """
        if existing_reviews is None:
            existing_reviews = self.all_reviews
        
        score = QualityScore()
        
        # Basic validation
        if not text or not text.strip():
            score.rejection_reasons.append("Empty review")
            return score
        
        # Calculate individual metrics
        score.vocabulary_diversity = self.calculate_vocabulary_diversity(text)
        score.semantic_uniqueness = self.calculate_semantic_uniqueness(text, existing_reviews)
        score.sentiment_alignment = self.calculate_sentiment_alignment(text, rating)
        score.domain_relevance = self.calculate_domain_relevance(text)
        score.length_compliance = self.calculate_length_compliance(text)
        score.repetition_score = 1.0 - self.calculate_repetition_score(text)
        
        # Check thresholds and collect rejection reasons
        if score.vocabulary_diversity < self.min_vocab_diversity:
            score.rejection_reasons.append(f"Low vocabulary diversity: {score.vocabulary_diversity:.2f} < {self.min_vocab_diversity}")
        
        if score.semantic_uniqueness < (1 - self.max_semantic_similarity):
            score.rejection_reasons.append(f"Too similar to existing reviews: uniqueness {score.semantic_uniqueness:.2f}")
        
        if score.domain_relevance < self.domain_keyword_ratio:
            score.rejection_reasons.append(f"Low domain relevance: {score.domain_relevance:.2f} < {self.domain_keyword_ratio}")
        
        if score.length_compliance < 0.5:
            score.rejection_reasons.append(f"Length out of range: {len(text)} chars")
        
        if score.repetition_score < (1 - self.max_repetition):
            score.rejection_reasons.append(f"Too much repetition: {1 - score.repetition_score:.2f}")
        
        # Calculate overall score (weighted average)
        score.overall_score = (
            score.vocabulary_diversity * 0.2 +
            score.semantic_uniqueness * 0.25 +
            score.sentiment_alignment * 0.15 +
            score.domain_relevance * 0.2 +
            score.length_compliance * 0.1 +
            score.repetition_score * 0.1
        )
        
        # Determine pass/fail
        score.passed = len(score.rejection_reasons) == 0 and score.overall_score >= 0.5
        
        return score
    
    def add_review_to_corpus(self, text: str):
        """Add a validated review to the corpus for future comparison"""
        self.all_reviews.append(text)
        self.all_review_words.append(set(self._tokenize(text)))
    
    def calculate_dataset_metrics(
        self, 
        reviews: List[Dict[str, Any]]
    ) -> DatasetQualityMetrics:
        """
        Calculate aggregate metrics for the entire dataset
        """
        metrics = DatasetQualityMetrics()
        metrics.total_reviews = len(reviews)
        
        vocab_diversities = []
        semantic_uniquenesses = []
        sentiment_alignments = []
        domain_relevances = []
        overall_scores = []
        
        for review in reviews:
            quality = review.get('quality_score', {})
            
            if quality.get('passed', False):
                metrics.passed_reviews += 1
            else:
                metrics.rejected_reviews += 1
                for reason in quality.get('rejection_reasons', []):
                    reason_key = reason.split(':')[0]
                    metrics.rejection_reason_counts[reason_key] = \
                        metrics.rejection_reason_counts.get(reason_key, 0) + 1
            
            vocab_diversities.append(quality.get('vocabulary_diversity', 0))
            semantic_uniquenesses.append(quality.get('semantic_uniqueness', 0))
            sentiment_alignments.append(quality.get('sentiment_alignment', 0))
            domain_relevances.append(quality.get('domain_relevance', 0))
            overall_scores.append(quality.get('overall_score', 0))
            
            # Rating distribution
            rating = review.get('rating', 0)
            metrics.rating_distribution[rating] = \
                metrics.rating_distribution.get(rating, 0) + 1
            
            # Sentiment distribution
            text = review.get('text', '')
            sentiment, _ = self.calculate_sentiment(text)
            metrics.sentiment_distribution[sentiment] = \
                metrics.sentiment_distribution.get(sentiment, 0) + 1
        
        # Calculate averages
        if reviews:
            metrics.avg_vocabulary_diversity = sum(vocab_diversities) / len(vocab_diversities)
            metrics.avg_semantic_uniqueness = sum(semantic_uniquenesses) / len(semantic_uniquenesses)
            metrics.avg_sentiment_alignment = sum(sentiment_alignments) / len(sentiment_alignments)
            metrics.avg_domain_relevance = sum(domain_relevances) / len(domain_relevances)
            metrics.avg_overall_score = sum(overall_scores) / len(overall_scores)
        
        return metrics
    
    def calculate_vocabulary_overlap(self, reviews: List[str], sample_size: int = 50) -> List[List[float]]:
        """
        Calculate pairwise vocabulary overlap between reviews
        Returns a sample overlap matrix for analysis
        """
        sample = reviews[:sample_size] if len(reviews) > sample_size else reviews
        n = len(sample)
        matrix = [[0.0] * n for _ in range(n)]
        
        word_sets = [set(self._tokenize(r)) for r in sample]
        
        for i in range(n):
            for j in range(n):
                if i == j:
                    matrix[i][j] = 1.0
                elif word_sets[i] and word_sets[j]:
                    intersection = len(word_sets[i] & word_sets[j])
                    union = len(word_sets[i] | word_sets[j])
                    matrix[i][j] = intersection / union if union > 0 else 0
        
        return matrix
    
    def detect_bias(self, reviews: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Detect potential biases in the generated dataset
        """
        biases = {
            'sentiment_skew': None,
            'rating_bias': None,
            'length_bias': None,
            'vocabulary_concentration': None,
            'issues': []
        }
        
        if not reviews:
            return biases
        
        # Sentiment analysis
        sentiments = {'positive': 0, 'negative': 0, 'neutral': 0}
        for review in reviews:
            sentiment, _ = self.calculate_sentiment(review.get('text', ''))
            sentiments[sentiment] += 1
        
        total = sum(sentiments.values())
        if total > 0:
            sentiment_ratios = {k: v/total for k, v in sentiments.items()}
            biases['sentiment_skew'] = sentiment_ratios
            
            # Check for extreme skew
            if sentiment_ratios['positive'] > 0.7:
                biases['issues'].append("Excessive positive sentiment bias")
            elif sentiment_ratios['negative'] > 0.5:
                biases['issues'].append("Excessive negative sentiment bias")
        
        # Rating distribution analysis
        ratings = [r.get('rating', 0) for r in reviews]
        if ratings:
            avg_rating = sum(ratings) / len(ratings)
            biases['rating_bias'] = {
                'average': avg_rating,
                'distribution': Counter(ratings)
            }
            
            if avg_rating > 4.2:
                biases['issues'].append(f"High average rating ({avg_rating:.1f}) suggests unrealistic positivity")
            elif avg_rating < 2.5:
                biases['issues'].append(f"Low average rating ({avg_rating:.1f}) suggests unrealistic negativity")
        
        # Length analysis
        lengths = [len(r.get('text', '')) for r in reviews]
        if lengths:
            avg_length = sum(lengths) / len(lengths)
            biases['length_bias'] = {
                'average': avg_length,
                'min': min(lengths),
                'max': max(lengths),
                'std': (sum((l - avg_length) ** 2 for l in lengths) / len(lengths)) ** 0.5
            }
        
        # Vocabulary concentration
        all_words = []
        for review in reviews:
            all_words.extend(self._tokenize(review.get('text', '')))
        
        if all_words:
            word_freq = Counter(all_words)
            top_10_coverage = sum(c for _, c in word_freq.most_common(10)) / len(all_words)
            biases['vocabulary_concentration'] = {
                'unique_words': len(word_freq),
                'total_words': len(all_words),
                'top_10_coverage': top_10_coverage
            }
            
            if top_10_coverage > 0.4:
                biases['issues'].append("High vocabulary concentration (repetitive word usage)")
        
        return biases
