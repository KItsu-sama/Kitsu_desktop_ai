"""
=====================================
trainer.py (The Model Optimizer)
=====================================
This runs occasionally (or during "Sleep Mode") to bake the learned data.

Role: It takes the data from the learning_loop.py and rebuilds the Huffman trees and Markov matrices. It ensures Kisu's "brain" is optimized for the next time the app starts.
"""

import time
import logging
import threading
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path

from .markov import markov_chain
from .huffman import huffman_compressor
from .patterns import pattern_matcher

log = logging.getLogger(__name__)


@dataclass
class TrainingExample:
    """Represents a training example."""
    user_input: str
    response: str
    quality: float
    timestamp: float
    context: Optional[Dict[str, Any]] = None


class Trainer:
    """
    Background trainer that optimizes learned models.
    
    Periodically retrains models with accumulated data to improve
    performance and update pattern recognition.
    """
    
    def __init__(self):
        self.training_examples: List[TrainingExample] = []
        self.is_training = False
        self.last_training_time = 0.0
        self.training_interval = 1800  # 30 minutes
        
        # Training parameters
        self.min_examples_for_training = 10
        self.max_examples = 1000  # Keep last 1000 examples
        
        # Model save paths
        self.model_dir = Path("data/models")
        self.model_dir.mkdir(parents=True, exist_ok=True)
    
    def add_training_example(
        self,
        user_input: str,
        response: str,
        quality: float,
        context: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Add a training example.
        
        Args:
            user_input: User's message
            response: Kisu's response
            quality: Response quality (0.0 to 1.0)
            context: Additional context
        """
        example = TrainingExample(
            user_input=user_input,
            response=response,
            quality=quality,
            timestamp=time.time(),
            context=context
        )
        
        self.training_examples.append(example)
        
        # Trim old examples
        if len(self.training_examples) > self.max_examples:
            self.training_examples = self.training_examples[-self.max_examples:]
        
        log.debug(f"Added training example (quality: {quality:.2f})")
    
    def should_train(self) -> bool:
        """
        Check if training should be performed.
        
        Returns:
            True if training conditions are met
        """
        current_time = time.time()
        
        # Check time interval
        if current_time - self.last_training_time < self.training_interval:
            return False
        
        # Check minimum examples
        if len(self.training_examples) < self.min_examples_for_training:
            return False
        
        # Check if currently training
        if self.is_training:
            return False
        
        return True
    
    def train_models(self) -> bool:
        """
        Train all models with accumulated data.
        
        Returns:
            True if training was performed
        """
        if not self.should_train():
            return False
        
        if self.is_training:
            log.warning("Training already in progress")
            return False
        
        try:
            self.is_training = True
            log.info("Starting model training...")
            
            start_time = time.time()
            
            # Train Markov chain
            self._train_markov_chain()
            
            # Train Huffman compressor
            self._train_huffman_compressor()
            
            # Update patterns
            self._update_patterns()
            
            # Save models
            self._save_models()
            
            self.last_training_time = time.time()
            training_time = self.last_training_time - start_time
            
            log.info(f"Training completed in {training_time:.2f}s")
            return True
            
        except Exception as e:
            log.error(f"Error during training: {e}")
            return False
            
        finally:
            self.is_training = False
    
    def _train_markov_chain(self) -> None:
        """Train the Markov chain with recent examples."""
        log.debug("Training Markov chain...")
        
        # Clear existing transitions (or merge? For now, rebuild)
        markov_chain.transitions.clear()
        markov_chain.start_tokens.clear()
        markov_chain.end_tokens.clear()
        markov_chain.conversation_history.clear()
        
        # Add training examples
        for example in self.training_examples:
            if example.quality >= 0.5:  # Only learn from decent responses
                markov_chain.add_transition(example.user_input, example.response)
        
        log.debug(f"Trained Markov chain with {len(self.training_examples)} examples")
    
    def _train_huffman_compressor(self) -> None:
        """Train the Huffman compressor with text data."""
        log.debug("Training Huffman compressor...")
        
        # Reset frequencies
        huffman_compressor.frequencies.clear()
        huffman_compressor.is_built = False
        
        # Collect all text
        all_text = []
        for example in self.training_examples:
            all_text.append(example.user_input)
            all_text.append(example.response)
        
        combined_text = " ".join(all_text)
        
        # Update frequencies
        huffman_compressor.update_frequencies(combined_text)
        
        # Build tree
        huffman_compressor.build_tree()
        
        log.debug(f"Trained Huffman compressor with {len(huffman_compressor.frequencies)} unique tokens")
    
    def _update_patterns(self) -> None:
        """Update pattern matcher with learned patterns."""
        log.debug("Updating patterns...")
        
        # Extract common phrases from training data
        user_phrases = {}
        response_phrases = {}
        
        for example in self.training_examples:
            # Count user input patterns
            user_lower = example.user_input.lower().strip()
            if user_lower not in user_phrases:
                user_phrases[user_lower] = 0
            user_phrases[user_lower] += 1
            
            # Count response patterns
            resp_lower = example.response.lower().strip()
            if resp_lower not in response_phrases:
                response_phrases[resp_lower] = 0
            response_phrases[resp_lower] += 1
        
        # Add frequent patterns to fuzzy matcher
        for phrase, count in user_phrases.items():
            if count >= 3:  # Appears 3+ times
                # Find corresponding response
                responses = [ex.response for ex in self.training_examples 
                           if ex.user_input.lower().strip() == phrase]
                if responses:
                    most_common_response = max(set(responses), key=responses.count)
                    pattern_matcher.fuzzy_patterns[phrase] = most_common_response
        
        log.debug(f"Updated patterns with {len(pattern_matcher.fuzzy_patterns)} fuzzy matches")
    
    def _save_models(self) -> None:
        """Save all trained models."""
        try:
            # Save Markov model
            markov_path = self.model_dir / "markov_model.json"
            markov_chain.save_model(str(markov_path))
            
            # Save Huffman model
            huffman_path = self.model_dir / "huffman_model.pkl"
            huffman_compressor.save_model(str(huffman_path))
            
            log.debug("Saved trained models")
            
        except Exception as e:
            log.error(f"Error saving models: {e}")
    
    def load_models(self, model_dir: str) -> None:
        """
        Load saved models.
        
        Args:
            model_dir: Directory containing model files
        """
        model_path = Path(model_dir)
        
        try:
            # Load Markov model
            markov_path = model_path / "markov_model.json"
            if markov_path.exists():
                markov_chain.load_model(str(markov_path))
            
            # Load Huffman model
            huffman_path = model_path / "huffman_model.pkl"
            if huffman_path.exists():
                huffman_compressor.load_model(str(huffman_path))
            
            log.info("Loaded saved models")
            
        except Exception as e:
            log.error(f"Error loading models: {e}")
    
    def save_models(self, model_dir: str) -> None:
        """
        Save models to specified directory.
        
        Args:
            model_dir: Directory to save models
        """
        save_path = Path(model_dir)
        save_path.mkdir(parents=True, exist_ok=True)
        
        self._save_models()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get training statistics."""
        return {
            "training_examples": len(self.training_examples),
            "is_training": self.is_training,
            "last_training_time": self.last_training_time,
            "time_since_last_training": time.time() - self.last_training_time,
            "should_train": self.should_train(),
            "markov_transitions": len(markov_chain.transitions),
            "huffman_vocab_size": len(huffman_compressor.frequencies),
        }


# Global instance
trainer = Trainer()


def train_models() -> bool:
    """
    Train all models.
    
    Returns:
        True if training was performed
    """
    return trainer.train_models()


def add_training_data(user_input: str, response: str, quality: float = 0.5) -> None:
    """
    Add training data.
    
    Args:
        user_input: User input
        response: Response
        quality: Quality score
    """
    trainer.add_training_example(user_input, response, quality)