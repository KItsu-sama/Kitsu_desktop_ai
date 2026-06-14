# Debug Mode - Complete Guide

## Overview

Debug mode provides comprehensive visibility into every step of Kitsu's response generation process. When enabled, you'll see detailed logs for:

- **Router decisions** - How requests are routed (REFLEX → SLM → LLM)
- **Reflex matching** - Candidate retrieval, scores, and selection
- **Response cache** - Cache hits, misses, and storage decisions
- **Personality changes** - Mood, emotion, and trigger effects
- **Response pipeline** - Each stage of processing with millisecond timing

## Quick Start

### Enable Debug Mode
```
/debug on
```

You'll see logs like:
```
[14:32:45.127] [ROUTER        ] DECIDE        | route=REFLEX      confidence=100% reason=cache_hit
[14:32:45.128] [REFLEX        ] CACHE_HIT     | group=CACHE score=1.000
[14:32:45.128] [PIPELINE      ] PROCESS       | Reflex complete | response ready in 2.1ms
```

### Disable Debug Mode
```
/debug off
```

### Check Status
```
/debug
```

## Debug Commands

### Comprehensive View
```
/debug view
```
Shows complete overview of all systems including:
- Router configuration
- Reflex matching pipeline
- Cache statistics
- Personality/emotion state
- Performance tips

### Router Details
```
/debug router
```
Shows:
- Routing pipeline (REFLEX → SLM → LLM)
- Routing decision logic
- Complexity scoring
- Fast template list

### Reflex Details
```
/debug reflex
```
Shows:
- Matching algorithm
- Scoring components (SimHash, trigrams, tokens)
- Candidate retrieval process
- Response selection
- Judge validation

### Cache Details
```
/debug cache
```
Shows:
- Cache file location
- Entry count and capacity
- Average quality score
- Cache operation details

### Personality Details
```
/debug personality
```
Shows:
- Current mood, style, state
- Dominant emotion
- Energy and trust levels
- Personality traits
- Mood and style definitions

## Understanding the Debug Output

### Format
```
[TIMESTAMP] [COMPONENT] ACTION | DETAILS
```

- **TIMESTAMP**: `HH:MM:SS.mmm` (millisecond precision)
- **COMPONENT**: System name (ROUTER, REFLEX, PERSONALITY, etc)
- **ACTION**: What happened (DECIDE, MATCH, CACHE_HIT, CHANGE, etc)
- **DETAILS**: Context-specific information

### Timing Format
- `12.3ms` - milliseconds
- `150μs` - microseconds (< 1ms)
- `2.45s` - seconds

### Response Flow Example

When you send "Hello!":

```
[14:32:45.123] [ROUTER        ] DECIDE        | route=REFLEX confidence=100% reason=template_match
```
→ Router recognized "hello" as template, routing to REFLEX

```
[14:32:45.124] [REFLEX        ] CACHE_HIT     | group=CACHE score=1.000
```
→ Found exact match in reflex cache

```
[14:32:45.124] [PIPELINE      ] PROCESS       | Reflex complete | response ready in 1.2ms
```
→ Response ready from reflex cache (fastest path!)

## Key System Components

### 1. ROUTER (Request Entry Point)
Decides which path to take:

**Logs you'll see:**
- `DECIDE` - Routing decision made
- `ROUTE` - Path selected (REFLEX/SLM/LLM)

**What it does:**
1. Checks reflex cache for exact match → REFLEX_PATH
2. Checks template list → REFLEX_PATH
3. Scores complexity of query
4. Low complexity (< 0.3) → SLM_PATH
5. High complexity (≥ 0.3) → LLM_PATH

**Example:**
```
[ROUTER] DECIDE | route=REFLEX confidence=100% reason=cache_hit
```

### 2. REFLEX (Pattern Matching)
Matches queries to pre-written responses:

**Logs you'll see:**
- `CANDIDATES` - How many groups matched
- `DETAIL` - Details of top 3 matches
- `MATCH` or `NO_MATCH` - Success or failure
- `CACHE_HIT` - Instant cache response

**What it does:**
1. Computes SimHash of query
2. Checks learned cache (fastest)
3. Scores all response groups
4. Picks best match(es)
5. Runs judge validation
6. Returns response

**Example:**
```
[REFLEX] CANDIDATES | found 3 candidate(s), top_score=0.857
[REFLEX] DETAIL | group=greetings triggers=5 avg_score=0.710
[REFLEX] ✓ MATCH | score=0.857 threshold=0.350 group=greetings
```

### 3. JUDGE (Quality Validation)
Checks if responses are appropriate:

**Logs you'll see:**
- `PASS` - Quality check passed
- `FAIL` - Quality check failed

**What it checks:**
- Tone appropriateness for personality
- Confidence scoring (0.0-1.0)

**Example:**
```
[JUDGE] ✓ PASS | score=0.92 threshold=0.80 reason=tone_validation
```

### 4. MEMORY (Response Cache)
Learns from high-quality LLM responses:

**Logs you'll see:**
- `CACHE_HIT` - Cache lookup found response
- `GET` - Cache lookup operation
- `PUT` - Cache storage decision
- `QUALITY_HIT` - High-quality response being cached
- `QUALITY_MISS` - Response not worth caching

**What it does:**
1. Stores high-quality LLM responses
2. Uses SimHash as cache key
3. LRU eviction (max 10,000 entries)
4. Only caches quality ≥ 0.8

**Example:**
```
[MEMORY] CACHE_HIT | GET hash=a1b2c3d4... cached=True
[MEMORY] QUALITY_HIT | LLM response quality=0.92 - caching
[MEMORY] CACHE_PUT | hash=a1b2c3d4... quality=0.92 text='response...'
```

### 5. PERSONALITY (Mood & Emotion)
Tracks emotional state and personality changes:

