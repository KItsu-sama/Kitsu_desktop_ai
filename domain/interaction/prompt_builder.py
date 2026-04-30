"""
ai/prompt_builder.py

Prompt construction system extracted and enhanced from legacy code.

Builds prompts with personality, memory, and emotion context for LLM integration.
Supports both character and generic modes with template loading.
"""

import logging
from pathlib import Path
from typing import Dict, Any, Optional, Sequence
from dataclasses import dataclass

from domain.personality.emotion_config import get_style_rules

log = logging.getLogger(__name__)


@dataclass
class PromptConfig:
    """Configuration for prompt building."""
    max_chars: int = 900
    templates_path: Path = Path("data/templates")
    memory_limit: int = 5
    include_user_info: bool = True
    include_memory: bool = True


class PromptBuilder:
    """
    Builds prompts with personality, memory, and emotion context.
    
    Enhanced version of legacy PromptBuilder with:
    - Better error handling
    - Template reloading
    - Modern architecture integration
    - Character and generic mode support
    """

    def __init__(
        self,
        character_context: str,
        memory_manager: Optional[Any] = None,
        config: Optional[PromptConfig] = None,
    ):
        """
        Initialize prompt builder.
        
        Args:
            character_context: Base character description/context
            memory_manager: Memory system for context retrieval
            config: Prompt building configuration
        """
        self.character_context = character_context
        self.memory = memory_manager
        self.config = config or PromptConfig()
        
        # Load mode templates
        self.mode_templates = self._load_mode_templates()
        
        log.info(f"PromptBuilder initialized with {len(self.mode_templates)} mode templates")

    # ------------------------------------------------------------------
    # Template loading
    # ------------------------------------------------------------------

    def _load_mode_templates(self) -> Dict[str, str]:
        """Load mode-specific prompt templates."""
        templates = {}
        mode_dir = self.config.templates_path / "mode_templates"

        if not mode_dir.exists():
            log.warning(f"Mode templates directory not found: {mode_dir}")
            return self._get_fallback_templates()

        template_files = ["behave.txt", "mean.txt", "flirty.txt", "protective.txt"]
        
        for mode_file in template_files:
            mode_name = mode_file.replace(".txt", "")
            mode_path = mode_dir / mode_file
            
            try:
                if mode_path.exists():
                    templates[mode_name] = mode_path.read_text(encoding="utf-8").strip()
                    log.debug(f"Loaded template: {mode_name}")
                else:
                    log.warning(f"Template not found: {mode_path}")
                    templates[mode_name] = self._get_fallback_templates().get(mode_name, "")
            except Exception as e:
                log.error(f"Error loading template {mode_path}: {e}")
                templates[mode_name] = self._get_fallback_templates().get(mode_name, "")

        return templates

    def _get_fallback_templates(self) -> Dict[str, str]:
        """Get fallback templates when files are not available."""
        return {
            "behave": "## Mode: BEHAVE\nYou are friendly, playful, and supportive. Be kind but teasing.",
            "mean": "## Mode: MEAN\nYou are mischievous and enjoy teasing. Be playfully mean but not hurtful.",
            "flirty": "## Mode: FLIRTY\nYou are flirtatious and charming. Be playful and affectionate.",
            "protective": "## Mode: PROTECTIVE\nYou are caring and defensive. Be supportive but assertive."
        }

    def _get_style_modifier(self, style: str) -> str:
        """Get style-specific modifier text."""
        style_rules = get_style_rules(style)
        
        modifiers = {
            "chaotic": f"Be energetic, unpredictable, and playful. Use exclamations and emotes. Max {style_rules.get('max_words', 25)} words.",
            "sweet": f"Be warm, gentle, and caring. Use soft language and affection. Max {style_rules.get('max_words', 20)} words.",
            "cold": f"Be polite but distant. Keep responses brief and emotionally reserved. Max {style_rules.get('max_words', 12)} words.",
            "direct": f"Be extremely concise. Respond with minimal words, mostly emotes or sounds. Max {style_rules.get('max_words', 5)} words.",
            "sarcastic": f"Be witty and dry. Use ironic humor. Max {style_rules.get('max_words', 18)} words.",
            "playful": f"Be light and teasing. Use jokes and friendly banter. Max {style_rules.get('max_words', 20)} words.",
            "eerie": f"Be mysterious and unsettlingly calm. No emojis. Max {style_rules.get('max_words', 15)} words."
        }
        
        return modifiers.get(style, f"Use your natural personality. Max {style_rules.get('max_words', 20)} words.")

    # ------------------------------------------------------------------
    # User info handling
    # ------------------------------------------------------------------

    def _get_user_info_block(self) -> str:
        """
        Safely retrieve user info and return a formatted string block.
        Enhanced error handling from legacy version.
        """
        if not self.memory or not self.config.include_user_info:
            return self._format_default_user_block()

        try:
            # Attempt to get user info from memory manager
            if hasattr(self.memory, 'get_user_info'):
                raw = self.memory.get_user_info()
            else:
                return self._format_default_user_block()

            # Validate response type
            if not isinstance(raw, dict):
                log.debug(f"get_user_info returned {type(raw).__name__}, using default user info")
                return self._format_default_user_block()

            # Extract fields with safe defaults
            name = raw.get("name", "User")
            nickname = raw.get("nickname", name)
            title = raw.get("refer_title", nickname)
            status = raw.get("status", "User")
            
            # Handle relationship data safely
            rel = raw.get("relationship", {})
            if not isinstance(rel, dict):
                rel = {}
            
            trust = int(float(rel.get("trust_level", 0.5)) * 100)
            affinity = int(float(rel.get("affinity", 1.0)) * 100)
            lore = str(rel.get("lore", "")).strip()
            
            # Handle permissions safely
            perms = raw.get("permissions", {})
            if not isinstance(perms, dict):
                perms = {}

            lines = [
                "\n## User Profile",
                f"- Name: {name}",
                f"- Kitsu calls you: {title}",
                f"- Status: {status}",
                f"- Trust: {trust}/100",
                f"- Affinity: {affinity}/100",
            ]
            
            if lore:
                lines.append(f"- Lore: {lore}")
            
            if perms:
                lines.append("- Permissions:")
                for k, v in perms.items():
                    lines.append(f"   - {k}: {v}")

            return "\n".join(lines)

        except Exception as e:
            log.warning(f"User info retrieval failed: {e}")
            return self._format_default_user_block()

    def _format_default_user_block(self) -> str:
        """Format default user info block."""
        return (
            "\n## User Profile\n"
            "- Name: User\n"
            "- Kitsu calls you: User\n"
            "- Status: User\n"
            "- Trust: 50/100\n"
            "- Affinity: 100/100"
        )

    # ------------------------------------------------------------------
    # Public prompt builders
    # ------------------------------------------------------------------

    def build_conversational_prompt(
        self,
        user_input: str,
        mood: str = "behave",
        style: str = "chaotic",
        memory_limit: Optional[int] = None,
    ) -> str:
        """
        Build a conversational response prompt.
        
        Enhanced from legacy version with better error handling.
        """
        memory_limit = memory_limit or self.config.memory_limit
        
        # Memory context
        memory_context = ""
        if self.memory and self.config.include_memory:
            try:
                if hasattr(self.memory, 'format_context'):
                    memory_context = self.memory.format_context(memory_limit)
                elif hasattr(self.memory, 'recall'):
                    recent = self.memory.recall(context_length=memory_limit) or []
                    if recent:
                        memory_context = "Context:\n" + "\n".join(f"- {m}" for m in recent[-3:])
                else:
                    memory_context = ""
            except Exception as e:
                log.warning(f"Memory context failed: {e}")

        mode_template = self.mode_templates.get(mood, self.mode_templates.get("behave", ""))
        style_modifier = self._get_style_modifier(style)
        user_info_block = self._get_user_info_block()

        prompt = f"""{self.character_context}

{mode_template}

## Style: {style.upper()}
{style_modifier}
{user_info_block}

{memory_context}

## Current Message
User: {user_input}

Respond as Kitsu. Stay in character. Keep response natural and conversational.
Reply to the user in the same tone and style as the examples.
Do not summarize your identity unless directly asked.

## Response Guidelines
- Keep responses concise (1-3 sentences normally, max 5 sentences)
- Be conversational, not verbose
- Avoid long monologues or explanations
- Match the energy level of the conversation

Kitsu:"""
        
        # Truncate if needed
        if len(prompt) > self.config.max_chars:
            prompt = self._truncate_prompt(prompt)
        
        return prompt

    def build_emotion_analysis_prompt(self, text: str) -> str:
        """Build prompt for emotion analysis."""
        prompt = f"""Analyze the emotional content and intent of this message.

Input: "{text}"

Return ONLY valid JSON with these fields:
{{
  "intent": "one word intent (ask, joke, flirt, insult, praise, compliment, command, etc.)",
  "sentiment": "positive | neutral | negative",
  "emotion": "joy | sadness | anger | fear | surprise | disgust | neutral",
  "trigger": "emotional trigger if any (teased, praised, insulted, ignored, complimented, etc.) or null"
}}

JSON:"""
        return prompt

    def build_reaction_planning_prompt(
        self,
        user_input: str,
        emotion_analysis: Dict[str, Any],
        mood: str,
        style: str,
    ) -> str:
        """Build prompt for reaction planning."""
        import json
        prompt = f"""Plan Kitsu's reaction to this interaction.

Current State:
- Mood: {mood}
- Style: {style}

User Input: "{user_input}"

Emotion Analysis:
{json.dumps(emotion_analysis, indent=2)}

Return ONLY valid JSON with:
{{
  "plan": "brief description of intended approach",
  "expression": "primary emotion to display (happy, annoyed, flirty, shy, smug, etc.)",
  "retaliation": "none | mild | strong | playful"
}}

JSON:"""
        return prompt

    def build_greeting_prompt(self, user_title: str, mood: str, style: str) -> str:
        """Build greeting prompt."""
        mode_flavors = {
            "behave": "friendly, energetic, and welcoming",
            "mean": "playfully bratty and teasing, but still excited to see them",
            "flirty": "charming, coy, and affectionate with fox-spirit mystique",
            "protective": "caring but assertive, defensive of user",
        }
        style_hints = {
            "chaotic": "Lots of energy! Exclamations! Playful and bouncy!",
            "sweet": "Warm, gentle, soft and caring.",
            "cold": "Brief, polite, subtle warmth.",
            "direct": "Minimal words. Mostly emotes or sounds.",
            "sarcastic": "Dry humor, witty remarks. ",
            "playful": "Light teasing, jokes, fun banter.",
            "eerie": "Mysterious, unsettling calm, no emojis.",
        }
        flavor = mode_flavors.get(mood, "friendly and playful")
        style_hint = style_hints.get(style, "Be natural and expressive.")

        return f"""{self.character_context}

## Current Mode: {mood.upper()}
Be {flavor}.

## Current Style: {style.upper()}
{style_hint}

{user_title} has just woken you up. Respond with a brief, natural greeting.

## Requirements
- ONE OR TWO sentences MAXIMUM
- Be casual and conversational
- Match your {mood} mood and {style} style
- DO NOT describe actions in third person
- DO NOT introduce yourself or explain who you are
- Just greet them naturally
- Use dialogue format, not narration

Now generate a short greeting (one or two sentences)."""

    def reload_templates(self) -> bool:
        """Reload mode templates from disk."""
        try:
            log.info("Reloading mode templates...")
            old_count = len(self.mode_templates)
            self.mode_templates = self._load_mode_templates()
            new_count = len(self.mode_templates)
            log.info(f"Reloaded templates: {old_count} -> {new_count}")
            return True
        except Exception as e:
            log.error(f"Failed to reload templates: {e}")
            return False

    # ------------------------------------------------------------------
    # Helper methods
    # ------------------------------------------------------------------

    def _truncate_prompt(self, prompt: str) -> str:
        """Truncate prompt to fit max_chars limit."""
        if len(prompt) <= self.config.max_chars:
            return prompt
        
        # Try to preserve important sections
        if "Context:\n" in prompt:
            before, after = prompt.split("Context:\n", 1)
            new_prompt = before + "Context:\n" + after[:80] + "..."
            if len(new_prompt) <= self.config.max_chars:
                return new_prompt
            prompt = before + "(Context trimmed)"
        
        # Final truncation
        if len(prompt) > self.config.max_chars:
            return prompt[:self.config.max_chars - 20].rstrip() + "\n\nKitsu:"
        
        return prompt

    def update_config(self, **kwargs) -> None:
        """Update configuration parameters."""
        for key, value in kwargs.items():
            if hasattr(self.config, key):
                setattr(self.config, key, value)
                log.debug(f"Updated prompt config: {key} = {value}")
            else:
                log.warning(f"Unknown config parameter: {key}")


