# Configuration Examples

This directory contains example configuration files for different industry domains. These examples demonstrate how to customize the synthetic review generator for your specific use case.

## Available Examples

| File | Domain | Products | Personas |
|------|--------|----------|----------|
| `ecommerce_config.yaml` | E-commerce & Online Shopping | 5 | 6 |
| `health_fitness_config.yaml` | Health & Fitness Apps | 5 | 6 |
| `gaming_entertainment_config.yaml` | Gaming & Entertainment | 6 | 6 |
| `education_config.yaml` | Education & Learning | 6 | 6 |
| `restaurant_food_config.yaml` | Restaurant & Food Delivery | 6 | 6 |

## How to Use

### Option 1: Replace the main config

```bash
# Backup original config
cp config/config.yaml config/config.yaml.backup

# Use an example config
cp config/examples/ecommerce_config.yaml config/config.yaml

# Generate reviews
python cli.py generate -n 100
```

### Option 2: Use with CLI flag

```bash
python cli.py generate -n 100 --config config/examples/gaming_entertainment_config.yaml
```

## Configuration Structure

Each configuration file has the following main sections:

### 1. Generation Settings

```yaml
generation:
  target_samples: 400        # Total reviews to generate
  min_acceptable_samples: 350  # Minimum acceptable after quality filtering
  max_retries_per_sample: 3   # Retry attempts for failed generations
  batch_size: 10              # Reviews generated per batch
```

### 2. Products

Define the products/services to review:

```yaml
products:
  - name: "Product Name"
    category: "Category Type"
    description: "Brief description for LLM context"
    features: ["Feature 1", "Feature 2", "Feature 3"]
    price_tier: "freemium"  # freemium, paid, or enterprise
```

**Tips for products:**
- Include 4-6 products for variety
- Features help the LLM write specific, realistic reviews
- Price tier affects the tone (enterprise = professional, freemium = casual)

### 3. Personas

Define who writes the reviews:

```yaml
personas:
  - id: "unique_id"
    name: "Display Name"
    experience_level: "beginner"  # beginner, intermediate, expert
    priorities: ["what they care about"]
    tone: "casual"  # casual, technical, professional, etc.
    typical_review_length: "medium"  # short, medium, long
    weight: 0.25  # Distribution weight (should sum to 1.0)
```

**Tips for personas:**
- Weights control how often each persona is selected
- Experience level affects vocabulary complexity
- Priorities influence what aspects the review focuses on

### 4. Rating Distribution

Control the distribution of star ratings:

```yaml
rating_distribution:
  1: 0.08   # 8% 1-star reviews
  2: 0.10   # 10% 2-star reviews
  3: 0.17   # 17% 3-star reviews
  4: 0.35   # 35% 4-star reviews
  5: 0.30   # 30% 5-star reviews
```

**Common patterns:**
- **Positive skew** (typical): More 4-5 stars (satisfied customers review more)
- **Bimodal** (polarizing products): High 1-star and 5-star
- **Uniform**: Equal distribution (rare in real data)

### 5. Review Characteristics

Define length distributions and content markers:

```yaml
review_characteristics:
  length:
    short:
      min_words: 15
      max_words: 50
      weight: 0.30
    medium:
      min_words: 50
      max_words: 150
      weight: 0.50
    long:
      min_words: 150
      max_words: 300
      weight: 0.20
      
  sentiment_markers:
    positive: ["great", "excellent", "love it"]
    negative: ["terrible", "waste", "disappointed"]
    neutral: ["okay", "average", "decent"]
```

### 6. Quality Thresholds

Tune the quality guardrails:

```yaml
quality_thresholds:
  min_vocabulary_diversity: 0.25    # Lower = allow more repetitive language
  max_semantic_similarity: 0.80     # Higher = allow more similar reviews
  min_review_length_chars: 35       # Minimum characters
  max_review_length_chars: 1800     # Maximum characters
  required_domain_keywords_ratio: 0.10  # Percentage of domain words required
  sentiment_rating_alignment: 0.72  # How strictly sentiment must match rating
  max_repetition_ratio: 0.15        # Maximum phrase repetition allowed
```

### 7. Domain Keywords

Keywords for domain relevance validation:

```yaml
domain_keywords:
  category1:
    - "keyword1"
    - "keyword2"
  category2:
    - "keyword3"
    - "keyword4"
```

## Creating Your Own Configuration

### Step 1: Copy a template

```bash
cp config/examples/ecommerce_config.yaml config/my_domain_config.yaml
```

### Step 2: Define your products

Think about:
- What products/services exist in your domain?
- What are their key features?
- What price tiers exist?

### Step 3: Define your personas

Think about:
- Who uses these products?
- What do they care about?
- How do they write reviews?

### Step 4: Research rating distributions

Look at real review data from:
- G2, Capterra (B2B software)
- Yelp, Google (local businesses)
- Amazon, App Store (consumer products)
- Trustpilot (general services)

### Step 5: Collect domain keywords

Gather vocabulary specific to your domain from:
- Industry publications
- Existing reviews
- Product documentation

### Step 6: Tune quality thresholds

Start with defaults and adjust based on:
- Pass rate (aim for 70-85%)
- Review realism when compared to real data

## Example: Custom SaaS Config

Here's a minimal example for a custom SaaS domain:

```yaml
generation:
  target_samples: 200
  min_acceptable_samples: 180
  max_retries_per_sample: 3
  batch_size: 10

products:
  - name: "MySaaS Tool"
    category: "Project Management"
    description: "Team collaboration and project tracking"
    features: ["Task boards", "Time tracking", "Reports"]
    price_tier: "freemium"

personas:
  - id: "team_lead"
    name: "Team Lead"
    experience_level: "intermediate"
    priorities: ["team visibility", "reporting"]
    tone: "professional"
    typical_review_length: "medium"
    weight: 0.50
    
  - id: "individual_user"
    name: "Individual User"
    experience_level: "beginner"
    priorities: ["ease of use", "price"]
    tone: "casual"
    typical_review_length: "short"
    weight: 0.50

rating_distribution:
  1: 0.05
  2: 0.10
  3: 0.20
  4: 0.35
  5: 0.30

quality_thresholds:
  min_vocabulary_diversity: 0.25
  max_semantic_similarity: 0.82
  min_review_length_chars: 40
  max_review_length_chars: 1500
  required_domain_keywords_ratio: 0.08
  sentiment_rating_alignment: 0.70
  max_repetition_ratio: 0.15

domain_keywords:
  general:
    - "project"
    - "task"
    - "team"
    - "manage"
    - "track"

models:
  primary: "ollama"
  fallback: "ollama"
  ollama:
    enabled: true
    base_url: "http://localhost:11434"
    models:
      - name: "llama3.2"
        priority: 1
        temperature: 0.8
        max_tokens: 400

output:
  format: "json"
  include_metadata: true
  include_quality_scores: true
```

## Tips for Realistic Reviews

1. **Study real reviews** - Read actual reviews in your domain
2. **Vary the personas** - Different people write differently
3. **Balance ratings** - Real distributions are rarely uniform
4. **Include imperfections** - Real reviews have typos, informal language
5. **Domain specificity** - Use industry-specific vocabulary
6. **Emotional variance** - Some reviews are passionate, others factual
