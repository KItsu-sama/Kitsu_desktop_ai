"""
simhashh.py — Real SimHash implementation for text similarity.

Replaces the broken md5(sorted_tokens) approach.

SimHash preserves similarity:
  - identical texts   → hamming distance 0
  - similar texts     → small hamming distance
  - unrelated texts   → large hamming distance

This is the property the old MD5 approach completely lacked.
"""

from __future__ import annotations

import hashlib
import re
from typing import Iterable

# ── Constants ────────────────────────────────────────────────────────────────

BITS = 64
_MASK = (1 << BITS) - 1

STOPWORDS: frozenset[str] = frozenset({
    "a", "an", "the", "is", "it", "i", "you", "me", "my",
    "and", "or", "to", "of", "in", "that", "do", "did",
    "be", "was", "are", "were", "been", "have", "has",
    "he", "she", "we", "they", "at", "by", "for", "on",
    "with", "this", "but", "from", "so", "as", "if",
})

_NON_ALPHA = re.compile(r"[^a-z0-9\s]")


# ── Tokenizer ────────────────────────────────────────────────────────────────

def _tokenize(text: str) -> list[str]:
    """Lowercase, strip punctuation, remove stopwords."""
    cleaned = _NON_ALPHA.sub(" ", text.lower())
    return [t for t in cleaned.split() if t and t not in STOPWORDS]


def _token_hash(token: str) -> int:
    """64-bit hash of a single token via MD5 (fast, sufficient for SimHash)."""
    raw = hashlib.md5(token.encode(), usedforsecurity=False).digest()
    # Take first 8 bytes → 64-bit int
    return int.from_bytes(raw[:8], "big")


# ── SimHash ──────────────────────────────────────────────────────────────────

def simhash(text: str, tokens: Iterable[str] | None = None) -> int:
    """
    Compute a 64-bit SimHash fingerprint for *text*.

    Optionally pass pre-tokenized *tokens* to skip tokenization (useful
    when the caller already has tokens and wants to avoid re-processing).

    Returns an int in [0, 2**64).
    """
    toks = list(tokens) if tokens is not None else _tokenize(text)

    if not toks:
        return 0

    # Accumulator: v[i] counts +1 when bit i is set, -1 otherwise
    v = [0] * BITS

    for token in toks:
        h = _token_hash(token)
        for i in range(BITS):
            if (h >> i) & 1:
                v[i] += 1
            else:
                v[i] -= 1

    # Collapse: bit i = 1 if v[i] > 0 else 0
    fingerprint = 0
    for i in range(BITS):
        if v[i] > 0:
            fingerprint |= 1 << i

    return fingerprint


# ── Hamming & similarity ─────────────────────────────────────────────────────

def hamming(a: int, b: int) -> int:
    """Number of bit positions where *a* and *b* differ."""
    return bin(int(a) ^ int(b)).count("1")


def similarity(a: int, b: int, bits: int = BITS) -> float:
    """
    Cosine-style similarity in [0.0, 1.0] derived from Hamming distance.

      1.0  → identical hashes (distance 0)
      0.0  → maximally different (distance == bits)
    """
    return 1.0 - hamming(a, b) / bits


# ── Trigram helpers (used by the hybrid scorer in reflex) ────────────────────

def trigrams(text: str) -> set[str]:
    """Character 3-grams of *text* (lowercased, no padding)."""
    t = text.lower()
    if len(t) < 3:
        return {t} if t else set()
    return {t[i : i + 3] for i in range(len(t) - 2)}


def trigram_similarity(a: str, b: str) -> float:
    """Jaccard similarity over character trigrams of *a* and *b*."""
    ta, tb = trigrams(a), trigrams(b)
    if not ta and not tb:
        return 1.0
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


# ── Token-overlap (Jaccard on token sets) ────────────────────────────────────

def token_overlap(a: str, b: str) -> float:
    """Jaccard similarity over token sets of *a* and *b* (stopwords removed)."""
    sa = set(_tokenize(a))
    sb = set(_tokenize(b))
    if not sa and not sb:
        return 1.0
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)


# ── Hybrid scorer ─────────────────────────────────────────────────────────────

def hybrid_score(query: str, candidate: str, qhash: int | None = None) -> float:
    """
    Lightweight hybrid similarity as specified in the architecture:

        score = trigram_similarity * 0.4
              + token_overlap      * 0.3
              + simhash_similarity * 0.3

    *qhash* can be pre-computed and passed in to avoid recomputing
    simhash(query) for every candidate in a loop.
    """
    if qhash is None:
        qhash = simhash(query)
    chash = simhash(candidate)

    tg = trigram_similarity(query, candidate)
    to = token_overlap(query, candidate)
    sh = similarity(qhash, chash)

    return tg * 0.4 + to * 0.3 + sh * 0.3