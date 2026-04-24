# FastBrain Architecture

## Concept Explanation
FastBrain is Kitsu's base layer for instant response generation. It uses a combination of:
- **Binary encoding** for efficient storage
- **Markov chains** for pattern prediction
- **Huffman compression** for space optimization

## How it applies to Kitsu
- **Instant responses**: 0ms latency for common inputs
- **Self-learning**: Promotes frequent inputs via `score = frequency × recency`
- **Spam detection**: Identifies and filters repetitive unwanted inputs
- **Memory efficiency**: Compressed storage allows large pattern libraries

## Key Implementation Details
- Always active, never unloads
- Learns from every response (feeds back confirmed outputs)
- Handles greetings, repeated phrases, and common commands
- Serves as first layer in inference pipeline

## Limitations
- Only works for previously seen patterns
- Cannot generate novel responses
- Limited to pattern matching, not reasoning
- Requires initial training data to be effective

## Integration Points
- Receives input before PolicyRouter
- Returns instant response or passes to SLM
- Updates scoring based on user feedback
- Persists learned patterns between sessions
