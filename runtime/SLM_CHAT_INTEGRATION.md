# SLM Integration in Chat Loop

## Overview

The chat loop now has a working **Small Language Model (SLM)** tier integrated into the response generation pipeline. This enables fast, personality-aware responses before escalating to the heavier LLM tier.

## Architecture

### Updated Pipeline

The response generation now follows this tiered approach:

```
User Input
    ↓
Chat Loop (_chat_loop)
    ↓
process_input()
    ├─ Emotion Engine (pure Python)
    ├─ Intent Router (pure Python)
    ├─ Binary Reasoner (pure Python)
    ├─ Memory Retrieval (if needed)
    ↓
Response Generation (TWO PATHS):
    
PATH A - Compressed (if enabled):
    _generate_compressed()
        ├─ SLM (Ollama - fast, personality-aware)
        ├─ LLM (Ollama - fallback if SLM confidence low)
        └─ Personality Fallback (if all else fails)

PATH B - Fallback (default):
    _generate_fallback()
        ├─ SLM (Ollama - fast, personality-aware) ← NEW TIER
        ├─ LLM (Ollama - fallback if needed)
        └─ Personality Fallback (if all else fails)
    ↓
ResponseReady Event
    ↓
Display to User
```

## Key Changes

### 1. **SLM Tier in `_generate_fallback()` Method**

**Location:** [core/orchestrator.py](core/orchestrator.py#L977)

The fallback response generation now checks SLM first:

```python
# Tier 1: SLM (Small Language Model)
if self.slm:
    # Advanced interface with confidence scoring
    if hasattr(self.slm, 'infer_with_confidence'):
        response, confidence = await self.slm.infer_with_confidence(user_input, context)
        if response and not self.slm.needs_llm_escalation(confidence):
            return response  # Use SLM response
    # Fall back to basic query interface
    elif hasattr(self.slm, 'query'):
        response = self.slm.query(user_input, context)
        if response:
            return response  # Use SLM response

# Tier 2: LLM (only if SLM unavailable/failed)
if self.llm and self.llm.is_available():
    return self.llm.query(user_input)

# Tier 3: Personality fallback
return self.llm_fallback.generate(...)
```

### 2. **SLM Tier in `_generate_compressed()` Method**

**Location:** [core/orchestrator.py](core/orchestrator.py#L1093)

The compressed path also includes SLM:

```python
# Try SLM first in compression path
if self.slm:
    response = await self.slm.infer_with_confidence(...)
    if response and not confidence_too_low:
        return response  # Accept SLM response

# Escalate to LLM if needed
prompt = f"User: {user_input}\n..."
return self.llm.query(prompt)
```

### 3. **Personality Context Injection**

Both methods now pass personality/mood/style context to SLM:

```python
context = {
    "personality_hint": f"{mood or 'behave'}, {style or 'sweet'}",
    "mood": mood or "behave",
    "style": style or "sweet",
    "emotion_state": str(emotional_state),  # For compressed path
    "memory_context": memory_context or ""
}
```

This enables SLM to generate personality-aligned responses without needing full LLM inference.

## Flow Through Chat Loop

1. **User Input**: Text enters via `_chat_loop()`
2. **Processing**: `process_input()` runs emotional state analysis
3. **Response Generation**: 
   - Attempts SLM first (fast tier)
   - Falls back to LLM if SLM confidence is low
   - Uses personality fallback if both fail
4. **Response Ready Event**: Result published to bus
5. **Display**: Response shown to user with confidence info

## Configuration

SLM settings are in `config/ollama.yaml`:

```yaml
ollama:
  base_url: "http://localhost:11434"
  timeout: 30
  slm:
    model: "qwen2.5:1.5b"          # Small model
    temperature: 0.7
    top_p: 0.9
    max_tokens: 256                 # Fast, concise responses
    system_prompt: "You are Kitsu..."
  slm_confidence_threshold: 0.65    # Escalate if confidence < 65%
```

## Benefits

✅ **Faster Responses**: SLM generates in milliseconds vs LLM seconds  
✅ **Personality Aware**: Context passed to preserve character  
✅ **Graceful Escalation**: Automatically uses LLM for complex queries  
✅ **Reduced Costs**: Lower token usage with appropriate model tier  
✅ **Confidence-Based**: Only escalates when needed  

## Requirements

### Ollama Setup

SLM needs Ollama running locally:

```bash
# Start Ollama
ollama serve

# In another terminal, pull the small model
ollama pull qwen2.5:1.5b
```

### Models Required

- **SLM**: `qwen2.5:1.5b` (~1GB) — fast, good quality for Kitsu persona
- **LLM**: `llama3.2:3b` or similar — fallback for complex queries

## Testing

To verify SLM is working:

1. **Check logs**:
   ```
   SLM: Attempting fast response generation
   SLM: Response generated with confidence=0.85
   ```

2. **Test commands** (in chat):
   ```
   > hi
   > what's your name
   > tell me a joke
   ```

3. **Verify escalation** (should see in logs):
   ```
   SLM: Low confidence, escalating to LLM
   LLM: Attempting response generation
   ```

## Debugging

- **SLM not responding**: Check Ollama is running (`ollama serve`)
- **Wrong model**: Verify in `config/ollama.yaml`
- **Confidence too low**: Adjust `slm_confidence_threshold` in config
- **Slow responses**: SLM might be downloading model first run

## Future Improvements

- [ ] SLM fine-tuning on Kitsu persona data
- [ ] Confidence score visualization
- [ ] Per-intent SLM model selection
- [ ] Batch inference for performance
- [ ] SLM → FastBrain feedback loop

---

**Pipeline Visualization**: See [personality/VECTOR_SYSTEM_README.md](VECTOR_SYSTEM_README.md) for full architecture.
