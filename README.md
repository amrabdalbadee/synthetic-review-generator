# Synthetic Review Generator with Quality Guardrails

A production-grade synthetic data generator for service/tool reviews in the Developer Tools & SaaS domain. Features configurable personas, multi-model support, comprehensive quality guardrails, and automated comparison against real reviews.

## 🎯 Features

- **Multi-Provider LLM Support**: Ollama (local), OpenAI, and Anthropic
- **Configurable Generation**: YAML-based configuration for personas, products, rating distributions
- **Quality Guardrails**: 
  - Vocabulary diversity metrics
  - Semantic similarity detection
  - Sentiment-rating alignment
  - Domain relevance validation
  - Automated rejection/regeneration
- **Bias Detection**: Sentiment skew, rating bias, vocabulary concentration analysis
- **Real vs Synthetic Comparison**: Statistical comparison against real review datasets
- **CLI Interface**: Easy-to-use command-line tools
- **Comprehensive Reporting**: Markdown and JSON quality reports

## 📋 Requirements

- Python 3.9+
- Ollama (for local LLM inference) - [Install Ollama](https://ollama.ai)
- Optional: OpenAI API key, Anthropic API key

## 🚀 Quick Start

### 1. Setup

```bash
# Clone or navigate to the project
cd synthetic-review-generator

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy environment template
cp .env.example .env
```

### 2. Configure Ollama

Ensure Ollama is running and has at least one model:

```bash
# Check Ollama status
ollama list

# Pull recommended models (if not already available)
ollama pull llama3.2
ollama pull mistral
```

### 3. Check Provider Status

```bash
python cli.py status
```

Expected output:
```
🔍 Checking Provider Status
LLM Provider Status:
========================================

OLLAMA:
  Status: ✓ Available
  Enabled: True
  Models: ['llama3.2', 'mistral', 'gemma2']
  Available Models: ['llama3.2', 'mistral']
...
```

### 4. Initialize Real Reviews Dataset

```bash
python cli.py init-real-reviews
```

This creates a sample dataset of 45 real developer tool reviews for comparison.

### 5. Generate Synthetic Reviews

```bash
# Generate with default settings (350 samples, multiple models)
python cli.py generate

# Generate specific number of samples
python cli.py generate -n 100

# Use single model
python cli.py generate --single-model -p ollama -m llama3.2
```

### 6. Compare with Real Reviews

```bash
python cli.py compare -s data/generated/synthetic_reviews_TIMESTAMP.json
```

### 7. Generate Quality Report

```bash
python cli.py report \
  -s data/generated/synthetic_reviews_TIMESTAMP.json \
  --stats data/generated/generation_stats_TIMESTAMP.json
```

## 📁 Project Structure

```
synthetic-review-generator/
├── cli.py                      # Main CLI interface
├── config/
│   └── config.yaml             # Main configuration file
├── src/
│   ├── providers/              # LLM provider implementations
│   │   ├── base.py            # Abstract base class
│   │   ├── ollama_provider.py # Ollama implementation
│   │   ├── openai_provider.py # OpenAI implementation
│   │   ├── anthropic_provider.py # Anthropic implementation
│   │   └── manager.py         # Provider orchestration
│   ├── generators/
│   │   └── review_generator.py # Main generation logic
│   ├── guardrails/
│   │   ├── quality.py         # Quality validation
│   │   └── comparison.py      # Synthetic vs real comparison
│   └── utils/
│       ├── real_reviews.py    # Real review utilities
│       └── report_generator.py # Report generation
├── data/
│   ├── generated/             # Generated synthetic reviews
│   └── real_reviews/          # Real review datasets
├── reports/                   # Quality reports
├── requirements.txt
├── .env.example
└── README.md
```

## ⚙️ Configuration

### config/config.yaml

The main configuration file controls all aspects of generation:

```yaml
generation:
  target_samples: 350
  max_retries_per_sample: 3
  batch_size: 10

products:
  - name: "CodeFlow IDE"
    category: "IDE/Code Editor"
    features: ["AI code completion", "Git integration"]
    price_tier: "freemium"

personas:
  - id: "senior_dev"
    name: "Senior Developer"
    experience_level: "expert"
    priorities: ["performance", "scalability"]
    tone: "technical"
    weight: 0.25

rating_distribution:
  1: 0.05
  2: 0.10
  3: 0.20
  4: 0.35
  5: 0.30

quality_thresholds:
  min_vocabulary_diversity: 0.3
  max_semantic_similarity: 0.85
  required_domain_keywords_ratio: 0.1
```

### Environment Variables (.env)

```bash
# For OpenAI (optional)
OPENAI_API_KEY=sk-...

# For Anthropic (optional)
ANTHROPIC_API_KEY=sk-ant-...

# Ollama (default)
OLLAMA_BASE_URL=http://localhost:11434
```

## 📊 Quality Metrics

### Individual Review Metrics

| Metric | Description | Threshold |
|--------|-------------|-----------|
| Vocabulary Diversity | Unique words / total words | ≥ 0.30 |
| Semantic Uniqueness | Dissimilarity from existing reviews | ≥ 0.15 |
| Sentiment Alignment | Sentiment matches rating | ≥ 0.70 |
| Domain Relevance | Domain keyword presence | ≥ 0.10 |
| Length Compliance | Within expected range | 50-2000 chars |
| Repetition Score | Low phrase repetition | ≤ 0.15 |

### Dataset Metrics

- **Pass Rate**: Percentage of reviews passing all quality checks
- **Rating Distribution**: Alignment with configured distribution
- **Sentiment Distribution**: Balance of positive/neutral/negative
- **Vocabulary Overlap**: Diversity across the dataset

### Comparison Metrics

- **Vocabulary Overlap**: Shared vocabulary with real reviews
- **Sentiment Similarity**: Distribution alignment
- **N-gram Overlap**: Bigram and trigram similarity
- **Realism Score**: Overall composite score

## 🔧 CLI Commands

```bash
# Check provider status
python cli.py status

# Generate reviews
python cli.py generate [OPTIONS]
  -c, --config PATH      Configuration file
  -o, --output PATH      Output directory
  -n, --samples INT      Number of samples
  --single-model         Use only one model
  -p, --provider TEXT    Specific provider
  -m, --model TEXT       Specific model

# Compare synthetic vs real
python cli.py compare [OPTIONS]
  -s, --synthetic PATH   Synthetic reviews JSON
  -r, --real PATH        Real reviews JSON
  -o, --output PATH      Output directory

# Generate quality report
python cli.py report [OPTIONS]
  -s, --synthetic PATH   Synthetic reviews JSON
  --stats PATH           Generation stats JSON
  -r, --real PATH        Real reviews JSON
  -o, --output PATH      Output directory

# Initialize real reviews
python cli.py init-real-reviews [OPTIONS]
  -o, --output PATH      Output directory

# Test single generation
python cli.py test-generation [OPTIONS]
  -p, --prompt TEXT      Custom prompt
  --provider TEXT        Provider to use
  --model TEXT           Model to use
```

## 🏗️ Architecture & Design Decisions

### Multi-Provider Architecture

The system uses an abstract provider interface allowing easy addition of new LLM providers:

```python
class BaseLLMProvider(ABC):
    @abstractmethod
    def generate(self, prompt: str) -> GenerationResult:
        pass
```

**Trade-off**: More complexity in exchange for flexibility and resilience through fallback support.

### Quality-First Generation

Reviews are validated immediately after generation with automatic retry on failure:

1. Generate review with LLM
2. Parse and clean output
3. Run quality checks
4. Accept or regenerate

**Trade-off**: Higher quality output at the cost of more LLM calls and longer generation time.

### Configurable Everything

All parameters are externalized to YAML configuration:

- Products and categories
- Persona definitions and weights
- Rating distributions
- Quality thresholds
- Model configurations

**Trade-off**: Flexibility vs. simplicity. Advanced users can tune everything, but defaults work well.

### Lightweight NLP

Quality metrics use simple, interpretable methods (word overlap, keyword matching) rather than heavy transformer models:

**Trade-off**: Faster execution and no GPU requirements, but potentially less sophisticated semantic analysis.

## 📈 Performance Considerations

### Hardware Requirements

- **Ollama**: 8GB+ RAM recommended for llama3.2/mistral
- **API Providers**: No special requirements

### Generation Speed

| Provider | Model | Avg Time/Review |
|----------|-------|-----------------|
| Ollama | llama3.2 | 3-8s |
| Ollama | mistral | 2-6s |
| OpenAI | gpt-4o-mini | 1-2s |
| Anthropic | claude-3-haiku | 1-2s |

### Scaling

For large datasets (1000+ reviews):
- Use batch processing
- Consider multiple Ollama instances
- Enable API providers for parallel generation

## 🔄 Adding New Providers

1. Create provider class inheriting from `BaseLLMProvider`
2. Implement `generate()` method
3. Register in `ProviderManager.PROVIDER_CLASSES`
4. Add configuration section to config.yaml

Example:
```python
class NewProvider(BaseLLMProvider):
    @property
    def provider_name(self) -> str:
        return "new_provider"
    
    def is_available(self) -> bool:
        # Check availability
        pass
    
    def generate(self, prompt: str, model_config=None) -> GenerationResult:
        # Implementation
        pass
```

## 📝 Sample Output

### Generated Review Example

```json
{
  "id": "syn_00001",
  "product_name": "CodeFlow IDE",
  "product_category": "IDE/Code Editor",
  "rating": 4,
  "text": "After three months of daily use, CodeFlow has significantly improved my workflow. The AI code completion is remarkably context-aware and saves considerable typing time. Git integration works seamlessly for most operations. My only complaint is occasional sluggishness with larger TypeScript projects. The extension marketplace offers good variety, though some popular plugins are missing. Overall, solid choice for modern development.",
  "persona_id": "senior_dev",
  "persona_name": "Senior Developer",
  "model": "llama3.2",
  "provider": "ollama",
  "generation_time": 4.521,
  "quality_score": {
    "vocabulary_diversity": 0.623,
    "semantic_uniqueness": 0.847,
    "sentiment_alignment": 1.0,
    "domain_relevance": 0.182,
    "overall_score": 0.734,
    "passed": true
  }
}
```

## 🐛 Troubleshooting

### Ollama Not Available

```bash
# Check if Ollama is running
curl http://localhost:11434/api/tags

# Start Ollama
ollama serve
```

### Low Acceptance Rate

- Adjust quality thresholds in config.yaml
- Improve prompt templates
- Use different models

### Memory Issues

- Reduce batch_size
- Use smaller models
- Close other applications

## 📜 License

MIT License - feel free to use and modify.

## 🙏 Acknowledgments

- Ollama team for local LLM infrastructure
- OpenAI and Anthropic for API access
- Rich library for beautiful CLI output