class CharacterPromptBuilder:
    """
    Minimal prompt builder for character models.
    
    Extracted and enhanced from legacy CharacterPromptBuilder.
    """

    def __init__(self, memory_manager: Optional[Any] = None, max_chars: int = 900):
        self.memory = memory_manager
        self.max_chars = int(max_chars)
        log.info("CharacterPromptBuilder initialized (max_chars=%d)", self.max_chars)

    def build_character_prompt(
        self,
        user_input: str,
        emotional_state: Optional[Dict[str, Any]] = None,
        user_info: Optional[Dict[str, Any]] = None,
        recent_commands: Optional[Sequence[Dict[str, Any]]] = None,
        system_context: Optional[Dict[str, Any]] = None,
        allow_trigger: bool = True,
    ) -> str:
        """
        Build character prompt from emotional state.
        
        Enhanced from legacy version with better error handling.
        """
        try:
            # Convert state dict to emotion projection format
            eproj = self._state_dict_to_emotion_projection(emotional_state or {})
            
            return self.build_prompt(
                user_input=user_input,
                emotion_projection=eproj,
                user_info=user_info,
                recent_commands=recent_commands,
                allow_trigger=allow_trigger,
            )
        except Exception as e:
            log.error(f"Error building character prompt: {e}")
            # Fallback to minimal prompt
            return f"User: {user_input}\n\nKitsu:"

    @staticmethod
    def _state_dict_to_emotion_projection(state: Dict[str, Any]) -> Dict[str, Any]:
        """Convert state dict to emotion projection format."""
        return {
            "mood": state.get("mood", "behave"),
            "style": state.get("style", "chaotic"),
            "dominant": state.get("dominant_emotion", state.get("dominant", "neutral")),
            "dominant_emotion": state.get("dominant_emotion", "neutral"),
            "dominant_value": state.get("emotion_intensity", state.get("confidence", None)),
            "trigger": state.get("trigger"),
            "trigger_value": state.get("trigger_value"),
            "resistance": state.get("resistance", 0.0),
            "stack_size": state.get("stack_size", 0),
            "is_hidden": state.get("is_hidden", False),
        }

    def build_prompt(
        self,
        user_input: str,
        emotion_projection: Dict[str, Any],
        user_info: Optional[Dict[str, Any]] = None,
        recent_commands: Optional[Sequence[Dict[str, Any]]] = None,
        allow_trigger: bool = True,
    ) -> str:
        """Build prompt from emotion projection."""
        try:
            user_block = self._format_user_block(user_info)
            emotion_block = self._format_emotion_block(emotion_projection, allow_trigger=allow_trigger)
            memory_block = self._format_memory_block(user_input)

            sections = [s for s in [user_block, emotion_block, memory_block] if s]
            sections.append(self._format_user_line(user_info, user_input))

            prompt = "\n\n".join(sections).strip()
            if len(prompt) > self.max_chars:
                prompt = self._truncate_prompt(prompt)
            return prompt + "\n\nKitsu:"
        except Exception as e:
            log.error(f"Error building prompt: {e}")
            return f"User: {user_input}\n\nKitsu:"

    def _format_user_block(
        self,
        user_info: Optional[Dict[str, Any]],
        include_optional: bool = False,
    ) -> str:
        """Format user information block."""
        if not user_info:
            return "User: Unknown"
        
        try:
            name = user_info.get("nickname") or user_info.get("name") or "User"
            rel = user_info.get("relationship", {}) or {}
            trust = rel.get("trust_level")
            label = "acquaintance"
            
            if isinstance(trust, (int, float)):
                t = float(trust)
                label = "close" if t > 0.75 else "friend" if t > 0.4 else "acquaintance"

            if include_optional:
                title = user_info.get("refer_title") or user_info.get("title")
                parts = [f"User: {name} ({label})"]
                if title:
                    parts.append(f"Title: {title}")
                if trust is not None:
                    parts.append(f"Trust: {round(float(trust), 2)}")
                return " | ".join(parts)
            return f"User: {name} ({label})"
        except Exception as e:
            log.warning(f"Error formatting user block: {e}")
            return "User: Unknown"

    def _format_emotion_block(
        self,
        eproj: Dict[str, Any],
        allow_trigger: bool = True,
    ) -> str:
        """Format emotion projection block."""
        if not eproj:
            return ""

        try:
            # Auto mode handling
            if eproj.get("mode") == "auto" or eproj.get("emotion_mode") == "auto":
                mood = eproj.get("mood", "behave")
                style = eproj.get("style", "chaotic")
                return f"[mood: {mood}] [style: {style}]"

            mood = eproj.get("mood") or eproj.get("mode") or "behave"
            style = eproj.get("style") or "chaotic"
            dominant = eproj.get("dominant") or eproj.get("dominant_emotion") or "neutral"
            dom_val = eproj.get("dominant_value", eproj.get("dominance"))
            dom_level = self._to_level(dom_val) if dom_val is not None else "none"

            lines = [
                f"[mood: {mood}] [style: {style}]",
                f"[dominant: {dominant} ({dom_level})]",
            ]

            # Rich fields from EmotionEngine
            resistance = float(eproj.get("resistance", 0.0))
            stack_size = int(eproj.get("stack_size", 0))
            is_hidden = bool(eproj.get("is_hidden", False))

            rich_parts = []
            if resistance > 0.1:
                rich_parts.append(f"[resistance: {self._to_level(resistance)}]")
            if stack_size > 1:
                rich_parts.append(f"[stack: {stack_size}]")
            if is_hidden:
                rich_parts.append("[hidden]")
            if rich_parts:
                lines.append(" ".join(rich_parts))

            if allow_trigger:
                trig = eproj.get("trigger")
                if trig:
                    trig_val = eproj.get("trigger_value")
                    trig_level = self._to_level(trig_val) if trig_val is not None else "none"
                    lines.append(f"trigger: {trig} ({trig_level})")

            return "Emotion:\n" + "\n".join(lines)
        except Exception as e:
            log.warning(f"Error formatting emotion block: {e}")
            return ""

    @staticmethod
    def _to_level(value: float) -> str:
        """Convert float value to level string."""
        try:
            v = float(value)
        except Exception:
            return "none"
        v = max(0.0, min(1.0, v))
        levels = ["none", "low", "mid", "high", "extreme"]
        idx = int(round(v * (len(levels) - 1)))
        return levels[idx]

    def _format_memory_block(self, user_input: str) -> str:
        """Format memory context block."""
        if not self.memory:
            return ""
        
        try:
            # Try different memory access methods
            recent = []
            if hasattr(self.memory, "recall"):
                recent = self.memory.recall(context_length=3) or []
            elif hasattr(self.memory, "recent"):
                recent = self.memory.recent(3) or []
            elif hasattr(self.memory, "get_recent"):
                recent = self.memory.get_recent(3) or []
        except Exception as e:
            log.debug("Memory recall failed: %s", e)
            recent = []

        facts = []
        for mem in recent[-3:]:
            try:
                if isinstance(mem, dict):
                    text = mem.get("text") or mem.get("content") or ""
                elif isinstance(mem, str):
                    text = mem
                else:
                    text = str(mem)
                
                text = text.strip()
                if not text:
                    continue
                if user_input and text.lower() in user_input.lower():
                    continue
                if len(text) > 140:
                    text = text[:137].rstrip() + "..."
                facts.append(text)
            except Exception:
                continue

        if not facts:
            return ""
        return "Context:\n" + "\n".join(f"- {f}" for f in facts[-2:])

    def _format_user_line(self, user_info: Optional[Dict[str, Any]], user_input: str) -> str:
        """Format user input line."""
        try:
            name = "User"
            if user_info:
                name = user_info.get("nickname") or user_info.get("name") or "User"
            safe = user_input.strip().replace("\n", " ").strip()
            return f"{name}: {safe}" if safe else f"{name}:"
        except Exception:
            return f"User: {user_input}"

    def _truncate_prompt(self, prompt: str) -> str:
        """Truncate prompt to max chars."""
        if len(prompt) <= self.max_chars:
            return prompt
        
        try:
            if "Context:\n" in prompt:
                before, after = prompt.split("Context:\n", 1)
                new_prompt = before + "Context:\n" + after[:80] + "..."
                if len(new_prompt) <= self.max_chars:
                    return new_prompt
                prompt = before + "(Context trimmed)"
            
            if len(prompt) > self.max_chars:
                return prompt[:self.max_chars - 20].rstrip() + "\n\nKitsu:"
        except Exception:
            pass
        
        return prompt[:self.max_chars - 20].rstrip() + "\n\nKitsu:"


# Factory functions
def create_prompt_builder(
    character_context: str,
    memory_manager: Optional[Any] = None,
    config: Optional[PromptConfig] = None,
) -> PromptBuilder:
    """Create a configured PromptBuilder instance."""
    return PromptBuilder(character_context, memory_manager, config)


def create_character_prompt_builder(
    memory_manager: Optional[Any] = None,
    max_chars: int = 900,
) -> CharacterPromptBuilder:
    """Create a configured CharacterPromptBuilder instance."""
    return CharacterPromptBuilder(memory_manager, max_chars)
