# ML System Integration Guide

## Architecture Overview

```bash
┌─────────────────────────────────────────────────────────┐
│                    RUNTIME LAYER                        │
│  (NO FILE I/O, models injected, fast inference)         │
└─────────────────────────────────────────────────────────┘
core/ml/inference/
  ├─ base_predictor.py       ✅ Base interface
  ├─ intent_predictor.py     ✅ Intent classification
  ├─ emotion_predictor.py    ✅ Emotion detection
  └─ policy_predictor.py     ✅ Policy selection

controller/meta/
  └─ meta_controller.py      ✅ Orchestrates predictions

manager/ml/
  └─ model_state_manager.py  ✅ Holds loaded models

┌─────────────────────────────────────────────────────────┐
│                     I/O LAYER                           │
│  (File operations only, no logic)                       │
└─────────────────────────────────────────────────────────┘
io/ml/
  ├─ model_loader.py         ✅ Load models from disk
  └─ model_saver.py          ✅ Save models to disk

┌─────────────────────────────────────────────────────────┐
│                   TRAINING LAYER                         │
│  (Batch jobs, file I/O allowed)                         │
└─────────────────────────────────────────────────────────┘
data/ml/
  ├─ trainers/
  │   ├─ intent_trainer.py   ✅ Train intent model
  │   ├─ emotion_trainer.py  ✅ Train emotion model
  │   └─ policy_trainer.py   ✅ Train policy model
  ├─ dataset_builder.py      ✅ Build training datasets
  ├─ session_logger.py       ✅ Log interactions
  └─ nightly_job.py          ✅ Orchestrate batch jobs
```

## Startup Flow (main.py)

```python
# main.py or launcher.py

from pathlib import Path

# 1. Create I/O layer
from io.ml.model_loader import ModelLoader
model_loader = ModelLoader(models_dir=Path("data/models/ml"))

# 2. Create state manager
from manager.ml.model_state_manager import ModelStateManager
model_state = ModelStateManager(model_loader=model_loader)

# 3. Load models at startup
model_state.load_model("intent_classifier", version="v1")
model_state.load_model("emotion_classifier", version="v1")

# Load policy models (special multi-model case)
policy_data = model_loader.load_policy_models("policy_selector", "v1")
if policy_data:
    model_state.register_model(
        "policy_selector",
        model=policy_data["models"],
        version="v1",
        feature_engineer=policy_data["feature_engineer"],
        metadata=policy_data["metadata"]
    )

# 4. Create predictors (inject models from state manager)
from core.ml.inference.base_predictor import (
    IntentPredictor,
    EmotionPredictor,
    PolicyPredictor
)

intent_predictor = IntentPredictor(
    model=model_state.get_model("intent_classifier"),
    feature_engineer=model_state.get_feature_engineer("intent_classifier")
)

emotion_predictor = EmotionPredictor(
    model=model_state.get_model("emotion_classifier"),
    feature_engineer=model_state.get_feature_engineer("emotion_classifier")
)

policy_predictor = PolicyPredictor(
    model=model_state.get_model("policy_selector"),
    feature_engineer=model_state.get_feature_engineer("policy_selector")
)

# 5. Create meta controller (inject predictors)
from controller.meta.meta_controller import MetaController, SafetyGate

meta_controller = MetaController(
    intent_predictor=intent_predictor,
    emotion_predictor=emotion_predictor,
    policy_predictor=policy_predictor,
    safety_gate=SafetyGate(),
    confidence_threshold=0.6
)

# 6. Now meta_controller is ready to use!
# It has NO file I/O, all models injected
```

## Runtime Usage

```python
# In your chat loop or request handler

# Make a decision
decision = meta_controller.decide(
    user_input="Hello, how are you?",
    context={
        "mood": "behave",
        "style": "chaotic",
        "wizard_mode": False,
        "user_trust": 0.8,
        "user_affinity": 0.7,
        "messages_sent": 10,
        "recent_errors": 0
    }
)

# Use decision
print(f"Mode: {decision.mode}")           # e.g., "llm"
print(f"Emotion: {decision.emotion}")     # e.g., "happy"
print(f"LoRA: {decision.lora}")          # e.g., "playful"
print(f"Confidence: {decision.confidence}") # e.g., 0.85
print(f"Time: {decision.processing_time_ms}ms") # e.g., 15.2

# Based on decision, route to appropriate response generator
if decision.mode == "sass":
    response = sass_generator.generate(user_input)
elif decision.mode == "fallback":
    response = fallback_generator.generate(user_input)
else:
    response = llm_interface.generate(user_input, lora=decision.lora)
```

