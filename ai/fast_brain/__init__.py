"""
The "Fast Brain" (Binary + Markov + Huffman) logic
To make Kisu feel "alive" without using the CPU for an SLM, your Fast Brain should operate on a Frequency-Weighting logic:

Binary/Huffman: Used for ultra-fast pattern matching.
If the user input hash matches a "Common Input" exactly, the response is served in <1ms.

Markov Chain: Used for the "Spam" detection and "Boredom" system.
If the Markov state detects the same transition (User: "Hai" -> Kisu: "Hai") three times, it triggers the irritated emotion shift.

Learning Loop: When the LLM generates a high-quality response, the Fast Brain should "snatch" that pair and save it. Next time, Kisu won't need the LLM for that specific query.
"""

from .engine import process_user_input, fast_brain_engine
from .patterns import get_fast_response, pattern_matcher
from .intent_classifier import classify_intent, intent_classifier
from .markov import add_conversation, generate_markov_response, markov_chain
from .learning_loop import start_learning, stop_learning, add_learning_example, learning_loop
from .huffman import compress_text, decompress_text, huffman_compressor
from .cache_store import add_to_cache, get_cached_response, conversation_cache
from .trainer import train_models, trainer

__all__ = [
    # Engine
    'process_user_input',
    'fast_brain_engine',
    
    # Patterns
    'get_fast_response',
    'pattern_matcher',
    
    # Intent Classifier
    'classify_intent',
    'intent_classifier',
    
    # Markov
    'add_conversation',
    'generate_markov_response',
    'markov_chain',
    
    # Learning Loop
    'start_learning',
    'stop_learning',
    'add_learning_example',
    'learning_loop',
    
    # Huffman
    'compress_text',
    'decompress_text',
    'huffman_compressor',
    
    # Cache
    'add_to_cache',
    'get_cached_response',
    'conversation_cache',
    
    # Trainer
    'train_models',
    'trainer',
]