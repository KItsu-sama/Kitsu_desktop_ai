# Kitsu AI - Mini LLM Guide

## 🎯 Overview

The Mini LLM component provides **local token prediction** capabilities that work alongside the external LLM. This enables Kitsu to respond instantly to common interactions while maintaining the ability to handle complex reasoning when needed.

## 🧠 Architecture

### Components

1. **TokenEmbeddings** - Learned word representations (~1.2 MB)
2. **NeuralTokenPredictor** - Next-token prediction network (~2-4 MB)  
3. **HybridGenerator** - Routes between local/external generation
4. **ComplexityAnalyzer** - Determines when to use each mode

### Memory Footprint

| Component | Size | Description |
|-----------|------|-------------|
| Token Embeddings | 1.2 MB | 512 vocab × 64 dim |
| Neural Network | 2.8 MB | 2-layer feedforward |
| Markov Model | 1.5 MB | Transition probabilities |
| **Total** | **~5.5 MB** | **Complete local system** |

## 🚀 Quick Start

### Basic Usage

```python
from core.kitsu_engine_mini import KitsuEngineMini
from core.compression.hybrid_generator import GenerationConfig

# Configure for hybrid generation
config = {
    "model": "tinyllama:1.1b",
    "local_confidence_threshold": 0.7,
    "complexity_threshold": 0.6,
    "preferred_mode": "hybrid",
}

# Initialize engine
engine = KitsuEngineMini(config)
await engine.initialize()

# Process input (automatic routing)
response = await engine.process_input("hello how are you?")

print(f"Response: {response['text']}")
print(f"Mode: {response['generation_metadata']['generation_mode']}")
print(f"Time: {response['total_processing_time']:.3f}s")
```

### Force Specific Mode

```python
# Force local generation only
response = await engine.process_input(
    "hello", 
    force_generation_mode="local"
)

# Force external generation only  
response = await engine.process_input(
    "explain quantum computing",
    force_generation_mode="external"
)
```

## 🎚️ Configuration

### GenerationConfig

```python
from core.compression.hybrid_generator import GenerationConfig, GenerationMode

config = GenerationConfig(
    # Routing thresholds
    local_confidence_threshold=0.7,    # When to trust local prediction
    complexity_threshold=0.6,          # Request complexity cutoff
    resource_threshold=0.5,            # System resource consideration
    
    # Generation parameters
    max_local_tokens=64,               # Max tokens for local generation
    max_external_tokens=512,           # Max tokens for external LLM
    temperature_local=0.8,              # Creativity for local
    temperature_external=0.7,           # Creativity for external
    
    # Mode preferences
    preferred_mode=GenerationMode.HYBRID,  # local/external/hybrid
    fallback_to_external=True,          # Safety fallback enabled
    use_local_for_simple=True,          # Use local for simple inputs
)
```

### TokenPredictorConfig

```python
from core.compression.token_predictor import TokenPredictorConfig

token_config = TokenPredictorConfig(
    vocab_size=512,                    # Vocabulary size
    embedding_dim=64,                   # Embedding dimensions
    hidden_dim=128,                    # Hidden layer size
    context_window=8,                  # Context for prediction
    temperature=0.8,                    # Sampling temperature
    top_k=40,                          # Top-k sampling
    markov_weight=0.5,                 # Markov influence
    neural_weight=0.5,                 # Neural influence
)
```

## 📚 Training the Local Predictor

### Prepare Training Data

```python
# Training data format: (input_text, target_response, binary_features)
training_data = [
    ("hello", "Hey! I'm Kitsu 🦊 How are you today?", {"user_is_questioning": 1, "should_be_playful": 1}),
    ("help me", "Sure! What do you need help with?", {"user_requests_help": 1, "should_be_caring": 1}),
    ("tell me a joke", "Why don't foxes use smartphones? They can't find the 'app'! 🦊", {"creative_response_needed": 1}),
]
```

### Training from Existing Data

