#!/usr/bin/env python3
"""
Synthetic Review Generator CLI
Command-line interface for generating synthetic reviews with quality guardrails
"""

import sys
import json
import logging
from pathlib import Path
from datetime import datetime

import click
import yaml
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.table import Table
from rich.panel import Panel

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.providers import ProviderManager
from src.generators import ReviewGenerator
from src.guardrails import QualityGuardrails, ReviewComparator
from src.utils import (
    get_sample_real_reviews,
    load_real_reviews,
    save_real_reviews,
    initialize_real_reviews,
    RealReviewStats,
    ReportGenerator
)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

console = Console()


def load_config(config_path: str) -> dict:
    """Load configuration from YAML file"""
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)


@click.group()
@click.version_option(version='1.0.0')
def cli():
    """Synthetic Review Generator - Generate high-quality synthetic product reviews"""
    pass


@cli.command()
@click.option('--config', '-c', default='config/config.yaml', help='Path to configuration file')
def status(config):
    """Check status of LLM providers"""
    console.print(Panel.fit("🔍 Checking Provider Status", style="bold blue"))
    
    try:
        cfg = load_config(config)
        manager = ProviderManager(cfg.get('models', {}))
        
        console.print(manager.status_report())
        
        available = manager.get_available_providers()
        if available:
            console.print(f"\n[green]✓ {len(available)} provider(s) available: {', '.join(available)}[/green]")
        else:
            console.print("\n[red]✗ No providers available. Please check your configuration.[/red]")
            
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise click.Abort()


@cli.command()
@click.option('--config', '-c', default='config/config.yaml', help='Path to configuration file')
@click.option('--output', '-o', default='data/generated', help='Output directory')
@click.option('--samples', '-n', type=int, help='Number of samples to generate (overrides config)')
@click.option('--single-model', is_flag=True, help='Use only one model instead of multiple')
@click.option('--provider', '-p', type=str, help='Specific provider to use')
@click.option('--model', '-m', type=str, help='Specific model to use')
def generate(config, output, samples, single_model, provider, model):
    """Generate synthetic reviews"""
    console.print(Panel.fit("🚀 Synthetic Review Generator", style="bold green"))
    
    try:
        # Load configuration
        cfg = load_config(config)
        
        if samples:
            cfg['generation']['target_samples'] = samples
        
        # Initialize components
        console.print("\n[cyan]Initializing components...[/cyan]")
        
        provider_manager = ProviderManager(cfg.get('models', {}))
        
        # Check availability
        available = provider_manager.get_available_providers()
        if not available:
            console.print("[red]Error: No LLM providers available![/red]")
            console.print("Please ensure Ollama is running or configure API keys.")
            raise click.Abort()
        
        console.print(f"[green]Available providers: {', '.join(available)}[/green]")
        
        # Initialize guardrails
        guardrails = QualityGuardrails(
            cfg,
            cfg.get('domain_keywords', {})
        )
        
        # Initialize generator
        generator = ReviewGenerator(cfg, provider_manager, guardrails)
        
        target = cfg['generation']['target_samples']
        console.print(f"\n[cyan]Target: {target} reviews[/cyan]")
        
        # Generate with progress bar
        reviews = []
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console
        ) as progress:
            task = progress.add_task("[green]Generating reviews...", total=target)
            
            def update_progress(current, total, accepted):
                progress.update(task, completed=current, description=f"[green]Generating reviews... ({accepted} accepted)")
            
            if single_model or provider:
                # Use single model
                reviews = generator.generate_batch(
                    target,
                    provider_name=provider,
                    model_name=model,
                    progress_callback=update_progress
                )
            else:
                # Use multiple models for diversity
                reviews = generator.generate_dataset(
                    use_multiple_models=True,
                    progress_callback=update_progress
                )
        
        console.print(f"\n[green]✓ Generated {len(reviews)} reviews[/green]")
        
        # Calculate quality metrics
        console.print("\n[cyan]Calculating quality metrics...[/cyan]")
        
        review_dicts = [r.to_dict() for r in reviews]
        dataset_metrics = guardrails.calculate_dataset_metrics(review_dicts)
        bias_analysis = guardrails.detect_bias(review_dicts)
        
        # Save generated reviews
        output_dir = Path(output)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        reviews_file = output_dir / f"synthetic_reviews_{timestamp}.json"
        
        with open(reviews_file, 'w') as f:
            json.dump(review_dicts, f, indent=2)
        
        console.print(f"[green]✓ Reviews saved to {reviews_file}[/green]")
        
        # Display summary
        table = Table(title="Generation Summary")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")
        
        stats = generator.get_stats()
        table.add_row("Total Generated", str(len(reviews)))
        table.add_row("Acceptance Rate", f"{stats['acceptance_rate']*100:.1f}%")
        table.add_row("Avg Quality Score", f"{dataset_metrics.avg_overall_score*100:.1f}%")
        table.add_row("Total Time", f"{stats['total_time']:.1f}s")
        table.add_row("Avg Time/Review", f"{stats['avg_time_per_review']:.2f}s")
        
        console.print(table)
        
        # Show bias warnings
        if bias_analysis.get('issues'):
            console.print("\n[yellow]⚠️  Bias Warnings:[/yellow]")
            for issue in bias_analysis['issues']:
                console.print(f"  - {issue}")
        
        # Save stats
        stats_file = output_dir / f"generation_stats_{timestamp}.json"
        with open(stats_file, 'w') as f:
            json.dump({
                'generation_stats': stats,
                'dataset_metrics': dataset_metrics.to_dict() if hasattr(dataset_metrics, 'to_dict') else dataset_metrics,
                'bias_analysis': bias_analysis
            }, f, indent=2)
        
        console.print(f"\n[green]✓ Stats saved to {stats_file}[/green]")
        
    except FileNotFoundError as e:
        console.print(f"[red]Configuration file not found: {e}[/red]")
        raise click.Abort()
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        logger.exception("Generation failed")
        raise click.Abort()


