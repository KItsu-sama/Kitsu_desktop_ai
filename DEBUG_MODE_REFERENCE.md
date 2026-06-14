# Debug Mode - Quick Reference Card

## Commands

### Enable/Disable
```bash
/debug on              # Enable detailed logging
/debug off             # Disable logging
/debug                 # Show current status
```

### Information Views
```bash
/debug view            # Comprehensive system overview
/debug router          # Router configuration & routing pipeline
/debug reflex          # Reflex matching system details
/debug cache           # Response cache statistics
/debug personality     # Emotion & mood state
```

## What Gets Logged

### Router
```
🧭 ROUTER - Request routing decisions
  [ROUTER] DECIDE | route=REFLEX confidence=100% reason=cache_hit
  [ROUTER] ROUTE  | COMPLEXITY → LLM_PATH conf=65% (high complexity)
```

### Reflex Matching
```
📦 REFLEX - Pattern matching & response selection
  [REFLEX] CANDIDATES | found 3 candidate(s), top_score=0.857
  [REFLEX] DETAIL     | group=greetings avg_score=0.710
  [REFLEX] ✓ MATCH    | score=0.857 threshold=0.350 group=greetings
  [REFLEX] CACHE_HIT  | group=CACHE score=1.000
```

### Cache Operations
```
💾 MEMORY - Response cache management
  [MEMORY] GET         | hash=a1b2c3d4... cached=True
  [MEMORY] CACHE_HIT   | cache entry found
  [MEMORY] CACHE_PUT   | hash=a1b2c3d4... quality=0.92
  [MEMORY] QUALITY_HIT | LLM response quality=0.92 - caching
```

### Personality Changes
```
🎭 PERSONALITY - Mood, emotion, triggers
  [PERSONALITY] CHANGE | emotion=happy mood=flirty style=playful
```

### Judge & Escalation
```
⚖️ JUDGE - Quality validation
  [JUDGE] ✓ PASS | score=0.92 threshold=0.80 reason=tone_validation
  
📤 ESCALATE - Stage transitions
  [ESCALATE] → NEXT | reason=no_candidates from=REFLEX
```

### Pipeline Stages
```
🔄 PIPELINE - Response processing stages
  [PIPELINE] PROCESS | Retrieving candidates
  [PIPELINE] PROCESS | Running judge
  [PIPELINE] PROCESS | Reflex complete | response ready in 45.2ms
```

## Response Routing Paths

### 1. Cache Path (⚡ 1-3ms) - Fastest
```
Input → Cache Hit → Response
```
Triggers:
- Exact query match in cache
- Template match (hi, hello, etc)

### 2. Reflex Path (⚡ 5-50ms) - Fast
```
Input → Pattern Matching → Judge → Response
```
Triggers:
- Low complexity + pattern match
- Pre-trained response groups

### 3. SLM Path (🔄 100-500ms) - Medium
```
Input → Lightweight LLM → Judge → Response
```
Triggers:
- Low complexity without pattern
- Budget constraints

### 4. LLM Path (🧠 500-2000ms) - Full
```
Input → Full LLM → Judge → Cache → Response
```
Triggers:
- High complexity queries
- Reasoning required
- Creative responses

## Timing Format

| Format | Meaning |
|--------|---------|
| `12.3ms` | Milliseconds |
| `150μs` | Microseconds (< 1ms) |
| `2.45s` | Seconds |

## Performance Targets

| Path | Target Time | Status |
|------|------------|--------|
| Cache | 1-3ms | ✓ Excellent |
| Reflex | 5-50ms | ✓ Good |
| SLM | 100-500ms | ✓ Acceptable |
| LLM | 500-2000ms | ✓ Expected |

## Debugging Common Issues

### Slow responses?
- Look for `LLM_PATH` routing (expected to be slow)
- Check for multiple escalations
- Verify budget is sufficient

### Responses from LLM instead of REFLEX?
- Check for `no_candidates_matched` escalation
- Verify pattern is trained with `/train`
- Look for `judge_rejected` (tone issues)

### Low cache hit rate?
- New patterns not in cache yet
- Use `/rate` to mark good responses
- Use `/train` to teach new patterns

### Quality issues?
- Look at judge scores in logs
- Check for `judge_rejected` escalations
- Review `/debug personality` state

## Integration Points

### Logging
- Uses Python `logging` module
- Log level: DEBUG when enabled
- Output to terminal in real-time

### Timing
- Millisecond precision timestamps
- Automatic duration calculation
- Performance metrics included

### Components Traced
1. **Router** - Routing decisions
2. **Reflex** - Pattern matching
3. **Memory** - Cache operations
4. **Personality** - Mood changes
5. **Judge** - Quality scores
6. **Pipeline** - Stage progression

## Sample Output

```
[14:32:45.123] [ROUTER        ] DECIDE        | route=REFLEX confidence=100%
[14:32:45.124] [REFLEX        ] CACHE_HIT     | group=CACHE score=1.000
[14:32:45.125] [JUDGE         ] ✓ PASS        | score=0.95 threshold=0.80
[14:32:45.126] [PIPELINE      ] PROCESS       | Reflex complete | 3.2ms
```

## File Reference

- **Debug Config**: `shared/debug_timer.py`
- **Router Enhancement**: `application/modules/router.py`
- **Reflex Enhancement**: `application/modules/reflex.py`
- **Memory Enhancement**: `application/modules/memory.py`
- **Personality Enhancement**: `domain/personality/emotion_engine.py`
- **Command Router**: `application/commands/command_router.py`
- **Full Guide**: `DEBUG_MODE_GUIDE.md`

## Tips & Tricks

✓ Enable debug to **monitor reflex learning** via cache hits
✓ Watch for **escalation patterns** to understand weak points
✓ Use **/debug cache** to verify responses being learned
✓ Monitor **judge scores** to tune personality
✓ Compare **timing** across response types
✓ Track **emotion changes** in real-time
