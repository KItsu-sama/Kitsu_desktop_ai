"""
system/loop_guard.py

Prevents infinite loops and runaway processes.
Monitors execution time and resource usage.
"""

from __future__ import annotations
import asyncio
import logging
import signal
import threading
import time
from typing import Callable, Optional, Any

log = logging.getLogger('kitsu.system.loop_guard')


class LoopGuard:
    """Monitors and prevents infinite loops and resource exhaustion."""
    
    def __init__(self, 
                 max_execution_time: float = 30.0,
                 max_memory_mb: int = 1024,
                 check_interval: float = 1.0):
        self.max_execution_time = max_execution_time
        self.max_memory_mb = max_memory_mb
        self.check_interval = check_interval
        
        self._start_time: Optional[float] = None
        self._is_running = False
        self._monitor_task: Optional[asyncio.Task] = None
        self._stop_event = threading.Event()
        self._callbacks: list[Callable[[], None]] = []
    
    def start_monitoring(self) -> None:
        """Start monitoring execution."""
        if self._is_running:
            return
        
        self._start_time = time.time()
        self._is_running = True
        self._stop_event.clear()
        
        # Start async monitor task
        try:
            loop = asyncio.get_event_loop()
            self._monitor_task = loop.create_task(self._monitor_loop())
        except RuntimeError:
            # No event loop, start thread
            threading.Thread(target=self._monitor_thread, daemon=True).start()
        
        log.debug(f"Loop guard started - max time: {self.max_execution_time}s, max memory: {self.max_memory_mb}MB")
    
    def stop_monitoring(self) -> None:
        """Stop monitoring execution."""
        if not self._is_running:
            return
        
        self._is_running = False
        self._stop_event.set()
        
        if self._monitor_task and not self._monitor_task.done():
            self._monitor_task.cancel()
        
        log.debug("Loop guard stopped")
    
    def is_expired(self) -> bool:
        """Check if execution time has exceeded limit."""
        if self._start_time is None:
            return False
        
        return (time.time() - self._start_time) > self.max_execution_time
    
    def get_execution_time(self) -> float:
        """Get current execution time in seconds."""
        if self._start_time is None:
            return 0.0
        
        return time.time() - self._start_time
    
    def add_timeout_callback(self, callback: Callable[[], None]) -> None:
        """Add callback to be executed on timeout."""
        self._callbacks.append(callback)
    
    def remove_timeout_callback(self, callback: Callable[[], None]) -> None:
        """Remove timeout callback."""
        if callback in self._callbacks:
            self._callbacks.remove(callback)
    
    async def _monitor_loop(self) -> None:
        """Async monitoring loop."""
        try:
            while self._is_running and not self._stop_event.is_set():
                if self._check_limits():
                    self._trigger_timeout()
                    break
                
                await asyncio.sleep(self.check_interval)
        except asyncio.CancelledError:
            pass
    
    def _monitor_thread(self) -> None:
        """Thread-based monitoring loop."""
        while self._is_running and not self._stop_event.wait(self.check_interval):
            if self._check_limits():
                self._trigger_timeout()
                break
    
    def _check_limits(self) -> bool:
        """Check if any limits have been exceeded."""
        # Check execution time
        if self.is_expired():
            log.warning(f"Execution time limit exceeded: {self.get_execution_time():.1f}s > {self.max_execution_time}s")
            return True
        
        # Check memory usage
        try:
            import psutil
            process = psutil.Process()
            memory_mb = process.memory_info().rss // (1024 * 1024)
            
            if memory_mb > self.max_memory_mb:
                log.warning(f"Memory limit exceeded: {memory_mb}MB > {self.max_memory_mb}MB")
                return True
                
        except ImportError:
            # psutil not available, skip memory monitoring
            pass
        except Exception as e:
            log.warning(f"Memory monitoring error: {e}")
        
        return False
    
    def _trigger_timeout(self) -> None:
        """Execute timeout callbacks."""
        log.error("Loop guard triggered - execution limits exceeded")
        
        for callback in self._callbacks:
            try:
                callback()
            except Exception as e:
                log.error(f"Loop guard callback error: {e}")
        
        # Send interrupt to current thread
        self._send_interrupt()
    
    def _send_interrupt(self) -> None:
        """Send interrupt signal to stop execution."""
        try:
            # Try to interrupt main thread
            if threading.main_thread() is threading.current_thread():
                # We're in main thread, raise KeyboardInterrupt
                raise KeyboardInterrupt("Loop guard timeout")
            else:
                # Send signal to process
                import os
                os.kill(os.getpid(), signal.SIGINT)
        except Exception:
            pass


# Context manager for automatic monitoring
class GuardedLoop:
    """Context manager that automatically monitors execution."""
    
    def __init__(self, 
                 max_time: float = 30.0,
                 max_memory_mb: int = 1024,
                 on_timeout: Optional[Callable[[], None]] = None):
        self.guard = LoopGuard(max_time, max_memory_mb)
        if on_timeout:
            self.guard.add_timeout_callback(on_timeout)
    
    def __enter__(self) -> LoopGuard:
        self.guard.start_monitoring()
        return self.guard
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.guard.stop_monitoring()
        if exc_type == KeyboardInterrupt:
            log.info("Execution interrupted by loop guard")


# Decorator for function guarding
def guard_execution(max_time: float = 30.0, 
                  max_memory_mb: int = 1024,
                  on_timeout: Optional[Callable[[], None]] = None):
    """Decorator to guard function execution."""
    def decorator(func: Callable) -> Callable:
        def wrapper(*args, **kwargs):
            with GuardedLoop(max_time, max_memory_mb, on_timeout):
                return func(*args, **kwargs)
        return wrapper
    return decorator


# Async decorator for async function guarding
def guard_async_execution(max_time: float = 30.0,
                        max_memory_mb: int = 1024,
                        on_timeout: Optional[Callable[[], None]] = None):
    """Decorator to guard async function execution."""
    def decorator(func: Callable) -> Callable:
        async def wrapper(*args, **kwargs):
            guard = LoopGuard(max_time, max_memory_mb)
            if on_timeout:
                guard.add_timeout_callback(on_timeout)
            
            guard.start_monitoring()
            try:
                return await func(*args, **kwargs)
            finally:
                guard.stop_monitoring()
        return wrapper
    return decorator


# Global instance
_global_guard: Optional[LoopGuard] = None


def get_loop_guard() -> LoopGuard:
    """Get global loop guard instance."""
    global _global_guard
    if _global_guard is None:
        _global_guard = LoopGuard()
    return _global_guard


def initialize_loop_guard(max_time: float = 30.0,
                        max_memory_mb: int = 1024) -> LoopGuard:
    """Initialize global loop guard."""
    global _global_guard
    if _global_guard is not None:
        raise RuntimeError("Loop guard already initialized.")
    
    _global_guard = LoopGuard(max_time, max_memory_mb)
    return _global_guard


def reset_loop_guard() -> None:
    """Reset global loop guard (for testing)."""
    global _global_guard
    if _global_guard:
        _global_guard.stop_monitoring()
    _global_guard = None