@cli.command()
@click.option('--synthetic', '-s', required=True, help='Path to synthetic reviews JSON')
@click.option('--real', '-r', default=None, help='Path to real reviews JSON (uses sample if not provided)')
@click.option('--output', '-o', default='reports', help='Output directory for report')
def compare(synthetic, real, output):
    """Compare synthetic reviews against real reviews"""
    console.print(Panel.fit("📊 Review Comparison Analysis", style="bold blue"))
    
    try:
        # Load synthetic reviews
        console.print(f"\n[cyan]Loading synthetic reviews from {synthetic}...[/cyan]")
        with open(synthetic, 'r') as f:
            synthetic_reviews = json.load(f)
        console.print(f"[green]Loaded {len(synthetic_reviews)} synthetic reviews[/green]")
        
        # Load real reviews
        if real:
            console.print(f"[cyan]Loading real reviews from {real}...[/cyan]")
            real_reviews = load_real_reviews(real)
        else:
            console.print("[cyan]Using sample real reviews...[/cyan]")
            real_reviews = get_sample_real_reviews()
        
        console.print(f"[green]Loaded {len(real_reviews)} real reviews[/green]")
        
        # Run comparison
        console.print("\n[cyan]Analyzing...[/cyan]")
        comparator = ReviewComparator()
        metrics = comparator.compare(synthetic_reviews, real_reviews)
        
        # Display results
        table = Table(title="Comparison Results")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")
        
        table.add_row("Vocabulary Overlap", f"{metrics.vocab_overlap*100:.1f}%")
        table.add_row("Sentiment Similarity", f"{metrics.sentiment_similarity*100:.1f}%")
        table.add_row("Rating Distribution Similarity", f"{metrics.rating_similarity*100:.1f}%")
        table.add_row("Bigram Overlap", f"{metrics.bigram_overlap*100:.1f}%")
        table.add_row("Trigram Overlap", f"{metrics.trigram_overlap*100:.1f}%")
        table.add_row("Overall Realism Score", f"{metrics.realism_score*100:.1f}%")
        
        console.print(table)
        
        # Interpretation
        if metrics.realism_score >= 0.7:
            console.print("\n[green]✓ Excellent: Synthetic reviews closely match real review patterns.[/green]")
        elif metrics.realism_score >= 0.5:
            console.print("\n[yellow]⚠ Good: Reasonable similarity, some room for improvement.[/yellow]")
        else:
            console.print("\n[red]✗ Needs improvement: Significant differences from real reviews.[/red]")
        
        # Save detailed report
        output_dir = Path(output)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        report_file = output_dir / "comparison_report.json"
        with open(report_file, 'w') as f:
            json.dump(metrics.to_dict(), f, indent=2)
        
        console.print(f"\n[green]✓ Detailed report saved to {report_file}[/green]")
        
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        logger.exception("Comparison failed")
        raise click.Abort()


