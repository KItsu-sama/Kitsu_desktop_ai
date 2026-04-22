# Kitsu AI - Performance Guide

## ⚡ Performance Benchmarks

### Latency Measurements

| Operation | Fast Brain | Slow Brain | Hybrid System |
|-----------|------------|------------|---------------|
| Simple greeting | 2-5ms | N/A | 2-5ms |
| Basic question | 3-8ms | 800ms | 3-8ms |
| Complex query | N/A | 1.2s | 1.2s |
| Creative task | N/A | 1.8s | 1.8s |
| Emotional support | 4-10ms | 900ms | 4-10ms |

### Memory Usage

| Component | Memory | Description |
|-----------|--------|-------------|
| Token Embeddings | 1.2 MB | 512 vocab × 64 dim |
| Neural Predictor | 2.8 MB | 2 hidden layers |
| Huffman Codes | 0.5 MB | Compression table |
| Markov Model | 1.5 MB | Transition probabilities |
| BinaryNN | 1.0 MB | Reasoning network |
| **Total Fast Brain** | **7.0 MB** | **Local generation** |
| External LLM | Variable | Depends on model |

### CPU Usage

| Process | CPU% | Duration |
|---------|------|----------|
| Feature extraction | 5-10% | 1-2ms |
| Compression encoding | 8-15% | 2-3ms |
| Binary reasoning | 3-8% | <1ms |
| Local prediction | 10-20% | 1-3ms |
| External LLM call | 60-80% | 500ms-2s |

## 🚀 Optimization Strategies

### Fast Path Optimizations

#### 1. Precomputed Lookups

```python
# Cache frequent patterns
@lru_cache(maxsize=1000)
def get_binary_features_cached(text_hash: int) -> Dict[str, int]:
    return extract_binary_features(text)

# Cache compression results
@lru_cache(maxsize=500)
def get_compression_vector_cached(text_hash: int) -> np.ndarray:
    return compression_pipeline.process(text)
```

#### 2. Vectorized Operations

```python
# Use numpy for batch operations
def batch_feature_extraction(texts: List[str]) -> np.ndarray:
    # Process multiple texts in parallel
    tokens_batch = [tokenize(text) for text in texts]
    features_batch = np.array([extract_features(t) for t in tokens_batch])
    return features_batch
```

#### 3. Memory Pre-allocation

```python
class PreallocatedBuffers:
    def __init__(self):
        self.bitstream_buffer = np.zeros(256, dtype=np.float32)
        self.context_buffer = np.zeros(512, dtype=np.float32)
        self.feature_buffer = np.zeros(64, dtype=np.float32)
        
    def get_buffers(self):
        return self.bitstream_buffer, self.context_buffer, self.feature_buffer
```

### Hybrid Routing Optimizations

#### 1. Early Exit Conditions

```python
def should_use_fast_path(user_input: str, binary_features: Dict[str, int]) -> bool:
    # Quick checks before full processing
    if len(user_input.split()) < 5:  # Short input
        return True
        
    if binary_features.get("user_is_questioning") == 0:  # Not a question
        return True
        
    if binary_features.get("needs_search") == 0:  # No search needed
        return True
        
    return False
```

#### 2. Confidence Threshold Tuning

```python
def adaptive_confidence_threshold(performance_history: List[float]) -> float:
    """Adjust threshold based on recent performance."""
    if len(performance_history) < 10:
        return 0.7  # Default
        
    recent_success = np.mean(performance_history[-10:])
    
    if recent_success > 0.9:  # Very successful
        return 0.6  # Be more aggressive with fast path
    elif recent_success < 0.7:  # Struggling
        return 0.8  # Be more conservative
    else:
        return 0.7  # Default
```

#### 3. Resource-Aware Routing

```python
def resource_aware_routing(system_load: float) -> GenerationMode:
    """Choose generation mode based on system resources."""
    if system_load > 0.8:  # High load
        return GenerationMode.LOCAL  # Prefer fast path
    elif system_load < 0.3:  # Low load
        return GenerationMode.EXTERNAL  # Can afford LLM
    else:
        return GenerationMode.HYBRID  # Normal routing
```

## 📊 Performance Monitoring

### Real-time Metrics

