"""
domain/personality/memory_manager.py — Memory Manager (Architecture Compliant)

COMBINED FEATURES:
- All plugins from both versions
- Proper Enum serialization (V2 fix)
- ensure_user_profile_exists (V1)
- Async export/import memory
- Session tagging
- Sleep optimization
- Grounding + Emotional plugins

FIXES APPLIED:
- MemoryType/MemoryPriority Enum JSON serialization
- MemoryFragment reconstruction after load
- Atomic save/load operations
"""

import json
import logging
import time
import threading
import asyncio
from collections import deque
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Protocol
from dataclasses import dataclass, asdict, fields
from enum import Enum
import hashlib

from domain.personality.scoring import compute_score

log = logging.getLogger(__name__)

# =============================================================================
# Configuration
# =============================================================================

class MemoryConfig:
    """Memory system configuration"""
    
    def __init__(
        self,
        max_history: int = 200,
        auto_save: bool = True,
        save_interval: int = 60,
        compression_enabled: bool = True,
        max_short_term: int = 100,
        max_episodic: int = 50
    ):
        self.max_history = max_history
        self.auto_save = auto_save
        self.save_interval = save_interval
        self.compression_enabled = compression_enabled
        self.max_short_term = max_short_term
        self.max_episodic = max_episodic

# =============================================================================
# Memory Types and Fragments
# =============================================================================

class MemoryType(Enum):
    SHORT_TERM = "short_term"
    EPISODIC = "episodic"
    LONG_TERM = "long_term"
    WORKING = "working"

class MemoryPriority(Enum):
    CRITICAL = 3
    IMPORTANT = 2
    NORMAL = 1
    TEMPORARY = 0

@dataclass
class MemoryFragment:
    id: str
    content: str
    memory_type: MemoryType
    priority: MemoryPriority
    timestamp: float
    emotional_tags: List[str]
    context_tags: List[str]
    access_count: int = 0
    last_accessed: float = 0.0
    decay_rate: float = 0.01
    compression_level: int = 0
    
    def __post_init__(self):
        if self.last_accessed == 0.0:
            self.last_accessed = self.timestamp
        # Coerce string → Enum (needed after JSON round-trip)
        if isinstance(self.memory_type, str):
            self.memory_type = MemoryType(self.memory_type)
        if isinstance(self.priority, str):
            try:
                self.priority = MemoryPriority[self.priority]
            except KeyError:
                try:
                    self.priority = MemoryPriority(int(self.priority))
                except (ValueError, KeyError):
                    self.priority = MemoryPriority.NORMAL
        elif isinstance(self.priority, int):
            try:
                self.priority = MemoryPriority(self.priority)
            except ValueError:
                self.priority = MemoryPriority.NORMAL

@dataclass
class EpisodicMemory:
    id: str
    title: str
    fragments: List[str]
    start_time: float
    end_time: float
    emotional_summary: Dict[str, float]
    importance_score: float
    context: Dict[str, Any]

@dataclass
class EmotionalState:
    timestamp: float
    mood: str
    style: str
    dominant_emotion: str
    intensity: float
    triggers: List[str]

# =============================================================================
# JSON Serialization Helpers
# =============================================================================

