# Kitsu AI - Component Reference

## 🏗️ Core Components

### KitsuEngine

**File**: `core/kitsu_engine.py`

Main processing engine with compression pipeline integration.

```python
class KitsuEngine:
    async def process_input(
        self, 
        user_input: str, 
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]
```

**Key Methods:**
- `process_input()`: Main processing pipeline
- `train_compression_offline()`: Train compression system
- `get_compression_stats()`: Get system statistics
- `trigger_emotion()`: Manually trigger emotions

**Configuration:**
```python
runtime_config = {
    "compression_path": "data/compression",
    "bitstream_width": 256,
    "binary_output_dim": 64,
    "markov_order": 2,
    "model": "tinyllama:1.1b",
    "temperature": 0.8,
}
```

---

### KitsuEngineMini

**File**: `core/kitsu_engine_mini.py`

Enhanced engine with hybrid generation (local + external LLM).

```python
class KitsuEngineMini(KitsuEngine):
    async def process_input(
        self,
        user_input: str,
        context: Optional[Dict[str, Any]] = None,
        force_generation_mode: Optional[str] = None
    ) -> Dict[str, Any]
```

**Additional Methods:**
- `train_local_predictor()`: Train the local token predictor
- `get_enhanced_status()`: Get hybrid generation statistics

**Enhanced Configuration:**
```python
runtime_config.update({
    "local_confidence_threshold": 0.7,
    "complexity_threshold": 0.6,
    "preferred_mode": "hybrid",
    "max_local_tokens": 64,
    "use_local_for_simple": True,
})
```

---

## 🧠 Brain Components

### IntentRouter

**File**: `core/brain/router.py`

Routes user input to appropriate processing paths.

```python
class IntentRouter:
    def route(self, state: KitsuState) -> Dict[str, Any]
```

**Routing Categories:**
- `question`: User is asking something
- `command`: User wants action performed
- `conversational`: Casual chat
- `unknown`: Unclear intent

---

### BinaryReasoner

**File**: `core/brain/binary_reasoner.py`

Extracts binary features from input and emotional state.

```python
class BinaryReasoner:
    def reason(self, state: KitsuState) -> Dict[str, Any]
```

**Binary Features** (25+ total):
- Input analysis: `needs_search`, `user_is_questioning`
- Context: `memory_relevant`, `emotional_support_needed`
- Response: `should_be_playful`, `keep_brief`
- Safety: `needs_safety_check`, `is_sensitive_topic`

---

## 🗜️ Compression Components

### CompressionPipeline

**File**: `core/compression/pipeline.py`

Main interface for compression system.

```python
class CompressionPipeline:
    def process(
        self, 
        text: str, 
        state_dict: Optional[Dict[str, Any]] = None,
        include_log: bool = False
    ) -> Tuple[np.ndarray, Optional[str], Optional[str]]
    
    def offline_train(
        self, 
        corpus: List[Tuple[str, Optional[Dict[str, Any]]]],
        training_pairs: Optional[List[Tuple[Dict[str, Any], Dict[str, int]]]] = None
    ) -> Dict[str, Any]
    
    def online_update(
        self,
        text: str,
        state_dict: Optional[Dict[str, Any]] = None,
        binary_features: Optional[Dict[str, int]] = None,
        rating: Optional[int] = None
    ) -> bool
```

---

### HuffmanMarkovEncoder

**File**: `core/compression/huffman_markov_encoder.py`

Combines Huffman coding with Markov chain prediction.

```python
class HuffmanMarkovEncoder:
    def encode(
        self, 
        text: str, 
        state_dict: Optional[Dict[str, Any]] = None
    ) -> Tuple[str, np.ndarray]
    
    def offline_train(self, corpus: List[Tuple[str, Optional[Dict[str, Any]]]]) -> None
    
    def online_update(
        self, 
        text: str, 
        state_dict: Optional[Dict[str, Any]] = None
    ) -> bool
```

**Methods:**
- `build_huffman_tree()`: Create Huffman codes from frequencies
- `build_markov_model()`: Build transition probabilities
- `export_weights()`: Export probability matrices for NN

---

### BinaryNN

**File**: `core/compression/binary_nn.py`

Neural network for binary feature extraction.

