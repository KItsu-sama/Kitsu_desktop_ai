"""
The "Fast Brain" (Binary + Markov + Huffman) logic
To make Kisu feel "alive" without using CPU for an SLM, your Fast Brain should operate on a Frequency-Weighting logic:

Binary/Huffman: Used for ultra-fast pattern matching.
If user input hash matches a "Common Input" exactly, response is served in <1ms.

Markov Chain: Used for "Spam" detection and "Boredom" system.
If Markov state detects the same transition (User: "Hai" -> Kisu: "Hai") three times, it triggers irritated emotion shift.

Learning Loop: When LLM generates a high-quality response, Fast Brain should "snatch" that pair and save it. Next time, Kisu won't need LLM for that specific query.
"""

from .provider import FastBrainProvider

__all__ = [
    'FastBrainProvider',
]