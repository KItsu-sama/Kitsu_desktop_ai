"""
=====================================
learning_loop.py (The Experience Collector)
=====================================
This is the "background worker" that makes kitsu smarter as you use her.

Legacy Refactor: This replaces any manual "save to file" logic you had for user data.

Role: It watches the final output (from the LLM) and the user's reaction. If a response was good, it feeds it to trainer.py to update the Markov chains or Huffman tree.
"""

import asyncio
import logging
import threading
import time
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
from queue import Queue

from .markov import add_conversation, markov_chain
from .huffman import HuffmanCompressor
from .trainer import Trainer

log = logging.getLogger(__name__)


@dataclass
class ConversationTurn:
    """Represents a single conversation turn."""
    user_input: str
    kitsu_response: str
    timestamp: float
    response_quality: float = 0.0  # 0.0 to 1.0
    user_reaction: Optional[str] = None  # "positive", "negative", "neutral"
    context: Optional[Dict[str, Any]] = None


class LearningLoop:
    """
    Background learning system that improves kitsu's responses over time.
    
    Collects conversation data and feeds it to training systems
    to improve pattern recognition and response generation.
    """
    
    def __init__(self):
        self.conversation_history: List[ConversationTurn] = []
        self.learning_queue: Queue = Queue()
        self.is_running = False
        self.learning_thread: Optional[threading.Thread] = None
        
        # Learning components
        self.huffman_compressor = HuffmanCompressor()
        self.trainer = Trainer()
        
        # Learning parameters
        self.max_history_size = 10000  # Keep last 10k conversations
        self.learning_interval = 300  # Learn every 5 minutes
        self.min_quality_threshold = 0.6  # Only learn from good responses
        
        # Stats
        self.total_learned = 0
        self.last_learning_time = time.time()
    
    def start(self) -> None:
        """Start the background learning loop."""
        if self.is_running:
            return
        
        self.is_running = True
        self.learning_thread = threading.Thread(target=self._learning_worker, daemon=True)
        self.learning_thread.start()
        
        log.info("Learning loop started")
    
    def stop(self) -> None:
        """Stop the background learning loop."""
        self.is_running = False
        if self.learning_thread:
            self.learning_thread.join(timeout=5.0)
        
        log.info("Learning loop stopped")
    
    def add_conversation(
        self,
        user_input: str,
        kitsu_response: str,
        response_quality: float = 0.5,
        user_reaction: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Add a conversation turn to the learning system.
        
        Args:
            user_input: User's message
            kitsu_response: kitsu's response
            response_quality: Quality score (0.0 to 1.0)
            user_reaction: User's reaction if available
            context: Additional context data
        """
        turn = ConversationTurn(
            user_input=user_input,
            kitsu_response=kitsu_response,
            timestamp=time.time(),
            response_quality=response_quality,
            user_reaction=user_reaction,
            context=context
        )
        
        # Add to history
        self.conversation_history.append(turn)
        
        # Trim history if too large
        if len(self.conversation_history) > self.max_history_size:
            self.conversation_history = self.conversation_history[-self.max_history_size:]
        
        # Queue for immediate learning if quality is good
        if response_quality >= self.min_quality_threshold:
            self.learning_queue.put(turn)
        
        log.debug(f"Added conversation turn (quality: {response_quality:.2f})")
    
    def _learning_worker(self) -> None:
        """Background worker that processes learning data."""
        while self.is_running:
            try:
                # Process queued learning data
                while not self.learning_queue.empty():
                    turn = self.learning_queue.get_nowait()
                    self._process_learning_turn(turn)
                
                # Periodic batch learning
                current_time = time.time()
                if current_time - self.last_learning_time >= self.learning_interval:
                    self._batch_learning()
                    self.last_learning_time = current_time
                
                # Sleep briefly
                time.sleep(1.0)
                
            except Exception as e:
                log.error(f"Error in learning worker: {e}")
                time.sleep(5.0)  # Back off on errors
    
    def _process_learning_turn(self, turn: ConversationTurn) -> None:
        """
        Process a single learning turn.
        
        Args:
            turn: Conversation turn to learn from
        """
        try:
            # Add to Markov chain
            add_conversation(turn.user_input, turn.kitsu_response)
            
            # Update Huffman compressor with new text
            combined_text = f"{turn.user_input} {turn.kitsu_response}"
            self.huffman_compressor.update_frequencies(combined_text)
            
            # Update trainer
            self.trainer.add_training_example(
                user_input=turn.user_input,
                response=turn.kitsu_response,
                quality=turn.response_quality,
                context=turn.context
            )
            
            self.total_learned += 1
            
            log.debug(f"Processed learning turn {self.total_learned}")
            
        except Exception as e:
            log.error(f"Error processing learning turn: {e}")
    
    def _batch_learning(self) -> None:
        """Perform batch learning operations."""
        try:
            # Trigger trainer to update models
            self.trainer.train_models()
            
            # Compress and save updated data
            self._save_learning_data()
            
            log.info("Completed batch learning")
            
        except Exception as e:
            log.error(f"Error in batch learning: {e}")
    
    def _save_learning_data(self) -> None:
        """Save learning data to disk."""
        try:
            # Save Markov model
            markov_chain.save_model("data/models/markov_model.json")
            
            # Save Huffman compressor
            self.huffman_compressor.save_model("data/models/huffman_model.pkl")
            
            # Save trainer data
            self.trainer.save_models("data/models/")
            
            log.debug("Saved learning data to disk")
            
        except Exception as e:
            log.error(f"Error saving learning data: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get learning statistics."""
        return {
            "total_conversations": len(self.conversation_history),
            "total_learned": self.total_learned,
            "queue_size": self.learning_queue.qsize(),
            "is_running": self.is_running,
            "last_learning_time": self.last_learning_time,
            "markov_transitions": len(markov_chain.transitions),
            "huffman_vocab_size": len(self.huffman_compressor.frequencies),
        }


# Global instance
learning_loop = LearningLoop()


def start_learning() -> None:
    """Start the background learning system."""
    learning_loop.start()


def stop_learning() -> None:
    """Stop the background learning system."""
    learning_loop.stop()


def add_learning_example(
    user_input: str,
    kitsu_response: str,
    quality: float = 0.5,
    reaction: Optional[str] = None,
    context: Optional[Dict[str, Any]] = None
) -> None:
    """
    Add a conversation example to the learning system.
    
    Args:
        user_input: User's message
        kitsu_response: kitsu's response
        quality: Response quality (0.0 to 1.0)
        reaction: User reaction
        context: Additional context
    """
    learning_loop.add_conversation(
        user_input=user_input,
        kitsu_response=kitsu_response,
        response_quality=quality,
        user_reaction=reaction,
        context=context
    )