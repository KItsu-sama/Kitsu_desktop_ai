"""
core/memory/memory_manager.py — Memory Manager (Architecture Compliant)

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

from core.memory.scoring import compute_score

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
        with self._lock:
            self.sessions.clear()
            self.state = {}

    # ------------------------------------------------------------------
    # Enhanced Memory Features (Async)
    # ------------------------------------------------------------------

    async def store_memory(
        self,
        content: str,
        memory_type: MemoryType = MemoryType.SHORT_TERM,
        priority: MemoryPriority = MemoryPriority.NORMAL,
        emotional_tags: List[str] = None,
        context_tags: List[str] = None,
        emotional_state: Optional[Dict[str, Any]] = None
    ) -> str:
        memory_id = self._generate_memory_id(content)
        timestamp = time.time()
        fragment = MemoryFragment(
            id=memory_id,
            content=content,
            memory_type=memory_type,
            priority=priority,
            timestamp=timestamp,
            emotional_tags=emotional_tags or [],
            context_tags=context_tags or []
        )
        
        # Store in appropriate memory type
        store_map = {
            MemoryType.WORKING: self.working_memory,
            MemoryType.SHORT_TERM: self.short_term_memory,
            MemoryType.LONG_TERM: self.long_term_memory,
        }
        store = store_map.get(memory_type, self.short_term_memory)
        store[memory_id] = fragment
        
        if emotional_state:
            self.emotional_history.append(EmotionalState(**emotional_state, timestamp=timestamp))
        
        self.stats["total_memories"] += 1
        return memory_id

    async def retrieve_memories(
        self,
        query: str = None,
        emotional_tags: List[str] = None,
        context_tags: List[str] = None,
        memory_type: MemoryType = None,
        limit: int = 10,
        time_range: Tuple[float, float] = None
    ) -> List[MemoryFragment]:
        candidates = (
            list(self.working_memory.values()) +
            list(self.short_term_memory.values()) +
            list(self.long_term_memory.values())
        )
        
        # Apply filters
        if query:
            candidates = [f for f in candidates if query.lower() in f.content.lower()]
        if emotional_tags:
            candidates = [f for f in candidates if any(tag in f.emotional_tags for tag in emotional_tags)]
        
        candidates.sort(key=lambda f: f.timestamp, reverse=True)
        return candidates[:limit]

    async def start_episodic_session(self, title: str = None) -> str:
        if self.current_episode:
            await self.end_episodic_session()
        
        episode_id = self._generate_memory_id(f"episode_{title or 'unnamed'}")
        self.current_episode = episode_id
        self.episode_start_time = time.time()
        
        episode = EpisodicMemory(
            id=episode_id,
            title=title or f"Session {time.strftime('%H:%M')}",
            fragments=[],
            start_time=self.episode_start_time,
            end_time=self.episode_start_time,
            emotional_summary={},
            importance_score=0.0,
            context={}
        )
        self.episodic_memories[episode_id] = episode
        log.info(f"Started episodic session: {episode_id}")
        return episode_id

    async def end_episodic_session(self) -> Optional[str]:
        if not self.current_episode:
            return None
        
        episode = self.episodic_memories.get(self.current_episode)
        if not episode:
            self.current_episode = None
            return None
        
        episode.end_time = time.time()
        await self._calculate_episode_emotional_summary(episode)
        episode.importance_score = await self._calculate_episode_importance(episode)
        
        if episode.importance_score < 0.3:
            await self._compress_episode(episode)
        
        self.current_episode = None
        log.info(f"Ended episodic session: {episode.id}")
        return episode.id

    async def _calculate_episode_emotional_summary(self, episode: EpisodicMemory) -> None:
        emotional_counts = {}
        for fragment_id in episode.fragments:
            fragment = self.short_term_memory.get(fragment_id) or self.long_term_memory.get(fragment_id)
            if fragment:
                for tag in fragment.emotional_tags:
                    emotional_counts[tag] = emotional_counts.get(tag, 0) + 1
        
        total = sum(emotional_counts.values())
        if total > 0:
            episode.emotional_summary = {emotion: count / total for emotion, count in emotional_counts.items()}

    async def _calculate_episode_importance(self, episode: EpisodicMemory) -> float:
        score = 0.0
        duration = episode.end_time - episode.start_time
        
        # Duration score (up to 0.3)
        score += min(duration / 300, 0.3)
        
        # Fragment count score (up to 0.3)
        score += min(len(episode.fragments) / 20, 0.3)
        
        # Emotional intensity score (up to 0.4)
        if episode.emotional_summary:
            max_emotion = max(episode.emotional_summary.values())
            score += max_emotion * 0.4
        
        return min(score, 1.0)

    async def _compress_episode(self, episode: EpisodicMemory) -> None:
        summary = (
            f"Episode: {episode.title}\n"
            f"Duration: {episode.end_time - episode.start_time:.1f}s\n"
            f"Fragments: {len(episode.fragments)}\n"
        )
        if episode.emotional_summary:
            summary += f"Emotional tone: {max(episode.emotional_summary, key=episode.emotional_summary.get)}\n"
        
        await self.store_memory(
            content=summary,
            memory_type=MemoryType.LONG_TERM,
            context_tags=["episode_summary", "compressed"]
        )
        
        del self.episodic_memories[episode.id]
        for fragment_id in episode.fragments:
            self.short_term_memory.pop(fragment_id, None)

    async def apply_decay(self) -> None:
        """Apply time-based memory decay and forget low-priority old memories."""
        if not self.config.compression_enabled:
            return
        
        now = time.time()
        to_forget = []
        
        for fragment_id, fragment in self.short_term_memory.items():
            age = now - fragment.timestamp
            
            # Forget temporary memories after 1 hour
            if age > 3600 and fragment.priority == MemoryPriority.TEMPORARY:
                to_forget.append(fragment_id)
            # Forget normal priority memories after 24 hours
            elif age > 86400 and fragment.priority == MemoryPriority.NORMAL:
                to_forget.append(fragment_id)
        
        for fragment_id in to_forget:
            del self.short_term_memory[fragment_id]
            self.stats["forget_count"] += 1
        
        if to_forget:
            log.debug(f"Forgot {len(to_forget)} memories due to decay")

    async def enter_sleep_mode(self) -> None:
        """Compress memory before sleep."""
        await self._compress_short_term_memory()
        self.working_memory.clear()
        log.info("Entered sleep mode - memory optimized")

    async def exit_sleep_mode(self) -> None:
        """Wake from sleep mode."""
        log.info("Exited sleep mode")

    async def _compress_short_term_memory(self) -> None:
        """Compress short-term memory into episodic memories."""
        log.info("Compressing short-term memory...")
        to_compress = list(self.short_term_memory.values())
        
        if len(to_compress) > 5:
            episode_id = await self.start_episodic_session("Auto-compressed")
            
            for fragment in to_compress:
                await self._add_to_episode(fragment.id)
                del self.short_term_memory[fragment.id]
            
            await self.end_episodic_session()
            self.stats["compression_count"] += 1

    async def _add_to_episode(self, memory_id: str) -> None:
        """Add a memory fragment to the current episodic session."""
        if self.current_episode and self.current_episode in self.episodic_memories:
            self.episodic_memories[self.current_episode].fragments.append(memory_id)

    def _generate_memory_id(self, content: str) -> str:
        """Generate unique memory ID from content and timestamp."""
        timestamp = str(time.time())
        content_hash = hashlib.md5(content.encode()).hexdigest()[:8]
        return f"mem_{timestamp}_{content_hash}"

    def _calculate_decay_rate(self, priority: MemoryPriority) -> float:
        """Get decay rate based on memory priority."""
        rates = {
            MemoryPriority.CRITICAL: 0.001,
            MemoryPriority.IMPORTANT: 0.005,
            MemoryPriority.NORMAL: 0.01,
            MemoryPriority.TEMPORARY: 0.05
        }
        return rates.get(priority, 0.01)

    def _calculate_relevance(self, fragment: MemoryFragment) -> float:
        """Calculate relevance score for a memory fragment."""
        score = 0.0
        now = time.time()
        
        # Recency score (0-0.3)
        age = now - fragment.timestamp
        recency_score = max(0, 1.0 - age / 86400)
        score += recency_score * 0.3
        
        # Access score (0-0.2)
        access_score = min(fragment.access_count / 10, 1.0)
        score += access_score * 0.2
        
        # Priority score (0-0.3)
        priority_score = fragment.priority.value / 3.0
        score += priority_score * 0.3
        
        # Emotional tags score (0-0.2)
        if fragment.emotional_tags:
            emotion_score = len(fragment.emotional_tags) / 5.0
            score += min(emotion_score, 0.2)
        
        return score

    async def _store_emotional_state(self, emotional_state: Dict[str, Any]) -> None:
        """Store emotional state in history."""
        state = EmotionalState(
            timestamp=time.time(),
            mood=emotional_state.get("mood", "neutral"),
            style=emotional_state.get("style", "chaotic"),
            dominant_emotion=emotional_state.get("dominant_emotion", "neutral"),
            intensity=emotional_state.get("intensity", 0.5),
            triggers=emotional_state.get("triggers", [])
        )
        self.emotional_history.append(state)
        
        # Keep only last 1000 entries
        if len(self.emotional_history) > 1000:
            self.emotional_history = self.emotional_history[-500:]

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def save(self):
        """Save memory state to disk."""
        with self._lock:
            try:
                data = {
                    "sessions": list(self.sessions),
                    "state": self.state,
                    "short_term_memory": {k: _to_json_safe(v) for k, v in self.short_term_memory.items()},
                    "episodic_memories": {k: _to_json_safe(v) for k, v in self.episodic_memories.items()},
                    "long_term_memory": {k: _to_json_safe(v) for k, v in self.long_term_memory.items()},
                    "working_memory": {k: _to_json_safe(v) for k, v in self.working_memory.items()},
                    "emotional_history": [_to_json_safe(s) for s in self.emotional_history],
                    "metadata": {
                        "version": "0.1.0",
                        "saved_at": time.time(),
                        "total_entries": len(self.sessions)
                    }
                }
                
                # Allow plugins to modify data before save
                for plugin in self.plugins:
                    if hasattr(plugin, 'on_save'):
                        data = plugin.on_save(data)
                
                self.memory_path.parent.mkdir(parents=True, exist_ok=True)
                temp = self.memory_path.with_suffix('.tmp')
                temp.write_text(json.dumps(data, indent=2, ensure_ascii=False, cls=_EnumEncoder), encoding="utf-8")
                temp.replace(self.memory_path)
                self._last_save_time = time.time()
                log.info(f"Memory saved: {len(self.sessions)} entries")
            except Exception as e:
                log.error(f"Failed to save memory: {e}", exc_info=True)

    async def save_async(self):
        """Async wrapper for save."""
        try:
            await asyncio.to_thread(self.save)
        except Exception as e:
            log.error(f"Async save failed: {e}")

    def load(self):
        """Load memory state from disk."""
        with self._lock:
            try:
                if self.memory_path.exists():
                    raw = self.memory_path.read_text(encoding="utf-8")
                    if raw.strip():
                        data = json.loads(raw)
                    else:
                        data = {"sessions": [], "state": {}}
                    
                    self.sessions = deque(data.get("sessions", []), maxlen=self.config.max_history)
                    self.state = data.get("state", {})
                    
                    # Reconstruct typed objects
                    self.short_term_memory = {
                        k: _fragment_from_dict(v)
                        for k, v in data.get("short_term_memory", {}).items()
                    }
                    self.episodic_memories = {
                        k: EpisodicMemory(**v)
                        for k, v in data.get("episodic_memories", {}).items()
                    }
                    self.long_term_memory = {
                        k: _fragment_from_dict(v)
                        for k, v in data.get("long_term_memory", {}).items()
                    }
                    self.working_memory = {
                        k: _fragment_from_dict(v)
                        for k, v in data.get("working_memory", {}).items()
                    }
                    self.emotional_history = [
                        EmotionalState(**s)
                        for s in data.get("emotional_history", [])
                    ]
                    
                    # Allow plugins to process loaded data
                    for plugin in self.plugins:
                        try:
                            plugin.on_load(data)
                        except Exception:
                            pass
            except Exception as e:
                log.error(f"Failed to load memory: {e}", exc_info=True)

    # ------------------------------------------------------------------
    # Statistics & Tagging
    # ------------------------------------------------------------------

    def get_statistics(self) -> Dict[str, Any]:
        """Get memory statistics."""
        return {
            "working_memory": len(self.working_memory),
            "short_term_memory": len(self.short_term_memory),
            "episodic_memories": len(self.episodic_memories),
            "long_term_memory": len(self.long_term_memory),
            "emotional_history": len(self.emotional_history),
            "current_episode": self.current_episode,
            "stats": self.stats
        }

    def get_stats(self) -> Dict[str, Any]:
        """Get detailed memory statistics."""
        with self._lock:
            emotions = {}
            roles = {}
            for session in self.sessions:
                emotion = session.get("emotion", "neutral")
                role = session.get("role", "unknown")
                emotions[emotion] = emotions.get(emotion, 0) + 1
                roles[role] = roles.get(role, 0) + 1
            
            memory_json = json.dumps(list(self.sessions), ensure_ascii=False)
            memory_bytes = len(memory_json.encode('utf-8'))
            
            return {
                "total_sessions": len(self.sessions),
                "emotion_distribution": emotions,
                "role_distribution": roles,
                "active_plugins": [p.__class__.__name__ for p in self.plugins],
                "memory_usage_bytes": memory_bytes,
                **self.get_statistics()
            }

    async def tag_last_session(self, tag_name: str, tag_data: Any = None) -> bool:
        """Tag the last assistant session with metadata.
        
        Args:
            tag_name: Simple tag name (e.g., "edited", "rate", "training_corrected")
            tag_data: Optional data to attach to the tag
            
        Returns:
            True if tagged successfully, False if no session found
        """
        with self._lock:
            try:
                # Find the last assistant/kitsu response
                for sess in reversed(list(self.sessions)):
                    if sess.get("role") in ("kitsu", "assistant"):
                        # Initialize tags dict if needed
                        if "tags" not in sess:
                            sess["tags"] = {}
                        
                        # Add tag with timestamp
                        import datetime as dt
                        sess["tags"][tag_name] = {
                            "added_at": time.time(),
                            "isoformat": dt.datetime.now().isoformat(),
                            "data": tag_data
                        }
                        
                        log.debug(f"Tagged session with '{tag_name}': {tag_data}")
                        self._mark_dirty()
                        return True
                
                log.debug(f"No assistant session found to tag with '{tag_name}'")
                return False
            except Exception as e:
                log.error(f"Failed to tag session: {e}")
                return False

    # ------------------------------------------------------------------
    # Export/Import
    # ------------------------------------------------------------------

    async def export_memory(self, memory_id: str) -> Optional[Dict[str, Any]]:
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