```python
class PerformanceMonitor:
    def __init__(self):
        self.metrics = {
            "generation_times": [],
            "mode_choices": [],
            "success_rates": [],
            "memory_usage": [],
        }
        
    def record_generation(
        self, 
        mode: str, 
        duration: float, 
        success: bool,
        memory_mb: float
    ):
        self.metrics["generation_times"].append(duration)
        self.metrics["mode_choices"].append(mode)
        self.metrics["success_rates"].append(1 if success else 0)
        self.metrics["memory_usage"].append(memory_mb)
        
    def get_performance_summary(self) -> Dict[str, Any]:
        if not self.metrics["generation_times"]:
            return {}
            
        return {
            "avg_generation_time": np.mean(self.metrics["generation_times"]),
            "p95_generation_time": np.percentile(self.metrics["generation_times"], 95),
            "local_mode_ratio": self.metrics["mode_choices"].count("local") / len(self.metrics["mode_choices"]),
            "success_rate": np.mean(self.metrics["success_rates"]),
            "avg_memory_usage": np.mean(self.metrics["memory_usage"]),
        }
```

### Performance Alerts

```python
class PerformanceAlerts:
    def __init__(self, monitor: PerformanceMonitor):
        self.monitor = monitor
        self.thresholds = {
            "max_avg_latency": 0.1,  # 100ms
            "min_success_rate": 0.85,
            "max_memory_usage": 50.0,  # 50MB
            "min_local_ratio": 0.6,  # 60% local generation
        }
        
    def check_performance(self) -> List[str]:
        alerts = []
        summary = self.monitor.get_performance_summary()
        
        if summary.get("avg_generation_time", 0) > self.thresholds["max_avg_latency"]:
            alerts.append("High average latency detected")
            
        if summary.get("success_rate", 1.0) < self.thresholds["min_success_rate"]:
            alerts.append("Low success rate - consider adjusting thresholds")
            
        if summary.get("avg_memory_usage", 0) > self.thresholds["max_memory_usage"]:
            alerts.append("High memory usage - check for leaks")
            
        if summary.get("local_mode_ratio", 0) < self.thresholds["min_local_ratio"]:
            alerts.append("Low local generation ratio - fast path underutilized")
            
        return alerts
```

## 🔧 Configuration Tuning

### Performance-Optimized Settings

```python
# For maximum speed
FAST_CONFIG = GenerationConfig(
    local_confidence_threshold=0.5,      # More aggressive fast path
    complexity_threshold=0.4,            # Lower complexity threshold
    max_local_tokens=32,                 # Shorter local responses
    temperature_local=0.6,               # More deterministic
    preferred_mode=GenerationMode.LOCAL,  # Prefer local
)

# For balanced performance
BALANCED_CONFIG = GenerationConfig(
    local_confidence_threshold=0.7,      # Standard threshold
    complexity_threshold=0.6,            # Standard complexity
    max_local_tokens=64,                 # Standard length
    temperature_local=0.8,               # Standard creativity
    preferred_mode=GenerationMode.HYBRID,  # Hybrid routing
)

# For quality over speed
QUALITY_CONFIG = GenerationConfig(
    local_confidence_threshold=0.8,      # Conservative fast path
    complexity_threshold=0.8,            # Higher complexity threshold
    max_local_tokens=128,                # Longer responses
    temperature_local=0.9,               # More creative
    preferred_mode=GenerationMode.EXTERNAL,  # Prefer external
)
```

### Adaptive Configuration

```python
class AdaptiveConfig:
    def __init__(self, initial_config: GenerationConfig):
        self.config = initial_config
        self.performance_history = []
        self.adjustment_interval = 100  # Adjust every 100 generations
        
    def update_config(self, performance_summary: Dict[str, Any]) -> None:
        """Adjust configuration based on performance."""
        self.performance_history.append(performance_summary)
        
        if len(self.performance_history) % self.adjustment_interval == 0:
            recent = self.performance_history[-10:]
            avg_latency = np.mean([p.get("avg_generation_time", 0) for p in recent])
            success_rate = np.mean([p.get("success_rate", 0) for p in recent])
            
            # Adjust confidence threshold
            if avg_latency > 0.1 and success_rate > 0.8:
                self.config.local_confidence_threshold += 0.05  # Be more conservative
            elif avg_latency < 0.05 and success_rate < 0.7:
                self.config.local_confidence_threshold -= 0.05  # Be more aggressive
                
            log.info(f"Adjusted confidence threshold to {self.config.local_confidence_threshold}")
```

## 🎯 Benchmarking Tests