```python
# Train from existing conversation logs
results = await engine.train_local_predictor(
    training_data_path="data/conversations.jsonl",  # Optional
    epochs=20,
    lr=1e-3
)

print(f"Trained on {results['training_samples']} samples")
print(f"Final loss: {results['final_loss']:.4f}")
print(f"Loss history: {results['loss_history']}")
```

### Manual Training

```python
# Train with custom data
custom_data = [
    ("hi there", "Hello! Great to see you! 🦊", {"should_be_playful": 1}),
    ("i'm sad", "Oh no, I'm here for you! Want to talk about it?", {"should_be_caring": 1}),
]

losses = engine.hybrid_generator.train_local_predictor(
    training_data=custom_data,
    epochs=15,
    lr=5e-4
)
```

### Training Data Format

The system expects JSONL format:

```json
{"input": {"text": "hello"}, "output": {"text": "Hey there!", "personality": {"mood": "playful"}}}
{"input": {"text": "help me"}, "output": {"text": "Sure! What do you need?", "personality": {"mood": "caring"}}}
```

## 🔍 Monitoring Performance

### Generation Statistics

```python
# Get comprehensive statistics
status = engine.get_enhanced_status()

# Hybrid generation stats
hybrid_stats = status["hybrid_generation"]["generation_stats"]
print(f"Local generations: {hybrid_stats['local_generations']}")
print(f"External generations: {hybrid_stats['external_generations']}")
print(f"Hybrid generations: {hybrid_stats['hybrid_generations']}")
print(f"Fallbacks: {hybrid_stats['fallbacks']}")

# Token predictor stats
predictor_stats = status["hybrid_generation"]["token_predictor"]
print(f"Predictor trained: {predictor_stats['is_trained']}")
print(f"Vocabulary size: {predictor_stats['vocab_size']}")
```

### Performance Metrics

```python
# Track generation performance
response = await engine.process_input("test input")

# Timing information
print(f"Total time: {response['total_processing_time']:.3f}s")
print(f"Generation mode: {response['generation_metadata']['generation_mode']}")
print(f"Generation time: {response['generation_metadata']['generation_time']:.3f}s")
print(f"Complexity: {response['generation_metadata']['complexity']:.2f}")
print(f"Confidence: {response['generation_metadata']['confidence']:.2f}")
```

### Mode Analysis

```python
# Analyze routing decisions
def analyze_routing(test_inputs: List[str]):
    local_count = 0
    external_count = 0
    
    for text in test_inputs:
        response = await engine.process_input(text)
        mode = response["generation_metadata"]["generation_mode"]
        
        if mode == "local":
            local_count += 1
        else:
            external_count += 1
            
    print(f"Local: {local_count}/{len(test_inputs)} ({local_count/len(test_inputs)*100:.1f}%)")
    print(f"External: {external_count}/{len(test_inputs)} ({external_count/len(test_inputs)*100:.1f}%)")
```

## 🎨 Customization

### Personality Integration

```python
# Custom personality responses
personality_patterns = {
    "playful": {
        "greeting": "Hey there! 🦊 What's up?",
        "question": "Ooh, interesting question! Let me think...",
        "help": "Sure thing! I'd love to help! 🦊",
    },
    "caring": {
        "greeting": "Hello! It's so nice to see you!",
        "question": "That's a thoughtful question. Let me help...",
        "help": "Of course! I'm here for you.",
    }
}
```

### Custom Binary Features

```python
# Add custom binary features
class CustomBinaryReasoner(BinaryReasoner):
    def __init__(self):
        super().__init__()
        
        # Add custom features
        self.feature_rules.update({
            "is_technical": self._is_technical,
            "needs_code": self._needs_code,
            "is_creative": self._is_creative,
        })
    
    def _is_technical(self, state: Dict[str, Any]) -> int:
        user_input = state.get("user_input", "").lower()
        tech_keywords = ["api", "function", "algorithm", "database"]
        return 1 if any(kw in user_input for kw in tech_keywords) else 0
```

### Custom Generation Logic

