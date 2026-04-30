"""
=====================================
huffman.py (The Storage Compressor)
=====================================
This is a utility for keeping the "Fast Brain" footprint tiny.

Legacy Refactor: Move your data saving/loading utilities here.

Role: It encodes the learned user dictionary. Since many phrases repeat, Huffman compression ensures that a 1MB dictionary of chat history only takes up ~100KB of disk space—crucial for student laptops.
"""

import heapq
import pickle
import logging
from typing import Dict, List, Tuple, Optional, Any
from collections import Counter, defaultdict
from pathlib import Path
import json

log = logging.getLogger(__name__)


class HuffmanNode:
    """Node in Huffman tree."""
    
    def __init__(self, char: str, freq: float):
        self.char = char
        self.freq = freq
        self.left: Optional['HuffmanNode'] = None
        self.right: Optional['HuffmanNode'] = None
    
    def __lt__(self, other: 'HuffmanNode') -> bool:
        return self.freq < other.freq
    
    def __eq__(self, other: 'HuffmanNode') -> bool:
        return self.freq == other.freq


class HuffmanCompressor:
    """
    Huffman coding compressor for efficient storage of learned data.
    
    Compresses frequently used phrases and patterns to minimize
    memory footprint while maintaining fast access.
    """
    
    def __init__(self):
        self.frequencies: Counter = Counter()
        self.codes: Dict[str, str] = {}
        self.reverse_codes: Dict[str, str] = {}
        self.root: Optional[HuffmanNode] = None
        self.is_built = False
    
    def update_frequencies(self, text: str) -> None:
        """
        Update frequency counts with new text.
        
        Args:
            text: Text to analyze
        """
        # Tokenize text (simple word-based for now)
        tokens = self._tokenize(text)
        self.frequencies.update(tokens)
        
        # Mark as needing rebuild
        self.is_built = False
    
    def build_tree(self) -> None:
        """Build the Huffman tree from current frequencies."""
        if not self.frequencies:
            return
        
        # Create priority queue
        priority_queue = [HuffmanNode(char, freq) for char, freq in self.frequencies.items()]
        heapq.heapify(priority_queue)
        
        # Build tree
        while len(priority_queue) > 1:
            # Get two nodes with lowest frequency
            left = heapq.heappop(priority_queue)
            right = heapq.heappop(priority_queue)
            
            # Create internal node
            merged = HuffmanNode(None, left.freq + right.freq)
            merged.left = left
            merged.right = right
            
            heapq.heappush(priority_queue, merged)
        
        self.root = priority_queue[0]
        self._build_codes(self.root, "")
        self.is_built = True
    
    def _build_codes(self, node: HuffmanNode, current_code: str) -> None:
        """Recursively build Huffman codes."""
        if node is None:
            return
        
        if node.char is not None:
            # Leaf node
            self.codes[node.char] = current_code
            self.reverse_codes[current_code] = node.char
            return
        
        # Internal node
        self._build_codes(node.left, current_code + "0")
        self._build_codes(node.right, current_code + "1")
    
    def compress(self, text: str) -> str:
        """
        Compress text using Huffman coding.
        
        Args:
            text: Text to compress
            
        Returns:
            Compressed binary string
        """
        if not self.is_built:
            self.build_tree()
        
        tokens = self._tokenize(text)
        compressed = ""
        
        for token in tokens:
            if token in self.codes:
                compressed += self.codes[token]
            else:
                # Unknown token - use special encoding
                compressed += "111" + format(len(token), '08b') + ''.join(format(ord(c), '08b') for c in token)
        
        return compressed
    
    def decompress(self, compressed: str) -> str:
        """
        Decompress Huffman-encoded text.
        
        Args:
            compressed: Compressed binary string
            
        Returns:
            Decompressed text
        """
        if not self.is_built:
            return ""
        
        result = []
        current_code = ""
        
        i = 0
        while i < len(compressed):
            current_code += compressed[i]
            
            if current_code in self.reverse_codes:
                result.append(self.reverse_codes[current_code])
                current_code = ""
            elif current_code.startswith("111"):
                # Unknown token encoding
                if len(current_code) >= 11:  # "111" + 8-bit length
                    length_bits = current_code[3:11]
                    token_length = int(length_bits, 2)
                    
                    # Need enough bits for the token
                    total_bits_needed = 11 + token_length * 8
                    if len(current_code) >= total_bits_needed:
                        token_bits = current_code[11:total_bits_needed]
                        token = ""
                        for j in range(token_length):
                            char_bits = token_bits[j*8:(j+1)*8]
                            token += chr(int(char_bits, 2))
                        
                        result.append(token)
                        current_code = current_code[total_bits_needed:]
                        i = len(compressed) - len(current_code) - 1  # Adjust index
                        continue
            
            i += 1
        
        return " ".join(result)
    
    def get_compression_ratio(self, text: str) -> float:
        """
        Calculate compression ratio for given text.
        
        Args:
            text: Text to analyze
            
        Returns:
            Compression ratio (compressed_size / original_size)
        """
        if not text:
            return 1.0
        
        compressed = self.compress(text)
        
        # Original size in bits (8 bits per character)
        original_bits = len(text) * 8
        
        # Compressed size
        compressed_bits = len(compressed)
        
        return compressed_bits / original_bits if original_bits > 0 else 1.0
    
    def save_model(self, filepath: str) -> None:
        """
        Save the Huffman model to disk.
        
        Args:
            filepath: Path to save file
        """
        Path(filepath).parent.mkdir(parents=True, exist_ok=True)
        
        data = {
            "frequencies": dict(self.frequencies),
            "is_built": self.is_built,
        }
        
        with open(filepath, 'wb') as f:
            pickle.dump(data, f)
        
        log.info(f"Saved Huffman model to {filepath}")
    
    def load_model(self, filepath: str) -> None:
        """
        Load the Huffman model from disk.
        
        Args:
            filepath: Path to load file
        """
        try:
            with open(filepath, 'rb') as f:
                data = pickle.load(f)
            
            self.frequencies = Counter(data.get("frequencies", {}))
            self.is_built = data.get("is_built", False)
            
            if self.is_built:
                self.build_tree()
            
            log.info(f"Loaded Huffman model from {filepath}")
            
        except FileNotFoundError:
            log.warning(f"Huffman model file not found: {filepath}")
        except Exception as e:
            log.error(f"Error loading Huffman model: {e}")
    
    def _tokenize(self, text: str) -> List[str]:
        """Simple tokenization."""
        import re
        # Split on whitespace and punctuation
        tokens = re.findall(r'\b\w+\b', text.lower())
        return tokens
    
    def get_stats(self) -> Dict[str, Any]:
        """Get compressor statistics."""
        return {
            "vocab_size": len(self.frequencies),
            "total_tokens": sum(self.frequencies.values()),
            "is_built": self.is_built,
            "code_lengths": {char: len(code) for char, code in self.codes.items()},
        }


# Global instance
huffman_compressor = HuffmanCompressor()


def compress_text(text: str) -> str:
    """
    Compress text using Huffman coding.
    
    Args:
        text: Text to compress
        
    Returns:
        Compressed binary string
    """
    return huffman_compressor.compress(text)


def decompress_text(compressed: str) -> str:
    """
    Decompress Huffman-encoded text.
    
    Args:
        compressed: Compressed binary string
        
    Returns:
        Decompressed text
    """
    return huffman_compressor.decompress(compressed)