## Hot Reload (Runtime)

```python
# Hot reload a model without restart
success = model_state.hot_reload("emotion_classifier", version="v2")

if success:
    # Update predictor with new model
    emotion_predictor = EmotionPredictor(
        model=model_state.get_model("emotion_classifier"),
        feature_engineer=model_state.get_feature_engineer("emotion_classifier")
    )
    
    # Update meta controller
    meta_controller.emotion_predictor = emotion_predictor
    
    print("✅ Hot reloaded emotion_classifier v2")
```

## Training (Batch Job)

```python
# data/ml/trainers/intent_trainer.py

from data.ml.dataset_builder import DatasetBuilder
from io.ml.model_saver import ModelSaver
from sklearn.linear_model import LogisticRegression
from core.ml.feature_engineering import FeatureEngineer

def train_intent_classifier():
    # 1. Load training data
    builder = DatasetBuilder()
    df = builder.read_session_logs(Path("data/logs/sessions"))
    
    # Extract texts and labels
    texts = df["input_clean"].tolist()
    labels = df["intent"].tolist()
    
    # 2. Train feature engineer
    fe = FeatureEngineer(max_features=3000)
    fe.fit(texts, intents=labels)
    
    # 3. Transform features
    X = fe.transform_text(texts)
    
    # 4. Train model
    model = LogisticRegression(
        max_iter=1000,
        multi_class='multinomial'
    )
    model.fit(X, labels)
    
    # 5. Save (using io/ layer)
    saver = ModelSaver()
    saver.save_model(
        model_name="intent_classifier",
        model=model,
        version="v1",
        feature_engineer=fe,
        metadata={
            "training_samples": len(texts),
            "accuracy": 0.85  # from evaluation
        }
    )
    
    print("✅ Trained and saved intent_classifier v1")

# Run in nightly job
if __name__ == "__main__":
    train_intent_classifier()
```

## Nightly Job Flow

```python
# data/ml/nightly_job.py

async def run_nightly_job():
    # 1. Build datasets from logs
    builder = DatasetBuilder()
    train_df, val_df, test_df = builder.build_dataset(
        log_dir=Path("data/logs/sessions"),
        output_dir=Path("data/datasets/v20250123")
    )
    
    # 2. Check if retraining needed
    if len(train_df) > 1000:  # Threshold
        # 3. Retrain models
        from data.ml.trainers import (
            train_intent_classifier,
            train_emotion_classifier,
            train_policy_selector
        )
        
        train_intent_classifier()
        train_emotion_classifier()
        train_policy_selector()
        
        # 4. Hot reload in production (if API available)
        # This would call the runtime system's hot reload endpoint
        # or write a flag file that triggers reload on next request
        
    print("✅ Nightly job complete")
```

## Key Benefits

### ✅ Clean Separation

- **Runtime**: Fast, no file I/O, models injected
- **Training**: Batch jobs, file I/O allowed
- **State**: Manager holds models, delegates I/O

### ✅ Testability

```python
# Easy to test - inject mock models
from unittest.mock import Mock

mock_model = Mock()
mock_model.predict.return_value = ["greeting"]

predictor = IntentPredictor(model=mock_model)
result = predictor.predict("hello")
assert result == "greeting"
```

### ✅ Hot Reload

- Models can be reloaded without restart
- Zero downtime deployments
- A/B testing support

### ✅ Performance

- Models loaded once at startup
- Fast inference (no file I/O)
- Optimized for low-spec hardware

## Migration Checklist

- [x] Move `core/ml/*.py` training logic to `data/ml/trainers/`
- [x] Create pure predictors in `core/ml/inference/`
- [x] Create state manager in `manager/ml/`
- [x] Create loaders/savers in `io/ml/`
- [x] Update `meta_controller.py` to inject models
- [ ] Update `main.py` to wire everything together
- [ ] Update nightly job to use trainers
- [ ] Test hot reload functionality
- [ ] Update documentation

## File Locations Summary

```bash
Runtime (NO file I/O):
  core/ml/inference/          - Predictors
  controller/meta/            - Meta controller
  manager/ml/                 - State management

I/O (File operations):
  io/ml/                      - Load/save models

Training (Batch jobs):
  data/ml/trainers/           - Training logic
  data/ml/dataset_builder.py  - Build datasets
  data/ml/nightly_job.py      - Orchestration

Supporting:
  core/ml/feature_engineering.py - Feature engineering (used by both)
  core/meta/action_parser.py     - Action parsing (runtime)
  core/meta/action_executor.py   - Action execution (runtime)
  core/meta/safety_gate.py       - Safety checks (runtime)
```