**Logs you'll see:**
- `CHANGE` - Mood or emotion changed

**What it tracks:**
- Mood (behave, mean, flirty, protective)
- Style (chaotic, sweet, cold, direct, etc)
- Dominant emotion
- Emotion stack
- Trigger effects

**Example:**
```
[PERSONALITY] CHANGE | emotion=happy mood=flirty style=playful trigger=manual_set_mood
```

### 6. ESCALATE (Stage Transitions)
When advancing to next processing stage:

**Logs you'll see:**
- `→ NEXT` - Escalating to next stage

**Common reasons:**
- `budget exceeded` - Time limit reached
- `no candidates matched` - REFLEX found nothing
- `judge rejected` - Quality too low
- `tool unavailable` - Requested tool missing

**Example:**
```
[ESCALATE] → NEXT | reason=no_candidates_matched from=REFLEX
```

### 7. PIPELINE (Overall Processing)
Shows major stages of response generation:

**Logs you'll see:**
- `PROCESS` - Stage beginning/completion

**Example:**
```
[PIPELINE] PROCESS | Retrieving candidates
[PIPELINE] PROCESS | Invoking tool: clock.now
[PIPELINE] PROCESS | Reflex complete | response ready in 45.2ms
```

## Understanding the Response Paths

### Fast Path (REFLEX Cache) - ✨ Fastest
```
Input → CACHE HIT → Response (1-3ms)
```
Used when:
- Query exactly matches cached response
- Template match (hi, hello, what time is it, etc)

### Reflex Path - ⚡ Fast
```
Input → REFLEX MATCHING → JUDGE → Response (5-50ms)
```
Used when:
- Low complexity query with pattern match
- Medium complexity with high match score
- Budget allows

### SLM Path - 🔄 Medium
```
Input → LIGHTWEIGHT LLM → JUDGE → Response (100-500ms)
```
Used when:
- Low complexity query without pattern match
- Budget constraints
- Intermediate processing needed

### LLM Path - 🧠 Full Processing
```
Input → FULL LLM → JUDGE → CACHE (if good) → Response (500-2000ms)
```
Used when:
- High complexity query
- Reasoning required
- Creative response needed
- Teaching/learning scenario

## Performance Optimization with Debug

### Watch For:
1. **Frequent REFLEX cache hits** - Good! Responses are being reused
2. **Fast REFLEX responses** (< 50ms) - Excellent! Pattern matching working
3. **Escalations from REFLEX** - Check reasons (judge rejected? no match?)
4. **QUALITY_HIT logs** - Responses being learned for future use
5. **High average quality** in cache stats - Good learning

### Red Flags:
1. **Many escalations** - Responses not matching patterns
2. **Low cache hit rate** - Patterns not covering queries
3. **Low quality scores** - Responses need review
4. **Frequent "judge rejected"** - Responses off-tone
5. **Large response times** - Budget issues or complex queries

## Example Debug Session

```
User: "Hey there!"
[14:32:45.123] [ROUTER] DECIDE | route=REFLEX confidence=95% reason=template_match
[14:32:45.124] [REFLEX] CACHE_HIT | group=CACHE score=1.000
[14:32:45.124] [PIPELINE] PROCESS | Reflex complete | response ready in 1.2ms

User: "What's the meaning of life?"
[14:32:47.456] [ROUTER] ROUTE | COMPLEXITY → LLM_PATH conf=78% (high complexity=0.780)
[14:32:47.457] [REFLEX] CANDIDATES | found 0 candidate(s), top_score=0.000
[14:32:47.458] [ESCALATE] → NEXT | reason=no_candidates_matched from=REFLEX
[14:32:49.234] [JUDGE] ✓ PASS | score=0.91 threshold=0.80 reason=tone_validation
[14:32:49.235] [MEMORY] QUALITY_HIT | LLM response quality=0.91 - caching
[14:32:49.236] [MEMORY] CACHE_PUT | hash=abc123... quality=0.91 text='The meaning of life...'
[14:32:49.236] [PIPELINE] PROCESS | LLM complete | response ready in 1780.0ms
```

## Troubleshooting

### "Why is my response from LLM instead of REFLEX?"
Look for:
- `ESCALATE → NEXT | reason=no_candidates_matched` - Pattern not trained yet
- `ESCALATE → NEXT | reason=judge_rejected` - Response tone doesn't match
- Complex query detected - High complexity score triggered SLM/LLM

### "Why is my response slow?"
Look for:
- `LLM_PATH` routing - Full model inference needed (expected: 500-2000ms)
- Multiple escalations - Try simpler queries
- Budget checks - Some stages may be skipped

### "How do I train reflex to recognize this pattern?"
- Use `/rate` command after reflex responses you like
- Use `/train` to fine-tune responses
- Cache hits get better over time with `/rate` feedback

## Advanced Features

### Cache Statistics
```
/debug cache
```
Shows:
- Entry count / max capacity
- Cache usage percentage
- Average quality of cached responses

### Personality State
```
/debug personality
```
Shows:
- Current mood (behave/mean/flirty/protective)
- Current style (chaotic/sweet/cold/direct/sarcastic/playful/eerie)
- Emotion stack depth
- Energy and trust levels

### Live Monitoring
Keep `/debug on` while:
- Testing reflex patterns
- Training new responses
- Debugging quality issues
- Analyzing response times

## Environment Variables

Can be set to customize debug behavior:

- `REFLEX_MATCH_THRESHOLD=0.35` - Matching score threshold
- `LOG_LEVEL=DEBUG` - Python logging level

## See Also

- `/stats` - Memory and system statistics
- `/state` - Current emotional state
- `/mood` - Personality commands
- `/train` - Response training
- `/rate` - Quality feedback