```python
class CustomHybridGenerator(HybridGenerator):
    def _should_use_local(self, user_input: str, complexity: float) -> bool:
        # Custom logic for local generation decision
        
        # Always use local for greetings
        if any(greeting in user_input.lower() for greeting in ["hello", "hi", "hey"]):
            return True
            
        # Use external for technical questions
        if "explain" in user_input.lower() or "how to" in user_input.lower():
            return False
            
        # Default to complexity-based routing
        return complexity < self.config.complexity_threshold
```

## 🛠️ Advanced Usage

### Batch Processing

```python
async def batch_process(inputs: List[str]) -> List[Dict[str, Any]]:
    """Process multiple inputs efficiently."""
    tasks = [engine.process_input(text) for text in inputs]
    responses = await asyncio.gather(*tasks)
    return responses

# Usage
batch_inputs = ["hello", "how are you?", "help me", "explain AI"]
batch_responses = await batch_process(batch_inputs)
```

### Streaming Generation

```python
async def stream_response(user_input: str):
    """Stream response generation token by token."""
    response = await engine.process_input(user_input)
    
    if response["generation_metadata"]["generation_mode"] == "local":
        # Stream local generation
        tokens = response["text"].split()
        for i, token in enumerate(tokens):
            yield token + (" " if i < len(tokens) - 1 else "")
            await asyncio.sleep(0.01)  # Small delay for effect
    else:
        # External LLM response (already complete)
        yield response["text"]
```

### Performance Optimization

```python
# Optimize for speed
speed_config = GenerationConfig(
    local_confidence_threshold=0.5,      # More aggressive fast path
    complexity_threshold=0.4,            # Lower threshold
    max_local_tokens=32,                 # Shorter responses
    temperature_local=0.6,               # More deterministic
    preferred_mode=GenerationMode.LOCAL,  # Prefer local
)

# Optimize for quality
quality_config = GenerationConfig(
    local_confidence_threshold=0.8,      # Conservative fast path
    complexity_threshold=0.8,            # Higher threshold
    max_local_tokens=128,                # Longer responses
    temperature_local=0.9,               # More creative
    preferred_mode=GenerationMode.EXTERNAL,  # Prefer external
)
```

## 🔧 Troubleshooting

### Common Issues

#### 1. Low Local Generation Rate

```python
# Check confidence threshold
if hybrid_stats["local_generations"] / total < 0.5:
    print("Consider lowering local_confidence_threshold")
    print("Current threshold:", config["local_confidence_threshold"])
```

#### 2. Poor Local Response Quality

```python
# Check training data
if not predictor_stats["is_trained"]:
    print("Token predictor not trained - run training first")
    
# Check vocabulary size
if predictor_stats["vocab_size"] < 256:
    print("Vocabulary too small - consider increasing vocab_size")
```

#### 3. High Latency

```python
# Monitor generation times
if response["total_processing_time"] > 0.1:
    mode = response["generation_metadata"]["generation_mode"]
    print(f"High latency in {mode} mode")
    
    if mode == "local":
        print("Consider optimizing token predictor or reducing context_window")
    else:
        print("External LLM is slow - check model or network")
```

### Debug Mode

```python
# Enable detailed logging
import logging
logging.getLogger("core.compression.hybrid_generator").setLevel(logging.DEBUG)
logging.getLogger("core.compression.token_predictor").setLevel(logging.DEBUG)

# Process with debug info
response = await engine.process_input("debug test")
print("Debug log:", response.get("debug_log", "No debug log available"))
```

## 📈 Best Practices

### 1. Training Data Quality

- Use diverse conversation examples
- Include personality-consistent responses
- Balance simple and complex examples
- Ensure proper binary feature labeling

### 2. Configuration Tuning

- Start with default thresholds
- Adjust based on usage patterns
- Monitor success rates
- Balance speed vs quality

### 3. Performance Monitoring

- Track generation mode ratios
- Monitor latency percentiles
- Watch for performance regression
- Set up alerts for anomalies

### 4. Continuous Improvement

- Collect user feedback
- Retrain with new data periodically
- Adjust thresholds based on performance
- Experiment with new features

This guide provides everything needed to effectively use and optimize the Kitsu Mini LLM system for fast, intelligent local generation.