@cli.command()
@click.option('--synthetic', '-s', required=True, help='Path to synthetic reviews JSON')
@click.option('--stats', required=True, help='Path to generation stats JSON')
@click.option('--real', '-r', default=None, help='Path to real reviews JSON')
@click.option('--output', '-o', default='reports', help='Output directory')
@click.option('--config', '-c', default='config/config.yaml', help='Path to configuration file')
def report(synthetic, stats, real, output, config):
    """Generate comprehensive quality report"""
    console.print(Panel.fit("📝 Generating Quality Report", style="bold green"))
    
    try:
        # Load data
        with open(synthetic, 'r') as f:
            synthetic_reviews = json.load(f)
        
        with open(stats, 'r') as f:
            stats_data = json.load(f)
        
        
        cfg = load_config(config)
        
        # Load real reviews for comparison
        if real:
            real_reviews = load_real_reviews(real)
        else:
            real_reviews = get_sample_real_reviews()
        
        # Run comparison
        comparator = ReviewComparator()
        comparison_metrics = comparator.compare(synthetic_reviews, real_reviews)
        
        # Initialize guardrails for bias analysis
        guardrails = QualityGuardrails(cfg, cfg.get('domain_keywords', {}))
        bias_analysis = guardrails.detect_bias(synthetic_reviews)
        
        # Generate report
        report_gen = ReportGenerator(output)
        
        config_summary = {
            'target_samples': cfg.get('generation', {}).get('target_samples'),
            'products': len(cfg.get('products', [])),
            'personas': len(cfg.get('personas', [])),
            'models': cfg.get('models', {}).get('primary', 'unknown')
        }
        
        report_content = report_gen.generate_quality_report(
            dataset_metrics=stats_data.get('dataset_metrics', {}),
            generation_stats=stats_data.get('generation_stats', {}),
            comparison_metrics=comparison_metrics.to_dict(),
            bias_analysis=bias_analysis,
            config_summary=config_summary
        )
        
        # Save report
        report_path = report_gen.save_report(report_content)
        
        # Also save metrics JSON
        metrics_path = report_gen.save_metrics_json({
            'dataset_metrics': stats_data.get('dataset_metrics', {}),
            'generation_stats': stats_data.get('generation_stats', {}),
            'comparison_metrics': comparison_metrics.to_dict(),
            'bias_analysis': bias_analysis
        })
        
        console.print(f"\n[green]✓ Report saved to {report_path}[/green]")
        console.print(f"[green]✓ Metrics saved to {metrics_path}[/green]")
        
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        logger.exception("Report generation failed")
        raise click.Abort()


@cli.command()
@click.option('--output', '-o', default='data/real_reviews', help='Output directory')
def init_real_reviews(output):
    """Initialize sample real reviews dataset"""
    console.print(Panel.fit("📥 Initializing Real Reviews Dataset", style="bold cyan"))
    
    try:
        filepath = initialize_real_reviews(output)
        reviews = load_real_reviews(filepath)
        
        stats = RealReviewStats.calculate(reviews)
        
        console.print(f"\n[green]✓ Initialized {len(reviews)} real reviews[/green]")
        console.print(f"[green]✓ Saved to {filepath}[/green]")
        
        table = Table(title="Real Reviews Summary")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")
        
        table.add_row("Total Reviews", str(stats['total_reviews']))
        table.add_row("Average Rating", f"{stats['avg_rating']:.1f}")
        table.add_row("Avg Length", f"{stats['avg_length']:.0f} chars")
        table.add_row("Categories", str(len(stats['category_distribution'])))
        
        console.print(table)
        
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise click.Abort()


@cli.command()
@click.option('--config', '-c', default='config/config.yaml', help='Path to configuration file')
@click.option('--prompt', '-p', type=str, help='Custom prompt to test')
@click.option('--provider', type=str, help='Provider to use')
@click.option('--model', type=str, help='Model to use')
def test_generation(config, prompt, provider, model):
    """Test generation with a single sample"""
    console.print(Panel.fit("🧪 Testing Generation", style="bold yellow"))
    
    try:
        cfg = load_config(config)
        provider_manager = ProviderManager(cfg.get('models', {}))
        
        # Check availability
        available = provider_manager.get_available_providers()
        if not available:
            console.print("[red]No providers available![/red]")
            raise click.Abort()
        
        console.print(f"[green]Using provider: {provider or available[0]}[/green]")
        
        if prompt:
            test_prompt = prompt
        else:
            test_prompt = """Write a brief, realistic review for a code editor tool.
Rating: 4 stars
Length: 50-100 words
Focus on: usability and features
Write only the review text:"""
        
        console.print(f"\n[cyan]Prompt:[/cyan]\n{test_prompt[:200]}...")
        
        with console.status("[bold green]Generating..."):
            result = provider_manager.generate(
                test_prompt,
                provider_name=provider,
                model_name=model
            )
        
        if result.success:
            console.print(f"\n[green]✓ Generated in {result.generation_time:.2f}s[/green]")
            console.print(f"[cyan]Model: {result.provider}:{result.model}[/cyan]")
            console.print(f"\n[white]{result.text}[/white]")
        else:
            console.print(f"\n[red]✗ Generation failed: {result.error}[/red]")
        
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        logger.exception("Test failed")
        raise click.Abort()


if __name__ == '__main__':
    cli()
