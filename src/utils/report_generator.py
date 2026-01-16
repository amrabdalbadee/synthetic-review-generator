"""
Report Generator
Creates quality reports in markdown format
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


class ReportGenerator:
    """
    Generates comprehensive quality reports for synthetic review datasets
    """
    
    def __init__(self, output_dir: str = "./reports"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def generate_quality_report(
        self,
        dataset_metrics: Dict[str, Any],
        generation_stats: Dict[str, Any],
        comparison_metrics: Optional[Dict[str, Any]] = None,
        bias_analysis: Optional[Dict[str, Any]] = None,
        config_summary: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Generate a comprehensive quality report
        Returns the markdown content
        """
        lines = [
            "# Synthetic Review Dataset Quality Report",
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "---",
            "",
            "## Executive Summary",
            ""
        ]
        
        # Summary stats
        total = dataset_metrics.get('total_reviews', 0)
        passed = dataset_metrics.get('passed_reviews', 0)
        pass_rate = dataset_metrics.get('pass_rate', 0)
        avg_score = dataset_metrics.get('avg_overall_score', 0)
        
        lines.extend([
            f"- **Total Reviews Generated**: {total}",
            f"- **Reviews Passing Quality Checks**: {passed} ({pass_rate*100:.1f}%)",
            f"- **Average Quality Score**: {avg_score*100:.1f}%",
        ])
        
        if comparison_metrics:
            realism = comparison_metrics.get('realism_score', 0)
            lines.append(f"- **Realism Score (vs Real Reviews)**: {realism*100:.1f}%")
        
        lines.extend(["", "---", ""])
        
        # Configuration summary
        if config_summary:
            lines.extend([
                "## Configuration",
                "",
                f"- Target samples: {config_summary.get('target_samples', 'N/A')}",
                f"- Products: {config_summary.get('products', 'N/A')}",
                f"- Personas: {config_summary.get('personas', 'N/A')}",
                f"- Models used: {config_summary.get('models', 'N/A')}",
                "",
                "---",
                ""
            ])
        
        # Generation statistics
        lines.extend([
            "## Generation Statistics",
            "",
            "### Overall Performance",
            "",
            f"- Total generation time: {generation_stats.get('total_time', 0):.1f} seconds",
            f"- Average time per review: {generation_stats.get('avg_time_per_review', 0):.2f} seconds",
            f"- Total retries: {generation_stats.get('retries', 0)}",
            f"- Acceptance rate: {generation_stats.get('acceptance_rate', 0)*100:.1f}%",
            ""
        ])
        
        # Model performance
        by_model = generation_stats.get('by_model', {})
        if by_model:
            lines.extend([
                "### Performance by Model",
                "",
                "| Model | Reviews | Total Time | Avg Time |",
                "|-------|---------|------------|----------|"
            ])
            
            for model_key, stats in by_model.items():
                count = stats.get('count', 0)
                total_time = stats.get('total_time', 0)
                avg_time = stats.get('avg_time', total_time / max(count, 1))
                lines.append(f"| {model_key} | {count} | {total_time:.1f}s | {avg_time:.2f}s |")
            
            lines.append("")
        
        # Distribution analysis
        lines.extend([
            "---",
            "",
            "## Quality Metrics",
            "",
            "### Score Distribution",
            "",
            f"- Vocabulary Diversity: {dataset_metrics.get('avg_vocabulary_diversity', 0)*100:.1f}%",
            f"- Semantic Uniqueness: {dataset_metrics.get('avg_semantic_uniqueness', 0)*100:.1f}%",
            f"- Sentiment Alignment: {dataset_metrics.get('avg_sentiment_alignment', 0)*100:.1f}%",
            f"- Domain Relevance: {dataset_metrics.get('avg_domain_relevance', 0)*100:.1f}%",
            ""
        ])
        
        # Rating distribution
        rating_dist = dataset_metrics.get('rating_distribution', {})
        if rating_dist:
            lines.extend([
                "### Rating Distribution",
                "",
                "| Rating | Count | Percentage |",
                "|--------|-------|------------|"
            ])
            
            total_ratings = sum(rating_dist.values())
            for rating in sorted(rating_dist.keys()):
                count = rating_dist[rating]
                pct = count / total_ratings * 100 if total_ratings > 0 else 0
                stars = "⭐" * rating
                lines.append(f"| {rating} {stars} | {count} | {pct:.1f}% |")
            
            lines.append("")
        
        # Sentiment distribution
        sentiment_dist = dataset_metrics.get('sentiment_distribution', {})
        if sentiment_dist:
            lines.extend([
                "### Sentiment Distribution",
                "",
                "| Sentiment | Count | Percentage |",
                "|-----------|-------|------------|"
            ])
            
            total_sentiments = sum(sentiment_dist.values())
            for sentiment in ['positive', 'neutral', 'negative']:
                if sentiment in sentiment_dist:
                    count = sentiment_dist[sentiment]
                    pct = count / total_sentiments * 100 if total_sentiments > 0 else 0
                    emoji = {"positive": "😊", "neutral": "😐", "negative": "😞"}[sentiment]
                    lines.append(f"| {sentiment.capitalize()} {emoji} | {count} | {pct:.1f}% |")
            
            lines.append("")
        
        # Rejection analysis
        rejection_counts = dataset_metrics.get('rejection_reason_counts', {})
        if rejection_counts:
            lines.extend([
                "### Rejection Reasons",
                "",
                "| Reason | Count |",
                "|--------|-------|"
            ])
            
            for reason, count in sorted(rejection_counts.items(), key=lambda x: -x[1]):
                lines.append(f"| {reason} | {count} |")
            
            lines.append("")
        
        # Bias analysis
        if bias_analysis:
            lines.extend([
                "---",
                "",
                "## Bias Analysis",
                ""
            ])
            
            issues = bias_analysis.get('issues', [])
            if issues:
                lines.append("### Detected Issues")
                lines.append("")
                for issue in issues:
                    lines.append(f"- ⚠️ {issue}")
                lines.append("")
            else:
                lines.append("✅ No significant biases detected.")
                lines.append("")
            
            # Sentiment skew
            sentiment_skew = bias_analysis.get('sentiment_skew', {})
            if sentiment_skew:
                lines.extend([
                    "### Sentiment Balance",
                    ""
                ])
                for sentiment, ratio in sentiment_skew.items():
                    bar_length = int(ratio * 20)
                    bar = "█" * bar_length + "░" * (20 - bar_length)
                    lines.append(f"- {sentiment.capitalize()}: {bar} {ratio*100:.1f}%")
                lines.append("")
        
        # Comparison with real reviews
        if comparison_metrics:
            lines.extend([
                "---",
                "",
                "## Comparison with Real Reviews",
                "",
            ])
            
            vocab = comparison_metrics.get('vocabulary', {})
            lines.extend([
                "### Vocabulary Analysis",
                "",
                f"- Synthetic vocabulary size: {vocab.get('synthetic_vocab_size', 0):,} words",
                f"- Real vocabulary size: {vocab.get('real_vocab_size', 0):,} words",
                f"- Vocabulary overlap: {vocab.get('vocab_overlap', 0)*100:.1f}%",
                f"- Shared words: {vocab.get('shared_words', 0):,}",
                ""
            ])
            
            length = comparison_metrics.get('length', {})
            lines.extend([
                "### Length Analysis",
                "",
                f"- Synthetic average length: {length.get('synthetic_avg_length', 0):.0f} characters",
                f"- Real average length: {length.get('real_avg_length', 0):.0f} characters",
                f"- Length difference: {length.get('length_difference', 0):.0f} characters",
                ""
            ])
            
            sentiment = comparison_metrics.get('sentiment', {})
            lines.extend([
                "### Sentiment Comparison",
                "",
                f"- Sentiment similarity: {sentiment.get('similarity', 0)*100:.1f}%",
                ""
            ])
            
            ngrams = comparison_metrics.get('ngrams', {})
            lines.extend([
                "### N-gram Analysis",
                "",
                f"- Bigram overlap: {ngrams.get('bigram_overlap', 0)*100:.1f}%",
                f"- Trigram overlap: {ngrams.get('trigram_overlap', 0)*100:.1f}%",
                ""
            ])
            
            # Overall realism
            realism = comparison_metrics.get('realism_score', 0)
            lines.extend([
                "### Overall Realism Score",
                "",
                f"**{realism*100:.1f}%**",
                ""
            ])
            
            # Interpretation
            if realism >= 0.8:
                lines.append("✅ Excellent: Synthetic reviews closely match real review patterns.")
            elif realism >= 0.6:
                lines.append("✅ Good: Synthetic reviews show reasonable similarity to real reviews.")
            elif realism >= 0.4:
                lines.append("⚠️ Fair: Consider adjusting generation parameters for better realism.")
            else:
                lines.append("❌ Poor: Significant differences from real reviews detected.")
            
            lines.append("")
        
        # Recommendations
        lines.extend([
            "---",
            "",
            "## Recommendations",
            ""
        ])
        
        recommendations = self._generate_recommendations(
            dataset_metrics, generation_stats, comparison_metrics, bias_analysis
        )
        
        for rec in recommendations:
            lines.append(f"- {rec}")
        
        lines.extend([
            "",
            "---",
            "",
            f"*Report generated by Synthetic Review Generator*"
        ])
        
        return "\n".join(lines)
    
    def _generate_recommendations(
        self,
        dataset_metrics: Dict[str, Any],
        generation_stats: Dict[str, Any],
        comparison_metrics: Optional[Dict[str, Any]],
        bias_analysis: Optional[Dict[str, Any]]
    ) -> List[str]:
        """Generate recommendations based on metrics"""
        recommendations = []
        
        # Quality recommendations
        avg_score = dataset_metrics.get('avg_overall_score', 0)
        if avg_score < 0.6:
            recommendations.append("Consider adjusting quality thresholds or improving prompts to increase overall quality.")
        
        vocab_div = dataset_metrics.get('avg_vocabulary_diversity', 0)
        if vocab_div < 0.4:
            recommendations.append("Vocabulary diversity is low. Try adding more variety in prompts or use different personas.")
        
        # Bias recommendations
        if bias_analysis:
            issues = bias_analysis.get('issues', [])
            if 'Excessive positive sentiment bias' in str(issues):
                recommendations.append("Reduce positive sentiment bias by adjusting rating distribution or prompt wording.")
            if 'High vocabulary concentration' in str(issues):
                recommendations.append("Increase vocabulary variety by using more diverse prompts and personas.")
        
        # Comparison recommendations
        if comparison_metrics:
            realism = comparison_metrics.get('realism_score', 0)
            if realism < 0.5:
                recommendations.append("Realism score is low. Review prompt templates and compare with real review examples.")
            
            vocab = comparison_metrics.get('vocabulary', {})
            if vocab.get('vocab_overlap', 0) < 0.3:
                recommendations.append("Vocabulary overlap with real reviews is low. Include more domain-specific terminology.")
        
        # Performance recommendations
        acceptance_rate = generation_stats.get('acceptance_rate', 0)
        if acceptance_rate < 0.7:
            recommendations.append("Low acceptance rate. Consider relaxing quality thresholds or improving generation prompts.")
        
        if not recommendations:
            recommendations.append("Dataset quality meets all recommended thresholds. Continue monitoring for consistency.")
        
        return recommendations
    
    def save_report(
        self,
        report_content: str,
        filename: str = "quality_report.md"
    ) -> str:
        """Save report to file and return path"""
        filepath = self.output_dir / filename
        with open(filepath, 'w') as f:
            f.write(report_content)
        logger.info(f"Report saved to {filepath}")
        return str(filepath)
    
    def save_metrics_json(
        self,
        metrics: Dict[str, Any],
        filename: str = "metrics.json"
    ) -> str:
        """Save metrics to JSON file"""
        filepath = self.output_dir / filename
        with open(filepath, 'w') as f:
            json.dump(metrics, f, indent=2, default=str)
        logger.info(f"Metrics saved to {filepath}")
        return str(filepath)
