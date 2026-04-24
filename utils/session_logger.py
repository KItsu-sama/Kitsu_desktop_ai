# data/ml/session_logger.py
"""
Session logger for batch processing.
Logs every interaction to JSONL with rotation and compression.
Never blocks live inference - all operations are async/background.
"""

import json
import gzip
import logging
import asyncio
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime
from collections import deque
import threading

log = logging.getLogger(__name__)


class SessionLogger:
    """
    Async session logger for batch processing.
    
    Features:
    - Logs every interaction to JSONL
    - Fields: timestamp, user_id, input, output, emotion, intent, lora_used, rating
    - Rotation after 10k lines
    - Compressed backups
    - Thread-safe async writes
    - Never blocks live inference

    Example:
        logger = SessionLogger(log_dir=Path("data/logs/sessions"))
        
        # Log interaction (non-blocking)
        await logger.log_interaction(
            user_id="user123",
            input="hello kitsu",
            output="Hey there!",
            emotion="happy",
            intent="greeting",
            lora_used=["chaotic"],
            rating=None
        )
    """

    def __init__(
        self,
        log_dir: Optional[Path] = None,
        max_lines_per_file: int = 10000,
        enable_compression: bool = True
    ):
        self.log_dir = log_dir or Path("data/logs/sessions")
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        self.max_lines_per_file = max_lines_per_file
        self.enable_compression = enable_compression
        
        # Current log file
        self.current_log_file: Optional[Path] = None
        self.current_line_count = 0
        
        # Write queue for async processing
        self.write_queue: deque = deque(maxlen=10000)
        self.write_lock = threading.Lock()
        self._write_thread: Optional[threading.Thread] = None
        self._stop_writing = False
        
        # Start background writer
        self._start_writer()
        
        # Initialize current log file
        self._rotate_log_file()

    def _start_writer(self):
        """Start background thread for async writes"""
        if self._write_thread is None or not self._write_thread.is_alive():
            self._stop_writing = False
            self._write_thread = threading.Thread(target=self._write_worker, daemon=True)
            self._write_thread.start()
            log.info("Session logger background writer started")

    def _write_worker(self):
        """Background worker that processes write queue"""
        while not self._stop_writing:
            if self.write_queue:
                try:
                    entries = []
                    # Batch up to 100 entries at a time
                    for _ in range(min(100, len(self.write_queue))):
                        if self.write_queue:
                            entries.append(self.write_queue.popleft())
                    
                    if entries:
                        self._write_batch(entries)
                except Exception as e:
                    log.error(f"Error in write worker: {e}")
            
            # Sleep briefly to avoid busy-waiting
            import time
            time.sleep(0.1)

    def _write_batch(self, entries: List[Dict[str, Any]]):
        """Write batch of entries to log file"""
        with self.write_lock:
            if self.current_log_file is None:
                self._rotate_log_file()
            
            try:
                with open(self.current_log_file, "a", encoding="utf-8") as f:
                    for entry in entries:
                        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
                        self.current_line_count += 1
                
                # Rotate if needed
                if self.current_line_count >= self.max_lines_per_file:
                    self._rotate_log_file()
            except Exception as e:
                log.error(f"Failed to write session log batch: {e}")

    def _rotate_log_file(self):
        """Rotate to new log file"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.current_log_file = self.log_dir / f"session_{timestamp}.jsonl"
        self.current_line_count = 0
        log.info(f"Rotated to new session log: {self.current_log_file.name}")

    async def log_interaction(
        self,
        user_id: str,
        input: str,
        output: str,
        emotion: Optional[str] = None,
        intent: Optional[str] = None,
        lora_used: Optional[List[str]] = None,
        rating: Optional[int] = None,
        **kwargs
    ) -> None:
        """
        Log an interaction (non-blocking).
        
        Args:
            user_id: User identifier
            input: User input text
            output: System output text
            emotion: Detected emotion
            intent: Detected intent
            lora_used: List of LoRA adapters used
            rating: User rating (1-5) if available
            **kwargs: Additional metadata
        """
        entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "user_id": str(user_id),
            "input": str(input) if input else "",
            "output": str(output) if output else "",
            "emotion": emotion,
            "intent": intent,
            "lora_used": lora_used or [],
            "rating": rating,
            **kwargs
        }
        
        # Add to write queue (non-blocking)
        if len(self.write_queue) < self.write_queue.maxlen:
            self.write_queue.append(entry)
        else:
            log.warning("Session log queue full, dropping entry")

    def _compress_old_logs(self):
        """Compress old log files"""
        if not self.enable_compression:
            return
        
        try:
            # Find uncompressed JSONL files (not current)
            for log_file in self.log_dir.glob("session_*.jsonl"):
                if log_file == self.current_log_file:
                    continue
                
                # Check if already compressed
                if log_file.with_suffix(".jsonl.gz").exists():
                    continue
                
                # Compress
                compressed_path = log_file.with_suffix(".jsonl.gz")
                with open(log_file, "rb") as f_in:
                    with gzip.open(compressed_path, "wb") as f_out:
                        f_out.writelines(f_in)
                
                # Remove original
                log_file.unlink()
                log.info(f"Compressed {log_file.name}")
        except Exception as e:
            log.error(f"Error compressing logs: {e}")

    def get_all_log_files(self, include_compressed: bool = True) -> List[Path]:
        """
        Get all log files (for batch processing).
        
        Args:
            include_compressed: Include .gz files
            
        Returns:
            List of log file paths
        """
        files = []
        
        # Uncompressed files
        files.extend(self.log_dir.glob("session_*.jsonl"))
        
        # Compressed files
        if include_compressed:
            files.extend(self.log_dir.glob("session_*.jsonl.gz"))
        
        return sorted(files)

    def shutdown(self):
        """Shutdown logger and flush queue"""
        log.info("Shutting down session logger...")
        
        # Stop writer
        self._stop_writing = True
        if self._write_thread:
            self._write_thread.join(timeout=5.0)
        
        # Flush remaining queue
        if self.write_queue:
            self._write_batch(list(self.write_queue))
        
        # Compress old logs
        self._compress_old_logs()
        
        log.info("Session logger shut down")