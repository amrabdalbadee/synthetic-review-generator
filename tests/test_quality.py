"""
Unit tests for Quality Guardrails
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import unittest
from src.guardrails.quality import QualityGuardrails, QualityScore


class TestQualityGuardrails(unittest.TestCase):
    """Test quality guardrails functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.config = {
            'quality_thresholds': {
                'min_vocabulary_diversity': 0.3,
                'max_semantic_similarity': 0.85,
                'min_review_length_chars': 50,
                'max_review_length_chars': 2000,
                'required_domain_keywords_ratio': 0.1,
                'sentiment_rating_alignment': 0.7,
                'max_repetition_ratio': 0.15
            }
        }
        self.domain_keywords = {
            'general': ['software', 'tool', 'platform', 'feature', 'integration'],
            'technical': ['code', 'API', 'deployment', 'performance'],
            'business': ['pricing', 'support', 'enterprise']
        }
        self.guardrails = QualityGuardrails(self.config, self.domain_keywords)
    
    def test_vocabulary_diversity_high(self):
        """Test high vocabulary diversity text"""
        text = "This software tool offers amazing features including great API integration and excellent performance monitoring capabilities."
        diversity = self.guardrails.calculate_vocabulary_diversity(text)
        self.assertGreater(diversity, 0.5)
    
    def test_vocabulary_diversity_low(self):
        """Test low vocabulary diversity (repetitive) text"""
        text = "good good good good good good good good good good software software software"
        diversity = self.guardrails.calculate_vocabulary_diversity(text)
        self.assertLess(diversity, 0.3)
    
    def test_sentiment_positive(self):
        """Test positive sentiment detection"""
        text = "I love this amazing tool! It's excellent and fantastic for our team."
        sentiment, _ = self.guardrails.calculate_sentiment(text)
        self.assertEqual(sentiment, 'positive')
    
    def test_sentiment_negative(self):
        """Test negative sentiment detection"""
        text = "Terrible software, buggy and frustrating. I hate using this awful tool."
        sentiment, _ = self.guardrails.calculate_sentiment(text)
        self.assertEqual(sentiment, 'negative')
    
    def test_sentiment_neutral(self):
        """Test neutral sentiment detection"""
        text = "This tool works. It does what it says. Nothing special about it."
        sentiment, _ = self.guardrails.calculate_sentiment(text)
        self.assertEqual(sentiment, 'neutral')
    
    def test_domain_relevance_high(self):
        """Test high domain relevance"""
        text = "The software platform offers excellent API integration with great code performance for deployment workflows."
        relevance = self.guardrails.calculate_domain_relevance(text)
        self.assertGreater(relevance, 0.1)
    
    def test_domain_relevance_low(self):
        """Test low domain relevance (off-topic)"""
        text = "I went to the grocery store yesterday and bought some apples and oranges for my family."
        relevance = self.guardrails.calculate_domain_relevance(text)
        self.assertEqual(relevance, 0.0)
    
    def test_length_compliance(self):
        """Test length compliance checking"""
        short_text = "Too short"  # 9 chars, min is 50, so score = 9/50 = 0.18
        long_text = "x" * 3000   # 3000 chars, max is 2000, so score = 2000/3000 = 0.67
        good_text = "This is a properly sized review that discusses the software tool in appropriate detail and covers multiple aspects of the product experience."
        
        short_compliant = self.guardrails.calculate_length_compliance(short_text)
        long_compliant = self.guardrails.calculate_length_compliance(long_text)
        good_compliant = self.guardrails.calculate_length_compliance(good_text)
        
        # Short text gets partial score based on how close to minimum
        self.assertLess(short_compliant, 1.0)
        # Long text gets partial score based on how close to maximum  
        self.assertLess(long_compliant, 1.0)
        # Good text should get full score
        self.assertEqual(good_compliant, 1.0)
    
    def test_repetition_detection(self):
        """Test repetition detection"""
        repetitive = "The software is good. The software is good. The software is good. The software is good."
        non_repetitive = "This tool offers great features. The API integration works seamlessly. Performance is excellent."
        
        rep_score = self.guardrails.calculate_repetition_score(repetitive)
        non_rep_score = self.guardrails.calculate_repetition_score(non_repetitive)
        
        self.assertGreater(rep_score, 0.15)  # High repetition
        self.assertLess(non_rep_score, 0.15)  # Low repetition
    
    def test_validate_review_passes(self):
        """Test full validation for a good review"""
        good_review = """
        This software platform has been a game-changer for our development team. 
        The API integration is seamless and the performance monitoring tools are excellent.
        Documentation is comprehensive and support team is responsive. 
        Highly recommend for any enterprise deployment needs.
        """
        score = self.guardrails.validate_review(good_review, rating=5)
        # Good reviews should generally pass
        self.assertGreater(score.overall_score, 0.5)
    
    def test_validate_review_fails_short(self):
        """Test validation fails for too-short review"""
        short_review = "Good tool."
        score = self.guardrails.validate_review(short_review, rating=4)
        self.assertFalse(score.passed)
        self.assertIn('length', score.rejection_reasons[0].lower())


class TestSentimentRatingAlignment(unittest.TestCase):
    """Test sentiment-rating alignment"""
    
    def setUp(self):
        self.config = {'quality_thresholds': {'sentiment_rating_alignment': 0.7}}
        self.domain_keywords = {'general': ['software']}
        self.guardrails = QualityGuardrails(self.config, self.domain_keywords)
    
    def test_positive_rating_positive_sentiment(self):
        """5-star rating should align with positive sentiment"""
        text = "Amazing software! Absolutely love it!"
        alignment = self.guardrails.calculate_sentiment_alignment(text, 5)
        self.assertGreater(alignment, 0.5)
    
    def test_negative_rating_negative_sentiment(self):
        """1-star rating should align with negative sentiment"""
        text = "Terrible product, completely disappointing and buggy."
        alignment = self.guardrails.calculate_sentiment_alignment(text, 1)
        self.assertGreater(alignment, 0.5)
    
    def test_misaligned_positive_rating_negative_text(self):
        """5-star rating with negative text should not align well"""
        text = "Awful, terrible, worst software I've ever used, hate it."
        alignment = self.guardrails.calculate_sentiment_alignment(text, 5)
        self.assertLess(alignment, 0.5)


if __name__ == '__main__':
    unittest.main()