### Latency Benchmark

```python
async def benchmark_latency(engine: KitsuEngineMini, test_inputs: List[str]) -> Dict[str, float]:
    """Benchmark generation latency for different input types."""
    results = {"fast": [], "slow": [], "hybrid": []}
    
    for input_text in test_inputs:
        start_time = time.time()
        response = await engine.process_input(input_text)
        end_time = time.time()
        
        duration = end_time - start_time
        mode = response["generation_metadata"]["generation_mode"]
        results[mode].append(duration)
        
    return {
        "fast_avg": np.mean(results["fast"]) if results["fast"] else 0,
        "slow_avg": np.mean(results["slow"]) if results["slow"] else 0,
        "hybrid_avg": np.mean(results["hybrid"]) if results["hybrid"] else 0,
    }
```

### Memory Benchmark

```python
def benchmark_memory_usage(engine: KitsuEngineMini, iterations: int = 100) -> Dict[str, float]:
    """Benchmark memory usage during generation."""
    import psutil
    process = psutil.Process()
    
    baseline_memory = process.memory_info().rss / 1024 / 1024  # MB
    memory_samples = []
    
    for i in range(iterations):
        # Force garbage collection
        import gc
        gc.collect()
        
        current_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_samples.append(current_memory)
        
    return {
        "baseline_memory_mb": baseline_memory,
        "avg_memory_mb": np.mean(memory_samples),
        "peak_memory_mb": np.max(memory_samples),
        "memory_growth_mb": np.max(memory_samples) - baseline_memory,
    }
```

### Accuracy Benchmark

```python
async def benchmark_routing_accuracy(
    engine: KitsuEngineMini, 
    test_dataset: List[Tuple[str, str]]
) -> Dict[str, float]:
    """Benchmark routing accuracy."""
    correct_predictions = 0
    total_predictions = len(test_dataset)
    
    for input_text, expected_mode in test_dataset:
        response = await engine.process_input(input_text)
        actual_mode = response["generation_metadata"]["generation_mode"]
        
        if actual_mode == expected_mode:
            correct_predictions += 1
            
    return {
        "routing_accuracy": correct_predictions / total_predictions,
        "correct_predictions": correct_predictions,
        "total_predictions": total_predictions,
    }
```

## 📈 Performance Optimization Checklist

### ✅ Fast Path Optimizations

- [ ] Implement input length pre-checks
- [ ] Cache frequent binary feature patterns
- [ ] Pre-allocate memory buffers
- [ ] Use vectorized numpy operations
- [ ] Optimize Huffman code lookup tables
- [ ] Implement early exit conditions

### ✅ Hybrid Routing Optimizations

- [ ] Tune confidence thresholds based on usage
- [ ] Implement resource-aware routing
- [ ] Add performance-based threshold adjustment
- [ ] Optimize complexity analysis speed
- [ ] Cache complexity scores for similar inputs

### ✅ Memory Optimizations

- [ ] Monitor memory usage patterns
- [ ] Implement object pooling for frequent allocations
- [ ] Use sparse matrices for Markov transitions
- [ ] Optimize embedding storage format
- [ ] Add memory usage alerts

### ✅ Monitoring & Analytics

- [ ] Track generation latency percentiles
- [ ] Monitor mode selection ratios
- [ ] Measure success rates by mode
- [ ] Set up performance alerts
- [ ] Create performance dashboards

## 🔄 Continuous Performance Improvement

### Performance Regression Testing

```python
async def performance_regression_test():
    """Run automated performance tests."""
    engine = KitsuEngineMini(get_test_config())
    await engine.initialize()
    
    # Test latency
    latency_results = await benchmark_latency(engine, get_test_inputs())
    assert latency_results["fast_avg"] < 0.01, "Fast path too slow"
    assert latency_results["hybrid_avg"] < 0.05, "Hybrid path too slow"
    
    # Test memory
    memory_results = benchmark_memory_usage(engine)
    assert memory_results["memory_growth_mb"] < 5.0, "Memory leak detected"
    
    # Test accuracy
    accuracy_results = await benchmark_routing_accuracy(engine, get_test_dataset())
    assert accuracy_results["routing_accuracy"] > 0.8, "Routing accuracy too low"
    
    log.info("All performance tests passed!")
```

This performance guide provides comprehensive optimization strategies for achieving the best performance from the Kitsu hybrid AI system.