```python
class BinaryNN:
    def forward(
        self,
        bitstream_array: np.ndarray,
        context_vec: np.ndarray,
        binary_features: Optional[Dict[str, int]] = None,
        training: bool = False
    ) -> np.ndarray
    
    def train_batch(
        self,
        inputs: List[Tuple[np.ndarray, np.ndarray]],
        targets: List[np.ndarray],
        lr: float = 1e-3,
        epochs: int = 10
    ) -> List[float]
    
    def online_train_step(
        self,
        bitstream_array: np.ndarray,
        context_vec: np.ndarray,
        target: np.ndarray,
        lr: float = 5e-4
    ) -> float
```

**Architecture:**
- Input: `[bitstream | context]` → 768 units
- Hidden 1: 128 units (ReLU + STE)
- Hidden 2: 128 units (ReLU + STE)  
- Output: 64 units (binary)

---

## 🚀 Hybrid Generation Components

### HybridGenerator

**File**: `core/compression/hybrid_generator.py`

Controls routing between local and external generation.

```python
class HybridGenerator:
    async def generate_response(
        self,
        user_input: str,
        reasoning_vector: np.ndarray,
        binary_features: Dict[str, int],
        memory_context: Optional[str] = None,
        force_mode: Optional[GenerationMode] = None
    ) -> Dict[str, Any]
    
    def train_local_predictor(
        self,
        training_data: List[Tuple[str, str, Dict[str, int]]],
        epochs: int = 10,
        lr: float = 1e-3
    ) -> List[float]
```

**Generation Modes:**
- `LOCAL`: Use token predictor only
- `EXTERNAL`: Use external LLM only  
- `HYBRID`: Automatic routing based on complexity

---

### TokenPredictor

**File**: `core/compression/token_predictor.py`

Local next-token prediction system.

```python
class TokenPredictor:
    def predict_next_token(
        self,
        context_tokens: List[int],
        reasoning_vector: np.ndarray,
        markov_probs: Optional[Dict[str, float]] = None,
        temperature: Optional[float] = None,
        top_k: Optional[int] = None
    ) -> Tuple[int, float]
    
    def generate_sequence(
        self,
        prompt_tokens: List[int],
        reasoning_vector: np.ndarray,
        markov_probs: Optional[Dict[str, float]] = None,
        max_tokens: int = 32,
        temperature: Optional[float] = None,
        top_k: Optional[int] = None,
        stop_tokens: Optional[List[int]] = None
    ) -> List[int]
```

**Sub-components:**
- `TokenEmbeddings`: Learned word representations
- `NeuralTokenPredictor`: Neural next-token network

---

## 😊 Personality Components

### EmotionEngine

**File**: `core/personality/emotion_engine.py`

Manages Kitsu's emotional state and personality.

```python
class EmotionEngine:
    def process_user_input(self, user_input: str, state: KitsuState) -> None
    
    def get_emotional_state(self) -> Dict[str, Any]
    
    def trigger_emotion(self, emotion: str, intensity: float = 1.0) -> None
    
    def decay_emotions(self, decay_rate: float = 0.1) -> None
```

**Emotional Features:**
- Mood states: `behave`, `playful`, `mean`, `protective`
- Emotions: `happy`, `sad`, `angry`, `excited`, `worried`
- Resistance: Prevents rapid mood changes
- Stack: Multiple simultaneous emotions

---

### KitsuSelf

**File**: `core/personality/kitsu_self.py`

Core personality configuration and traits.

```python
class KitsuSelf:
    def __init__(self, initial_state: Dict[str, Any])
    
    def get_character_context(self) -> str
    
    def export_state(self) -> Dict[str, Any]
    
    def update_trait(self, trait: str, value: Any) -> None
```

**Personality Traits:**
- Base personality: playful, curious, slightly mischievous
- Speech patterns: fox noises, casual language
- Behavioral preferences: helpful but teasing

---

## 💾 Memory Components

### MemoryManager

**File**: `core/memory/memory_manager.py`

Manages short-term, episodic, and long-term memory.

```python
class MemoryManager:
    async def store_memory(
        self,
        content: str,
        memory_type: MemoryType,
        emotional_tags: List[str],
        context_tags: List[str]
    ) -> None
    
    async def recall(
        self, 
        query: str, 
        context_length: int = 3,
        memory_types: Optional[List[MemoryType]] = None
    ) -> List[Dict[str, Any]]
    
    def format_context(self, limit: int = 3) -> str
```

