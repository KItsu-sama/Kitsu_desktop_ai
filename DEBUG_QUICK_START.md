# 🐛 Debug Mode - Quick Start

## What's New

Your Kitsu system now has **comprehensive debug logging** that shows everything happening during response generation with **millisecond-precision timing**.

## Quick Start (30 seconds)

### 1. Enable Debug Mode
```bash
/debug on
```

### 2. Send a Message
```
User: "Hello!"
```

You'll see something like:
```
[14:32:45.123] [ROUTER        ] DECIDE        | route=REFLEX confidence=100%
[14:32:45.124] [REFLEX        ] CACHE_HIT     | group=CACHE score=1.000
[14:32:45.125] [JUDGE         ] ✓ PASS        | score=0.95 threshold=0.80
[14:32:45.126] [PIPELINE      ] PROCESS       | Reflex complete | response ready in 3.2ms
```

### 3. Explore More Details
```bash
/debug view         # Full system overview
/debug router       # Routing details
/debug reflex       # Matching algorithm
/debug cache        # Cache statistics
/debug personality  # Mood & emotions
```

### 4. Disable When Done
```bash
/debug off
```

## What You'll See

### 🧭 Router Decisions
- **Route chosen**: REFLEX (fast), SLM (medium), or LLM (full model)
- **Confidence**: How certain about the decision
- **Reason**: Why that route was chosen

### 📦 Reflex Matching
- **Candidates found**: How many patterns matched
- **Match score**: Quality of the match (0.0-1.0)
- **Cache hits**: Fast path response reuse

### 💾 Response Cache
- **GET/PUT**: Cache operations
- **Quality score**: Response quality (0.0-1.0)
- **Storage**: When responses are cached

### 🎭 Personality Changes
- **Mood**: behave, mean, flirty, protective
- **Style**: chaotic, sweet, cold, direct, etc
- **Triggers**: What caused the change

### ⚙️ Processing Stages
- **Retrieval**: Finding candidate responses
- **Matching**: Finding best match
- **Judge**: Quality validation
- **Response**: Ready to send

## Timing Guide

| Time | Meaning |
|------|---------|
| **1-3ms** | Cache hit (fastest!) |
| **5-50ms** | Pattern matched response |
| **100-500ms** | Lightweight processing |
| **500-2000ms** | Full model (expected) |

## Key Insights

### 📊 What to Watch For
- **Cache hits** 🎯 = Responses being reused (excellent!)
- **Fast times** ⚡ = System performing well
- **Escalations** 📤 = Moving to more complex processing
- **Quality scores** 💎 = Learning and improving

### 🔍 Common Patterns

**Fast Response** (< 5ms):
```
[ROUTER] DECIDE | route=REFLEX
[REFLEX] CACHE_HIT | group=CACHE score=1.000
```

**Pattern Match** (5-50ms):
```
[REFLEX] CANDIDATES | found 3 candidate(s)
[REFLEX] ✓ MATCH | score=0.857
```

**Complex Query** (500-2000ms):
```
[ROUTER] ROUTE | COMPLEXITY → LLM_PATH
[ESCALATE] → NEXT | reason=complex_query
```

## Documentation

Read more about:
- **Quick Reference**: `DEBUG_MODE_REFERENCE.md`
- **Full Guide**: `DEBUG_MODE_GUIDE.md`
- **Implementation**: `DEBUG_MODE_IMPLEMENTATION.md`

## All Debug Commands

```bash
# Control
/debug on              # Enable
/debug off             # Disable
/debug                 # Status

# Information
/debug view            # Everything
/debug router          # Router config
/debug reflex          # Matching system
/debug cache           # Cache status
/debug personality     # Emotions
```

## Try It Now! 🚀

```bash
/debug on
```

Then start chatting and watch the magic happen! ✨

You'll see:
- Where your responses come from
- How fast they're generated
- What patterns are matched
- How personality affects responses
- How cache improves performance over time

## Tips

✅ **Enable debug** to understand how Kitsu processes requests
✅ **Watch for cache hits** - they're the fastest!
✅ **Monitor escalations** - understand routing decisions
✅ **Check personality** - see mood and emotion state
✅ **Use /debug view** - quick system overview

## Questions?

- Read `DEBUG_MODE_GUIDE.md` for comprehensive guide
- Check `DEBUG_MODE_REFERENCE.md` for quick reference
- See `DEBUG_MODE_IMPLEMENTATION.md` for technical details

---

**Happy debugging! 🐛**
