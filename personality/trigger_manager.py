"""
core/personality/trigger_manager.py

TriggerManager = Manager — Lifecycle and state of emotion triggers.

Responsibilities:
- Load triggers from data/triggers.json
- Manage cooldowns per trigger
- Fire triggers and return emotion effects
- Provide trigger info and modifiers
- Add/update triggers and persist to disk

Non-responsibilities:
- Emotion stack manipulation (delegates to emotion_engine)
- UI rendering
- Training or learning
"""

import time
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List

log = logging.getLogger(__name__)


class TriggerManager:
    """
    Manages emotion triggers with cooldowns.
    
    Triggers are defined in data/triggers.json and can be:
    - Fired manually via commands
    - Triggered by keywords/symbols in user input
    - Applied automatically based on emotional analysis
    """
    
    def __init__(self, triggers_path: Optional[Path] = None):
        """
        Initialize trigger manager.
        
        Args:
            triggers_path: Path to triggers.json (default: data/triggers.json)
        """
        self.triggers_path = triggers_path or Path("data/triggers.json")
        self.triggers = self._load_triggers()
        self.last_trigger_times: Dict[str, float] = {}
        
        log.info(f"TriggerManager loaded: {len(self.triggers)} triggers")
    
    def _load_triggers(self) -> Dict[str, Any]:
        """
        Load triggers from JSON file.
        
        Returns:
            Dict of trigger definitions
        """
        if not self.triggers_path.exists():
            log.warning(f"Triggers file not found: {self.triggers_path}")
            return {}
        
        try:
            data = json.loads(self.triggers_path.read_text(encoding="utf-8"))
            return data.get("triggers", {})
        except Exception as e:
            log.error(f"Failed to load triggers: {e}")
            return {}
    
    def reload(self):
        """Reload triggers from file"""
        self.triggers = self._load_triggers()
        log.info(f"Triggers reloaded: {len(self.triggers)} triggers")
    
    def can_fire(self, trigger_name: str) -> bool:
        """
        Check if trigger can fire (respects cooldown).
        
        Args:
            trigger_name: Name of trigger to check
            
        Returns:
            True if trigger is off cooldown, False otherwise
        """
        trigger = self.triggers.get(trigger_name, {})
        cooldown = trigger.get("cooldown", 0.0)
        last_time = self.last_trigger_times.get(trigger_name, 0)
        
        elapsed = time.time() - last_time
        return elapsed >= cooldown
    
    def fire_trigger(self, trigger_name: str) -> Optional[List[Dict[str, Any]]]:
        """
        Fire trigger if cooldown allows.
        
        Args:
            trigger_name: Name of trigger to fire
            
        Returns:
            List of emotion effects, or None if on cooldown or not found
        """
        if not self.can_fire(trigger_name):
            log.debug(f"Trigger {trigger_name} on cooldown")
            return None
        
        # Update last fire time
        self.last_trigger_times[trigger_name] = time.time()
        
        # Get emotions
        trigger = self.triggers.get(trigger_name, {})
        emotions = trigger.get("emotions", [])
        
        log.debug(f"Trigger fired: {trigger_name} ({len(emotions)} emotions)")
        return emotions
    
    def get_modifiers(self, trigger_name: str) -> Dict[str, float]:
        """
        Get personality modifiers for trigger.
        
        Args:
            trigger_name: Name of trigger
            
        Returns:
            Dict of modifiers (e.g., {"happy": 0.1, "behave": 0.05})
        """
        trigger = self.triggers.get(trigger_name, {})
        return trigger.get("modifiers", {})
    
    def get_trigger_info(self, trigger_name: str) -> Optional[Dict[str, Any]]:
        """
        Get full trigger info.
        
        Args:
            trigger_name: Name of trigger
            
        Returns:
            Trigger definition dict, or None if not found
        """
        return self.triggers.get(trigger_name)
    
    def add_trigger(self, trigger_name: str, trigger_def: Dict[str, Any]) -> bool:
        """
        Add or update a trigger and persist to disk.
        
        Args:
            trigger_name: Name of trigger
            trigger_def: Trigger definition with cooldown, emotions, modifiers
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if not trigger_name:
                return False
            
            # Normalize and apply defaults
            td = dict(trigger_def)
            cooldown = max(0.0, float(td.get('cooldown', 5.0)))
            emotions = td.get('emotions') or []
            
            # Normalize emotions
            normalized_emotions = []
            for e in emotions:
                if isinstance(e, dict):
                    name = e.get('name')
                    if not name:
                        continue
                    intensity = float(e.get('intensity', 0.5))
                    duration = float(e.get('duration', 10.0))
                    normalized_emotions.append({
                        'name': name,
                        'intensity': intensity,
                        'duration': duration
                    })
                elif isinstance(e, (list, tuple)) and len(e) >= 1:
                    name = e[0]
                    intensity = float(e[1]) if len(e) > 1 else 0.5
                    duration = float(e[2]) if len(e) > 2 else 10.0
                    normalized_emotions.append({
                        'name': name,
                        'intensity': intensity,
                        'duration': duration
                    })
            
            # Normalize modifiers
            modifiers = {}
            for k, v in (td.get('modifiers') or {}).items():
                try:
                    modifiers[k] = float(v)
                except Exception:
                    continue
            
            # Build persisted definition
            to_write = {
                'cooldown': cooldown,
                'emotions': normalized_emotions,
                'modifiers': modifiers
            }
            
            # Load full file and update
            if not self.triggers_path.exists():
                base = {'triggers': {}}
            else:
                try:
                    base = json.loads(self.triggers_path.read_text(encoding='utf-8'))
                except Exception:
                    base = {'triggers': {}}
            
            if 'triggers' not in base or not isinstance(base['triggers'], dict):
                base['triggers'] = {}
            
            base['triggers'][trigger_name] = to_write
            
            # Persist atomically
            tmp = self.triggers_path.with_suffix('.tmp')
            with open(tmp, 'w', encoding='utf-8') as f:
                json.dump(base, f, indent=2)
            tmp.replace(self.triggers_path)
            
            # Update in-memory
            self.triggers[trigger_name] = to_write
            log.info(f"Trigger added/updated: {trigger_name}")
            return True
            
        except Exception as e:
            log.exception(f"Failed to add trigger: {e}")
            return False
    
    def list_triggers(self) -> Dict[str, Any]:
        """
        Return current triggers mapping.
        
        Returns:
            Dict of all trigger definitions
        """
        return self.triggers.copy()
    
    def delete_trigger(self, trigger_name: str) -> bool:
        """
        Delete a trigger and persist change.
        
        Args:
            trigger_name: Name of trigger to delete
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if trigger_name not in self.triggers:
                return False
            
            # Remove from memory
            del self.triggers[trigger_name]
            
            # Load full file and update
            if self.triggers_path.exists():
                base = json.loads(self.triggers_path.read_text(encoding='utf-8'))
                if 'triggers' in base and trigger_name in base['triggers']:
                    del base['triggers'][trigger_name]
                    
                    # Persist
                    tmp = self.triggers_path.with_suffix('.tmp')
                    with open(tmp, 'w', encoding='utf-8') as f:
                        json.dump(base, f, indent=2)
                    tmp.replace(self.triggers_path)
            
            log.info(f"Trigger deleted: {trigger_name}")
            return True
            
        except Exception as e:
            log.exception(f"Failed to delete trigger: {e}")
            return False