**Memory Types:**
- `SHORT_TERM`: Recent interactions
- `EPISODIC`: Specific conversations/events
- `SEMANTIC`: General knowledge
- `PROCEDURAL`: How to do things

---

## 🔧 Utility Components

### LLMController

**File**: `llm/llm_controller.py`

Interface to external language models.

```python
class LLMController:
    async def generate_response(
        self,
        user_input: str,
        mood: str,
        style: str
    ) -> str
    
    async def execute_prompt(
        self,
        prompt: str,
        mood: str,
        style: str,
        emotion: str
    ) -> str
```

**Supported Adapters:**
- `OllamaAdapter`: Local Ollama models
- `LoRAAdapter`: Fine-tuned models with LoRA

---

### BinaryTranslator

**File**: `core/compression/translator.py`

Converts binary vectors to prompts and responses.

```python
class BinaryTranslator:
    def binary_to_prompt(
        self,
        vec: np.ndarray,
        state: Any,
        user_input: str,
        user_info: Optional[Dict[str, Any]] = None,
        memory_context: Optional[str] = None
    ) -> str
    
    def binary_to_log(
        self,
        vec: np.ndarray,
        state_dict: Dict[str, Any],
        user_input: str,
        encoder_explain: str
    ) -> str
```

---

## 📊 Configuration Classes

### GenerationConfig

**File**: `core/compression/hybrid_generator.py`

```python
@dataclass
class GenerationConfig:
    local_confidence_threshold: float = 0.15
    complexity_threshold: float = 0.6
    resource_threshold: float = 0.5
    max_local_tokens: int = 64
    max_external_tokens: int = 512
    temperature_local: float = 0.8
    temperature_external: float = 0.7
    preferred_mode: GenerationMode = GenerationMode.HYBRID
    fallback_to_external: bool = True
    use_local_for_simple: bool = True
```

### TokenPredictorConfig

**File**: `core/compression/token_predictor.py`

```python
@dataclass
class TokenPredictorConfig:
    vocab_size: int = 512
    embedding_dim: int = 64
    hidden_dim: int = 128
    context_window: int = 8
    temperature: float = 0.8
    top_k: int = 40
    markov_weight: float = 0.5
    neural_weight: float = 0.5
```

---

## 🔄 Usage Examples

### Basic Usage

```python
from core.kitsu_engine_mini import KitsuEngineMini

# Initialize
config = {
    "model": "tinyllama:1.1b",
    "preferred_mode": "hybrid",
    "local_confidence_threshold": 0.7,
}
engine = KitsuEngineMini(config)
await engine.initialize()

# Process input
response = await engine.process_input("hello how are you?")
print(response["text"])
print(f"Mode: {response['generation_metadata']['generation_mode']}")
print(f"Time: {response['total_processing_time']:.3f}s")
```

### Training Local Predictor

```python
# Train from existing data
results = await engine.train_local_predictor(
    training_data_path="data/conversations.jsonl",
    epochs=20,
    lr=1e-3
)

print(f"Trained on {results['training_samples']} samples")
print(f"Final loss: {results['final_loss']:.4f}")
```

### Custom Configuration

```python
from core.compression.hybrid_generator import GenerationConfig, GenerationMode

# Force local generation only
local_config = GenerationConfig(
    preferred_mode=GenerationMode.LOCAL,
    local_confidence_threshold=0.5,
    max_local_tokens=32,
)

engine = KitsuEngineMini(config)
engine.hybrid_generator.config = local_config
```

### Monitoring Performance

```python
# Get system status
status = engine.get_enhanced_status()

print("Generation Statistics:")
stats = status["hybrid_generation"]["generation_stats"]
print(f"  Local: {stats['local_generations']}")
print(f"  External: {stats['external_generations']}")
print(f"  Hybrid: {stats['hybrid_generations']}")

print("Compression Stats:")
comp_stats = status["compression"]
print(f"  Available: {comp_stats['available']}")
print(f"  Vocab size: {comp_stats['encoder']['vocab_size']}")
```

This reference provides complete API documentation for all Kitsu components.