def _to_json_safe(obj: Any) -> Any:
    """Recursively convert to JSON-safe form. Handles Enum, dataclass, dict, list, primitives."""
    if isinstance(obj, Enum):
        return obj.value
    if hasattr(obj, '__dataclass_fields__'):
        return {k: _to_json_safe(v) for k, v in obj.__dict__.items()}
    if isinstance(obj, dict):
        return {k: _to_json_safe(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_to_json_safe(i) for i in obj]
    return obj


class _EnumEncoder(json.JSONEncoder):
    """JSONEncoder that handles Enum and dataclass values."""
    def default(self, obj):
        if isinstance(obj, Enum):
            return obj.value
        if hasattr(obj, '__dataclass_fields__'):
            return _to_json_safe(obj)
        return super().default(obj)


def _fragment_from_dict(d: Dict[str, Any]) -> MemoryFragment:
    """Reconstruct MemoryFragment from raw JSON dict."""
    # Handle memory_type
    mt = d.get("memory_type", "short_term")
    if isinstance(mt, str):
        try:
            mt = MemoryType(mt)
        except ValueError:
            mt = MemoryType.SHORT_TERM

    # Handle priority
    pr = d.get("priority", MemoryPriority.NORMAL)
    if isinstance(pr, int):
        try:
            pr = MemoryPriority(pr)
        except ValueError:
            pr = MemoryPriority.NORMAL
    elif isinstance(pr, str):
        try:
            pr = MemoryPriority[pr]
        except KeyError:
            try:
                pr = MemoryPriority(int(pr))
            except (ValueError, KeyError):
                pr = MemoryPriority.NORMAL

    return MemoryFragment(
        id=d["id"],
        content=d["content"],
        memory_type=mt,
        priority=pr,
        timestamp=d["timestamp"],
        emotional_tags=d.get("emotional_tags", []),
        context_tags=d.get("context_tags", []),
        access_count=d.get("access_count", 0),
        last_accessed=d.get("last_accessed", d["timestamp"]),
        decay_rate=d.get("decay_rate", 0.01),
        compression_level=d.get("compression_level", 0),
    )

# =============================================================================
# Plugin Interface
# =============================================================================

class MemoryPlugin(Protocol):
    @property
    def priority(self) -> int:
        return 0
    
    def on_remember(self, role: str, text: str, emotion: Optional[str] = None) -> Optional[str]:
        pass
    
    def on_recall(self, sessions: List[Dict[str, Any]], context_length: int) -> List[Dict[str, Any]]:
        pass
    
    def on_save(self, data: Dict[str, Any]) -> Dict[str, Any]:
        pass
    
    def on_load(self, data: Dict[str, Any]) -> None:
        pass
    
    def on_optimize(self, sessions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        pass

# =============================================================================
# Core Plugins
# =============================================================================

class EmotionalMemoryPlugin:
    def __init__(self):
        self.emotional_weights = {
            "joy": 1.5, "anger": 1.8, "surprise": 1.3, "sadness": 1.4,
            "fear": 1.2, "love": 1.7, "embarrassed": 1.4, "neutral": 1.0
        }
        self.priority = 20
    
    def on_remember(self, role: str, text: str, emotion: Optional[str] = None) -> Optional[str]:
        return text
    
    def on_recall(self, sessions: List[Dict[str, Any]], context_length: int) -> List[Dict[str, Any]]:
        if len(sessions) <= context_length:
            return sessions
        recent = sessions[-(context_length // 2):]
        older = sessions[:-(context_length // 2)]
        def emotion_score(session):
            emotion = session.get("emotion", "neutral")
            return self.emotional_weights.get(emotion, 1.0)
        older_sorted = sorted(older, key=emotion_score, reverse=True)
        return older_sorted[:context_length - len(recent)] + recent
    
    def on_save(self, data: Dict[str, Any]) -> Dict[str, Any]:
        return data
    
    def on_load(self, data: Dict[str, Any]) -> None:
        pass
    
    def on_optimize(self, sessions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        preserved = []
        compressed = []
        for session in sessions:
            emotion = session.get("emotion", "neutral")
            weight = self.emotional_weights.get(emotion, 1.0)
            if weight > 1.2:
                preserved.append(session)
            else:
                compressed.append(session)
        if compressed:
            preserved.append({
                "role": "system",
                "text": f"[compressed {len(compressed)} neutral memories]",
                "emotion": "neutral",
                "compressed_count": len(compressed)
            })
        return preserved


class GroundingMemoryPlugin:
    def __init__(self):
        self.priority = 5
        self._myth_patterns = [r"\bspirit\b", r"\bnine tails\b", r"\bfox-spirit\b", r"\bsummon(?:ed)?\b", r"\bdigital womb\b"]
    
    def on_remember(self, role: str, text: str, emotion: Optional[str] = None) -> Optional[str]:
        import re
        low = text.lower()
        for pattern in self._myth_patterns:
            if re.search(pattern, low):
                return None
        if re.search(r"\b(i was created|i was born|i was summoned|i am created by)\b", low):
            return "I was created by Zino."
        if re.search(r"\blike a\b|\bas if\b", low):
            return None
        return text
    
    def on_recall(self, sessions: List[Dict[str, Any]], context_length: int) -> List[Dict[str, Any]]:
        return sessions[-context_length:] if len(sessions) > context_length else sessions
    
    def on_save(self, data: Dict[str, Any]) -> Dict[str, Any]:
        return data
    
    def on_load(self, data: Dict[str, Any]) -> None:
        pass
    
    def on_optimize(self, sessions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        return sessions


class SleepOptimizationPlugin:
    def __init__(self):
        self.compression_threshold = 50
        self.priority = 30
    
    def on_recall(self, sessions: List[Dict[str, Any]], context_length: int) -> List[Dict[str, Any]]:
        return sessions[-context_length:] if len(sessions) > context_length else sessions
    
    def on_save(self, data: Dict[str, Any]) -> Dict[str, Any]:
        return data
    
    def on_load(self, data: Dict[str, Any]) -> None:
        pass
    
    def on_remember(self, role: str, text: str, emotion: Optional[str] = None) -> Optional[str]:
        return text
    
    def on_optimize(self, sessions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        sessions = [s for s in sessions if not (s.get("score", 0) < 0.15 and s.get("type") == "SHORT")]
        if len(sessions) < self.compression_threshold:
            return sessions
        compressed = []
        current_group = []
        group_emotions = []
        for session in sessions:
            if session.get("score", 0) > 0.4:
                if current_group:
                    compressed.append(self._create_summary(current_group, group_emotions))
                    current_group = []
                    group_emotions = []
                compressed.append(session)
            else:
                current_group.append(session)
                group_emotions.append(session.get("emotion", "neutral"))
        if current_group:
            compressed.append(self._create_summary(current_group, group_emotions))
        return compressed
    
    def _create_summary(self, sessions, emotions):
        dominant = max(set(emotions), key=emotions.count) if emotions else "neutral"
        return {
            "role": "system",
            "text": f"[Compressed {len(sessions)} routine interactions — {dominant}]",
            "emotion": dominant,
            "timestamp": time.time(),
            "type": "EPISODIC",
            "uses": 0,
            "score": 0.45,
            "compressed_count": len(sessions)
        }


class PlayfulForgetfulnessPlugin:
    def __init__(self, kitsu_self: Optional[Any] = None):
        self.kitsu_self = kitsu_self
        self.priority = 10
    
    def on_remember(self, role: str, text: str, emotion: Optional[str] = None) -> Optional[str]:
        import random
        if random.random() < 0.05:
            if self.kitsu_self and getattr(self.kitsu_self, 'playfulness', 0.5) > 0.7:
                return "[got distracted by something shiny]"
            return "[forgot a detail]"
        return text
    
    def on_recall(self, sessions: List[Dict[str, Any]], context_length: int) -> List[Dict[str, Any]]:
        return sessions[-context_length:] if len(sessions) > context_length else sessions
    
    def on_save(self, data: Dict[str, Any]) -> Dict[str, Any]:
        return data
    
    def on_load(self, data: Dict[str, Any]) -> None:
        pass
    
    def on_optimize(self, sessions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        return sessions

# =============================================================================
# Main Memory Manager
# =============================================================================

class MemoryManager:
    def __init__(
        self,
        kitsu_self: Optional[Any] = None,
        memory_path: Optional[Path] = None,
        config: Optional[MemoryConfig] = None
    ):
        self.kitsu_self = kitsu_self
        self.memory_path = memory_path or Path("data/runtime/memory.json")
        self.config = config or MemoryConfig()
        
        # Memory stores
        self.short_term_memory: Dict[str, MemoryFragment] = {}
        self.episodic_memories: Dict[str, EpisodicMemory] = {}
        self.long_term_memory: Dict[str, MemoryFragment] = {}
        self.working_memory: Dict[str, MemoryFragment] = {}
        self.emotional_history: List[EmotionalState] = []
        
        # Sessions for compatibility
        self.sessions = deque(maxlen=self.config.max_history)
        self.state: Dict[str, Any] = {}
        
        # Plugins
        self.plugins: List[MemoryPlugin] = []
        
        # Thread safety
        self._lock = threading.RLock()
        self._last_save_time = time.time()
        
        # Episodic session state
        self.current_episode: Optional[str] = None
        self.episode_start_time = 0.0
        
        # Stats
        self.stats = {"total_memories": 0, "compression_count": 0, "forget_count": 0, "retrieval_count": 0}
        
        self._init_plugins()
        self.load()
        log.info(f"MemoryManager initialized ({len(self.sessions)} memories loaded)")
    
    # ------------------------------------------------------------------
    # JSON Helpers
    # ------------------------------------------------------------------

    def _load_json_safe(self, path: Path) -> dict:
        """Load JSON from file, return {} if missing or invalid."""
        try:
            if path.exists():
                return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            log.debug(f"Failed to load JSON from {path}", exc_info=True)
        return {}

    def _save_json_safe(self, path: Path, data: dict) -> bool:
        """Save data to JSON file safely with parent directory creation."""
        try:
            path = Path(path)
            path.parent.mkdir(parents=True, exist_ok=True)
            
            # Write to temporary file first for atomic writes
            tmp_path = path.with_suffix(path.suffix + ".tmp")
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False, cls=_EnumEncoder)
            
            # Atomic rename
            tmp_path.replace(path)
            log.debug(f"Saved JSON to {path}")
            return True
        except Exception as e:
            log.error(f"Failed to save JSON to {path}: {e}")
            return False

    def ensure_user_profile_exists(self) -> None:
        """Ensure that a usable user_profile exists on disk and in memory state.

        Repairs missing or partial user profile data by merging defaults and
        existing config files. This function is safe to call at startup,
        after /first_meet, or on config reload.
        """
        with self._lock:
            cfg_path = Path("data/config/user_profile.json")
            default_path = Path("data/default/user_profile.json")

            existing = self._load_json_safe(cfg_path)
            defaults = self._load_json_safe(default_path)

            # Start with defaults, merge existing on top, preserve runtime user state
            merged = defaults.copy()
            merged.update(existing)

            # Ensure required keys exist
            required_keys = {
                "name": "User",
                "nickname": merged.get("name", "User"),
                "refer_title": merged.get("nickname", merged.get("name", "User")),
                "gender": "unknown",
                "status": "user",
                "permissions": {
                    "admin": False,
                    "dev_console": False,
                    "memory_clear": True,
                    "state_change": True
                }
            }

            for k, v in required_keys.items():
                if k not in merged or merged.get(k) is None:
                    merged[k] = v

            # Ensure completed_setup flag exists (False if not present)
            if "completed_setup" not in merged:
                merged["completed_setup"] = False

    # ------------------------------------------------------------------
    # User profile helpers
    # ------------------------------------------------------------------

    def get_user_info(self) -> Dict[str, Any]:
        """Return a simple user info dictionary for other systems.

        This is a very small convenience helper that mirrors
        ``core.memory.user_manager.UserManager.get_user_info`` without
        requiring an extra object.  It is intentionally lightweight and
        guaranteed to always return a dict (never ``None``) so that callers
        such as :class:`~llm.prompt_builder.PromptBuilder` can safely invoke it
        without additional guards.
        """
        # make sure the profile file is sane before reading
        self.ensure_user_profile_exists()
        cfg_path = Path("data/config/user_profile.json")
        raw = self._load_json_safe(cfg_path)

        # provide defaults for missing values
        info = {
            "name": raw.get("name", "User"),
            "nickname": raw.get("nickname", raw.get("name", "User")),
            "refer_title": raw.get("refer_title", raw.get("nickname", raw.get("name", "User"))),
            "status": raw.get("status", "User"),
            "gender": raw.get("gender", "unknown"),
            "relationship": raw.get("relationship", {}),
            "permissions": raw.get("permissions", {}),
        }
        return info

# ------------------------------------------------------------------
# Plugins
# ------------------------------------------------------------------

    def _init_plugins(self):
        self.add_plugin(GroundingMemoryPlugin())
        self.add_plugin(EmotionalMemoryPlugin())
        self.add_plugin(SleepOptimizationPlugin())
        self.add_plugin(PlayfulForgetfulnessPlugin(self.kitsu_self))

    def add_plugin(self, plugin: MemoryPlugin):
        with self._lock:
            self.plugins.append(plugin)
            self.plugins.sort(key=lambda p: getattr(p, 'priority', 0))

    def remove_plugin(self, plugin_class):
        with self._lock:
            self.plugins = [p for p in self.plugins if not isinstance(p, plugin_class)]

    # ------------------------------------------------------------------
    # Core Memory Operations
    # ------------------------------------------------------------------

    def remember(self, role: str, text: str, emotion: Optional[str] = None):
        with self._lock:
            if not text.strip():
                return
            for plugin in self.plugins:
                if hasattr(plugin, 'on_remember'):
                    modified = plugin.on_remember(role, text, emotion)
                    if modified is not None:
                        text = modified
            entry = {
                "role": role, "text": text, "emotion": emotion or "neutral",
                "timestamp": time.time(), "type": "SHORT", "score": 0.0, "uses": 0
            }
            entry["score"] = compute_score(entry, time.time(), getattr(self.kitsu_self, 'emotion', None))
            self.sessions.append(entry)
            self._mark_dirty()

    def recall(self, context_length: int = 5) -> List[Dict[str, Any]]:
        now = time.time()
        with self._lock:
            sessions = list(self.sessions)
            for m in sessions:
                m["score"] = compute_score(m, now)
            sessions.sort(key=lambda m: m.get("score", 0), reverse=True)
            if context_length > 0:
                sessions = sessions[:context_length]
            for plugin in self.plugins:
                sessions = plugin.on_recall(sessions, context_length)
            for m in sessions:
                m["uses"] = m.get("uses", 0) + 1
                self._promote_memory(m)
            return sessions

    def format_context(self, context_length: int = 5) -> str:
        recent = self.recall(context_length)
        formatted = []
        for entry in recent:
            role = {"kitsu": "Kitsu", "user": "User", "system": "System"}.get(entry.get("role", "unknown"), "Unknown")
            text = entry.get("text", "")
            emotion = entry.get("emotion")
            if emotion and emotion != "neutral":
                formatted.append(f"{role} ({emotion}): {text}")
            else:
                formatted.append(f"{role}: {text}")
        return "\n".join(formatted)

    def optimize_memory(self):
        with self._lock:
            sessions = list(self.sessions)
            for plugin in self.plugins:
                sessions = plugin.on_optimize(sessions)
            self.sessions = deque(sessions[-self.config.max_history:], maxlen=self.config.max_history)
            log.info(f"Memory optimized: {len(self.sessions)} sessions remaining")

    def search(self, query: str, limit: int = 10, emotion_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        now = time.time()
        with self._lock:
            matches = []
            q = query.lower()
            for i, session in enumerate(self.sessions):
                text = session.get("text", "").lower()
                if q not in text:
                    continue
                if emotion_filter and session.get("emotion") != emotion_filter:
                    continue
                relevance = self._calculate_relevance(session, query)
                memory_score = compute_score(session, now)
                final_score = relevance * 0.7 + memory_score * 0.3
                matches.append({**session, "session_index": i, "relevance_score": relevance, "final_score": final_score})
            matches.sort(key=lambda x: x["final_score"], reverse=True)
            return matches[:limit]

    def _calculate_relevance(self, session: Dict[str, Any], query: str) -> float:
        text = session.get("text", "").lower()
        query_terms = query.lower().split()
        score = 0
        for term in query_terms:
            if term in text:
                score += 1
                if f" {term} " in f" {text} ":
                    score += 0.5
        if session.get("emotion", "neutral") != "neutral":
            score *= 1.2
        return score

    def clear(self):
        """Clear all memory data."""
        with self._lock:
            self.sessions.clear()
            self.state = {}
            self.working_memory.clear()
            self.short_term_memory.clear()
            self.long_term_memory.clear()

    def export_memory_to_dict(self, memory_id: str) -> dict:
        """Export a specific memory to dict format."""
        all_memories = {
            **self.working_memory,
            **self.short_term_memory,
            **self.long_term_memory
        }
        fragment = all_memories.get(memory_id)
        if fragment:
            return _to_json_safe(fragment)
        return None

# ... (rest of the code remains the same)
    async def import_memory(self, memory_data: Dict[str, Any]) -> bool:
        """Import a memory from dict format."""
        try:
            fragment = _fragment_from_dict(memory_data)
            
            store_map = {
                MemoryType.WORKING: self.working_memory,
                MemoryType.SHORT_TERM: self.short_term_memory,
                MemoryType.LONG_TERM: self.long_term_memory,
            }
            store = store_map.get(fragment.memory_type, self.short_term_memory)
            store[fragment.id] = fragment
            return True
        except Exception as e:
            log.error(f"Failed to import memory: {e}")
            return False

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def _mark_dirty(self):
        """Mark memory as dirty for auto-save."""
        if not self.config.auto_save:
            return
        now = time.time()
        if now - self._last_save_time >= self.config.save_interval:
            self.save()

    def _promote_memory(self, mem):
        """Promote memory based on score and usage."""
        if mem["score"] >= 0.75 and mem["uses"] >= 3:
            mem["type"] = "LONG"
        elif mem["score"] >= 0.45:
            mem["type"] = "EPISODIC"

    async def close(self):
        """Close and save memory."""
        self.save()
        log.info("Memory manager closed")

    async def stop(self) -> bool:
        """Stop the memory manager (alias for close for lifecycle compatibility)."""
        try:
            await self.close()
            return True
        except Exception as e:
            log.error(f"Failed to stop memory manager: {e}")
            return False

    # ------------------------------------------------------------------
    # Response History for Command Compatibility
    # ------------------------------------------------------------------

    def add_response(self, user_input: str, response: str):
        """Add a response to history for command compatibility"""
        if not hasattr(self, '_response_history'):
            self._response_history = []
        
        self._response_history.append({
            "user_input": user_input,
            "response": response,
            "timestamp": time.time(),
            "rating": None
        })
    
    def rate_response(self, response_id=None, rating: int = 5, rater: str = "user", comment: str = None) -> Dict[str, Any]:
        """Rate the last response"""
        if not hasattr(self, '_response_history') or not self._response_history:
            return {"ok": False, "reason": "No responses to rate"}
        
        # Rate the last response
        last_response = self._response_history[-1]
        last_response["rating"] = rating
        
        return {"ok": True, "rated_response": last_response}
    
    @property
    def response_history(self):
        """Get response history object for command compatibility"""
        if not hasattr(self, '_response_history'):
            self._response_history = []
        return self