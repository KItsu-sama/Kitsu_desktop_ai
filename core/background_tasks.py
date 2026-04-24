"""
core/background_tasks.py

Background task management extracted from legacy runtime.

Provides centralized tracking and graceful shutdown of background tasks
with proper error handling and cleanup.
"""

import asyncio
import logging
from dataclasses import dataclass
from typing import List, Optional, Any

from core.contracts import ModuleContract
from core.events import EventBus, EventType, EventPayload
from utils.validation import sanitize_text

log = logging.getLogger(__name__)


@dataclass
class TaskInfo:
    """Information about a tracked background task."""
    task: asyncio.Task
    name: str
    description: Optional[str] = None
    critical: bool = False  # Critical tasks delay shutdown


class BackgroundTaskManager(ModuleContract):
    """
    Manages background tasks with centralized tracking and graceful shutdown.
    
    Enhanced from legacy version with:
    - Task metadata tracking
    - Critical task handling
    - Event integration
    - Better error handling
    """
    
    module_id = 'core.background_tasks'
    required_flags = []
    
    def __init__(self, event_bus: Optional[EventBus] = None) -> None:
        self.event_bus = event_bus
        self._tasks: List[TaskInfo] = []
        self._running = False
        self._shutdown_requested = False
        
    async def start(self) -> bool:
        """Start the background task manager."""
        if self._running:
            return True
            
        self._running = True
        self._shutdown_requested = False
        log.info("Background task manager started")
        return True
    
    async def stop(self) -> bool:
        """Stop all background tasks gracefully."""
        if not self._running:
            return True
            
        self._shutdown_requested = True
        log.info(f"Stopping {len(self._tasks)} background tasks...")
        
        # Separate critical and non-critical tasks
        critical_tasks = [info for info in self._tasks if info.critical]
        normal_tasks = [info for info in self._tasks if not info.critical]
        
        # Stop normal tasks first
        await self._stop_task_group(normal_tasks, timeout=5.0)
        
        # Stop critical tasks with longer timeout
        await self._stop_task_group(critical_tasks, timeout=10.0)
        
        self._tasks.clear()
        self._running = False
        log.info("All background tasks stopped")
        
        # Emit cleanup event
        if self.event_bus:
            self.event_bus.publish(EventPayload(
                event_type=EventType.BACKGROUND_TASKS_STOPPED,
                source='background_tasks',
                data={'stopped_count': len(normal_tasks) + len(critical_tasks)}
            ))
        
        return True
    
    async def health_check(self) -> dict:
        """Check health of background tasks."""
        return {
            'ok': self._running,
            'latency_ms': 0.0,
            'task_count': len(self._tasks),
            'running_tasks': len([t for t in self._tasks if not t.task.done()]),
            'failed_tasks': len([t for t in self._tasks if t.task.done() and t.task.exception()])
        }
    
    async def start_task(
        self, 
        coro, 
        name: str, 
        description: Optional[str] = None,
        critical: bool = False
    ) -> asyncio.Task:
        """
        Start a background task and track it.
        
        Args:
            coro: Coroutine to run
            name: Task name for identification
            description: Human-readable description
            critical: Whether task is critical (delays shutdown)
            
        Returns:
            Created asyncio.Task
        """
        # Validate inputs
        if not asyncio.iscoroutine(coro):
            raise ValueError("coro must be a coroutine object")
        
        if not isinstance(name, str) or not name.strip():
            raise ValueError("name must be a non-empty string")
        
        # Sanitize inputs
        safe_name = sanitize_text(name, max_length=100)
        safe_description = sanitize_text(description, max_length=500) if description else None
        
        if self._shutdown_requested:
            raise RuntimeError("Cannot start tasks during shutdown")
        
        task = asyncio.create_task(coro, name=safe_name)
        task_info = TaskInfo(
            task=task,
            name=safe_name,
            description=safe_description,
            critical=critical
        )
        
        self._tasks.append(task_info)
        
        log.debug(f"Started background task: {safe_name}")
        if safe_description:
            log.debug(f"  Description: {safe_description}")
        
        # Add done callback for cleanup
        task.add_done_callback(lambda t: self._on_task_done(task_info))
        
        # Emit task started event
        if self.event_bus:
            self.event_bus.publish(EventPayload(
                event_type=EventType.BACKGROUND_TASK_STARTED,
                source='background_tasks',
                data={
                    'name': name,
                    'description': description,
                    'critical': critical
                }
            ))
        
        return task
    
    def get_task_info(self, name: str) -> Optional[TaskInfo]:
        """Get information about a tracked task."""
        for info in self._tasks:
            if info.name == name:
                return info
        return None
    
    def get_all_tasks(self) -> List[TaskInfo]:
        """Get all tracked task information."""
        return self._tasks.copy()
    
    def cancel_task(self, name: str) -> bool:
        """Cancel a specific task by name."""
        for info in self._tasks:
            if info.name == name and not info.task.done():
                info.task.cancel()
                log.info(f"Cancelled task: {name}")
                return True
        return False
    
    async def _stop_task_group(self, tasks: List[TaskInfo], timeout: float) -> None:
        """Stop a group of tasks with timeout."""
        if not tasks:
            return
        
        # Cancel all tasks in group
        for info in tasks:
            if not info.task.done():
                info.task.cancel()
        
        # Wait for completion with timeout
        try:
            await asyncio.wait_for(
                asyncio.gather(*[info.task for info in tasks], return_exceptions=True),
                timeout=timeout
            )
        except asyncio.TimeoutError:
            log.warning(f"Timeout stopping tasks after {timeout}s")
    
    def _on_task_done(self, task_info: TaskInfo) -> None:
        """Handle task completion and cleanup."""
        task = task_info.task
        
        if task.cancelled():
            log.debug(f"Task {task_info.name} was cancelled")
        elif task.exception():
            log.error(f"Task {task_info.name} failed: {task.exception()}")
        else:
            log.debug(f"Task {task_info.name} completed successfully")
        
        # Remove completed task from tracking list to prevent memory leaks
        try:
            self._tasks.remove(task_info)
        except ValueError:
            # Task already removed or never added
            log.warning(f"Task {task_info.name} not found in tracking list during cleanup")
        
        # Emit task completed event
        if self.event_bus:
            self.event_bus.publish(EventPayload(
                event_type=EventType.BACKGROUND_TASK_COMPLETED,
                source='background_tasks',
                data={
                    'name': task_info.name,
                    'cancelled': task.cancelled(),
                    'exception': str(task.exception()) if task.exception() else None
                }
            ))


# Global instance for easy access
_background_manager: Optional[BackgroundTaskManager] = None


def get_background_manager() -> Optional[BackgroundTaskManager]:
    """Get the global background task manager."""
    return _background_manager


def create_background_manager(event_bus: Optional[EventBus] = None) -> BackgroundTaskManager:
    """Create and register the global background task manager."""
    global _background_manager
    _background_manager = BackgroundTaskManager(event_bus)
    return _background_manager


# Convenience functions for global manager
async def start_background_task(
    coro, 
    name: str, 
    description: Optional[str] = None,
    critical: bool = False
) -> asyncio.Task:
    """Start a background task using the global manager."""
    manager = get_background_manager()
    if not manager:
        raise RuntimeError("Background task manager not initialized")
    return await manager.start_task(coro, name, description, critical)


def cancel_background_task(name: str) -> bool:
    """Cancel a background task using the global manager."""
    manager = get_background_manager()
    if not manager:
        return False
    return manager.cancel_task(name)


def get_background_task_info(name: str) -> Optional[TaskInfo]:
    """Get task information using the global manager."""
    manager = get_background_manager()
    if not manager:
        return None
    return manager.get_task_info(name)
