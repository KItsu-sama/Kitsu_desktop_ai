"""
app/commands/command_router.py

Changes vs previous version:
  - _cmd_rate now also calls engine.compression.online_update(rating=N)
    so the BinaryNN gets a reward signal after every /rate.
  - _cmd_train now also notifies the compression pipeline that the
    target response changed, triggering a binary feature re-evaluation.
  - /compress command with subcommands:
        /compress status        — encoder + NN stats
        /compress train         — manual offline retrain from existing data
        /compress log           — show last binary debug log
        /compress debug [on|off]— toggle binary debug log in responses
  - Everything else is unchanged from the previous version.
"""

import json
import logging
import time
from typing import Dict, Any
from pathlib import Path
from rich.console import Console
from shared.utils.logger import set_debug_output, is_debug_output_enabled

log = logging.getLogger(__name__)

COMBO_WINDOW_SECONDS = 300   # /rate + /train must happen within this window


class CommandRouter:
    def __init__(self, desktop_controller):
        """
        Initialize CommandRouter with DesktopController interface.
        
        The CommandRouter should interact with engine subsystems through
        the DesktopController's property pass-through pattern rather than
        importing the engine subsystems directly.
        """
        # Store the desktop controller as our primary interface
        self.controller = desktop_controller
        self.engine = desktop_controller.engine if hasattr(desktop_controller, "engine") else desktop_controller
        self.console = Console()

        self._micro_train_method: str = "qlora"
        self._show_binary_log: bool = False   # toggled by /compress debug on

        self.commands = {
            # System
            "/quit":         self._cmd_quit,
            "/exit":         self._cmd_quit,
            "/clear":        self._cmd_clear,
            "/reload":       self._cmd_reload,
            "/debug":        self._cmd_debug,
            # Info
            "/stats":        self._cmd_stats,
            "/state":        self._cmd_state,
            "/model":        self._cmd_model,
            "/search":       self._cmd_search,
            "/prompt":       self._cmd_prompt,
            # Personality
            "/mood":         self._cmd_mood,
            "/style":        self._cmd_style,
            "/trigger":      self._cmd_trigger,
            # User
            "/user":         self._cmd_user,
            # Training
            "/train":        self._cmd_train,
            "/rate":         self._cmd_rate,
            "/auto_train":   self._cmd_auto_train,
            "/train_method": self._cmd_train_method,
            "/train_status": self._cmd_train_status,
            "/train_clear":  self._cmd_train_clear,
            "/delete_llm":   self._cmd_delete_llm,
            # Compression
            "/compress":     self._cmd_compress,
            # Binary Features
            "/binary":       self._cmd_binary,
            # Memory Management
            "/clear_short":  self._cmd_clear_short,
            "/clear_long":   self._cmd_clear_long,
            "/auto_prompt":  self._cmd_auto_prompt,
            # Help
            "/help":         self._cmd_help,
            "/h":            self._cmd_help,
        }

    # =========================================================================
    # Router
    # =========================================================================

    async def route(self, command: str) -> Dict[str, Any]:
        """
        Enhanced router that supports command stacking.
        Examples:
        - "/compress debug on /debug on" - executes both commands
        - "/clear /prompt" - clears memory then shows prompt
        """
        parts = command.strip().split()
        if not parts:
            return {"success": False, "output": "❌ No command provided"}
        
        # Find all command boundaries (commands start with /)
        commands = []
        current_cmd = []
        
        for i, part in enumerate(parts):
            if part.startswith('/'):
                # Save previous command if exists
                if current_cmd:
                    commands.append(current_cmd)
                current_cmd = [part]
            else:
                current_cmd.append(part)
        
        # Add the last command
        if current_cmd:
            commands.append(current_cmd)
        
        # Execute all commands and collect results
        results = []
        for cmd_parts in commands:
            cmd = cmd_parts[0].lower()
            if cmd not in self.commands:
                results.append({
                    "success": False,
                    "output": f"❌ Unknown command: {cmd}\n   Type /help for available commands",
                })
                continue
            
            try:
                result = await self.commands[cmd](cmd_parts, " ".join(cmd_parts))
                results.append(result)
            except Exception as e:
                log.exception("Command error: %s", e)
                results.append({"success": False, "output": f"❌ Command failed: {e}"})
        
        # Combine results
        if not results:
            return {"success": False, "output": "❌ No valid commands found"}
        
        if len(results) == 1:
            return results[0]
        
        # Multiple commands - combine outputs
        combined_output = ""
        all_success = True
        
        for result in results:
            if result.get("output"):
                combined_output += result["output"] + "\n"
            if not result.get("success", False):
                all_success = False
        
        return {
            "success": all_success,
            "output": combined_output.strip(),
            "multiple_commands": True
        }

    # =========================================================================
    # System Commands
    # =========================================================================

    async def _cmd_quit(self, parts, full_cmd):
        return {"success": True, "output": "", "action": "quit"}

    async def _cmd_clear(self, parts, full_cmd):
        memory = self.controller.memory
        if memory and hasattr(memory, 'clear'):
            memory.clear()
            return {"success": True, "output": "💭 Memory cleared"}
        return {"success": False, "output": "❌ Memory system not available"}

    async def _cmd_reload(self, parts, full_cmd):
        llm = self.controller.llm
        if llm and hasattr(llm, 'reload_templates'):
            llm.reload_templates()
            return {"success": True, "output": "🔄 Templates reloaded"}
        return {"success": False, "output": "❌ LLM controller not available"}

    async def _cmd_debug(self, parts, full_cmd):
        if len(parts) < 2:
            status = "ON 🔵" if is_debug_output_enabled() else "OFF 🔴"
            return {"success": True, "output": f"🐛 Debug output is currently: {status}"}
        mode = parts[1].lower()
        if mode == "on":
            set_debug_output(True)
            return {"success": True, "output": "🐛 Debug output enabled 🔵"}
        elif mode == "off":
            set_debug_output(False)
            return {"success": True, "output": "🐛 Debug output disabled 🔴"}
        return {"success": False, "output": "❌ Usage: /debug [on|off]"}

    # =========================================================================
    # Info Commands
    # =========================================================================

    async def _cmd_stats(self, parts, full_cmd):
        memory = self.controller.memory
        if memory and hasattr(memory, 'get_stats'):
            stats = memory.get_stats()
            output = (
                f"\n📊 Memory Statistics:\n"
                f"  Total sessions: {stats['total_sessions']}\n"
                f"  Emotions: {stats['emotion_distribution']}\n"
                f"  Memory usage: {stats['memory_usage_bytes'] / 1024:.1f} KB"
            )
            return {"success": True, "output": output}
        return {"success": False, "output": "❌ Memory system not available"}

    async def _cmd_state(self, parts, full_cmd):
        emotion_engine = self.controller.emotion_engine
        if emotion_engine and hasattr(emotion_engine, 'get_state_dict'):
            state = emotion_engine.get_state_dict()
            output = (
                f"\n📊 Current State:\n"
                f"  Mood: {state['mood']}\n"
                f"  Style: {state['style']}\n"
                f"  Dominant emotion: {state['dominant_emotion']}\n"
                f"  Stack size: {state['stack_size']}"
            )
            return {"success": True, "output": output}
        return {"success": False, "output": "❌ Emotion engine not available"}

    async def _cmd_model(self, parts, full_cmd):
        llm = self.controller.llm
        if not llm:
            return {"success": False, "output": "❌ LLM controller not available"}
        
        if hasattr(llm, 'get_status'):
            status = llm.get_status()
            model_name = status.get("model", "unknown")
            is_character = status.get("is_character_model", False)
            temp = status.get("temperature", 0.0)
        else:
            model_name = self.engine.runtime_config.get("model", "kitsu")
            is_character = True  # Assume character model for Kitsu
            temp = 0.75
        
        output = (
            f"\n📦 Model: {model_name}\n"
            f"🎭 Type: {'CHARACTER' if is_character else 'STANDARD'}\n"
            f"🌡️ Temperature: {temp}"
        )
        return {"success": True, "output": output}

    async def _cmd_search(self, parts, full_cmd):
        if len(parts) < 2:
            return {"success": False, "output": "❌ Usage: /search <query>"}
        query = " ".join(parts[1:])
        memory = self.controller.memory
        if memory and hasattr(memory, 'search'):
            results = memory.search(query, limit=5)
            output = f"\n🔍 Search results for '{query}':\n"
            if not results:
                output += "  No results found."
                return {"success": True, "output": output}
            for i, r in enumerate(results, 1):
                output += (
                    f"  {i}. [{r.get('role','?')}] ({r.get('emotion','neutral')}, "
                    f"score: {r.get('relevance_score',0):.2f})\n"
                    f"     {r.get('text','')[:80]}...\n"
                )
            return {"success": True, "output": output}
        return {"success": False, "output": "❌ Memory system not available"}

    async def _cmd_prompt(self, parts, full_cmd):
        # Prefer compression pipeline prompt (llm_prompt on state)
        kitsu_state = getattr(self.engine, "state", None)
        if kitsu_state:
            # Try different ways to get the prompt from compression pipeline
            prompt_text = None
            state_dict = kitsu_state.to_dict()
            
            # Method 1: Direct llm_prompt attribute
            if hasattr(kitsu_state, 'llm_prompt') and kitsu_state.llm_prompt:
                prompt_text = kitsu_state.llm_prompt
            
            # Method 2: Check state dict for prompt
            elif 'llm_prompt' in state_dict:
                prompt_text = state_dict['llm_prompt']
            
            # Method 3: Try to get from compression pipeline directly
            elif hasattr(self.engine, 'compression') and self.engine.compression:
                try:
                    # Get the last generated prompt from compression
                    if hasattr(self.engine.compression, 'last_prompt'):
                        prompt_text = self.engine.compression.last_prompt
                    elif hasattr(self.engine.compression, '_last_prompt'):
                        prompt_text = self.engine.compression._last_prompt
                except Exception:
                    pass
            
            if prompt_text:
                output = (
                    "\n" + "=" * 60 + "\n📝 LAST PROMPT (compression path)\n" + "=" * 60 + "\n\n"
                    f"🎭 Mood:    {state_dict.get('mood','?')}\n"
                    f"✨ Style:   {state_dict.get('style','?')}\n"
                    f"😊 Emotion: {state_dict.get('dominant_emotion','?')}\n"
                    f"👤 Input:   {state_dict.get('user_input','N/A')}\n"
                    + "-" * 60 + "\n📄 FULL PROMPT:\n" + "-" * 60 + "\n\n"
                )
                if len(prompt_text) > 2000:
                    output += prompt_text[:2000] + f"\n\n[... truncated, full length: {len(prompt_text)} chars]"
                else:
                    output += prompt_text
                output += "\n\n" + "=" * 60 + "\n"
                return {"success": True, "output": output}

        # Fallback: legacy LLM controller prompt
        # Try multiple access patterns for different engine types
        prompt_data = None
        
        # Pattern 1: Direct llm_controller (DesktopController fallback)
        llm_ctrl = getattr(self.engine, "llm_controller", None)
        if llm_ctrl and hasattr(llm_ctrl, "get_last_prompt"):
            prompt_data = llm_ctrl.get_last_prompt()
        
        # Pattern 2: Through llm property (DesktopController)
        elif hasattr(self.engine, "llm") and hasattr(self.engine.llm, "get_last_prompt"):
            prompt_data = self.engine.llm.get_last_prompt()
        
        # Pattern 3: Try to get LLM controller through engine's internal structure
        else:
            try:
                # Check if engine has a reference to LLM controller
                engine_llm = None
                if hasattr(self.engine, '_llm_controller'):
                    engine_llm = self.engine._llm_controller
                elif hasattr(self.engine, 'llm_controller'):
                    engine_llm = self.engine.llm_controller
                
                if engine_llm and hasattr(engine_llm, 'get_last_prompt'):
                    prompt_data = engine_llm.get_last_prompt()
            except Exception:
                pass
        
        if prompt_data is None:
            return {"success": True, "output": "❌ No prompt data available. Send a message first!"}
        if not prompt_data:
            return {"success": True, "output": "❌ No prompt generated yet. Send a message first!"}
        output = (
            "\n" + "=" * 60 + "\n📝 LAST PROMPT\n" + "=" * 60 + "\n\n"
            f"🎭 Mood: {prompt_data.get('mood','?')}\n"
            f"✨ Style: {prompt_data.get('style','?')}\n"
            f"😊 Emotion: {prompt_data.get('emotion','?')}\n"
            f"👤 User: {prompt_data.get('user_input','N/A')}\n"
            + "-" * 60 + "\n📄 FULL PROMPT:\n" + "-" * 60 + "\n\n"
        )
        prompt_text = prompt_data.get("prompt", "")
        if len(prompt_text) > 2000:
            output += prompt_text[:2000] + f"\n\n[... truncated, full length: {len(prompt_text)} chars]"
        else:
            output += prompt_text
        output += "\n\n" + "=" * 60 + "\n"
        return {"success": True, "output": output}

    # =========================================================================
    # Personality Commands
    # =========================================================================

    async def _cmd_mood(self, parts, full_cmd):
        if len(parts) < 2:
            return {"success": False, "output": "❌ Usage: /mood <behave|mean|flirty|protective> [duration_in_seconds]"}
        mood = parts[1].lower()
        
        # Try to get EmotionManager from orchestrator first
        emotion_manager = None
        if hasattr(self.controller, 'engine') and hasattr(self.controller.engine, 'emotion_manager'):
            emotion_manager = self.controller.engine.emotion_manager
        elif hasattr(self.controller, 'emotion_manager'):
            emotion_manager = self.controller.emotion_manager
        
        if not emotion_manager:
            return {"success": False, "output": "❌ EmotionManager not available"}
        
        if mood == "clear":
            emotion_manager.clear_mood_override()
            return {"success": True, "output": "✨ Manual mood override cleared"}
        elif mood in ("behave", "mean", "flirty", "protective"):
            # Parse duration (default 5 minutes)
            duration = 300.0  # 5 minutes default
            if len(parts) > 2:
                try:
                    duration = float(parts[2])
                except ValueError:
                    return {"success": False, "output": "❌ Invalid duration. Use number of seconds."}
            
            emotion_manager.set_mood(mood, duration=duration)
            duration_min = duration / 60
            return {"success": True, "output": f"✨ Mood set to: {mood} (for {duration_min:.1f} minutes)"}
        
        return {"success": False, "output": "❌ Invalid mood. Use: behave, mean, flirty, or protective"}

    async def _cmd_style(self, parts, full_cmd):
        if len(parts) < 2:
            from shared.personality_config import VALID_STYLES
            return {"success": False, "output": f"❌ Usage: /style <{', '.join(sorted(VALID_STYLES))}> [duration_in_seconds]"}
        style = parts[1].lower()
        from shared.personality_config import validate_style
        
        # Try to get EmotionManager from orchestrator first
        emotion_manager = None
        if hasattr(self.controller, 'engine') and hasattr(self.controller.engine, 'emotion_manager'):
            emotion_manager = self.controller.engine.emotion_manager
        elif hasattr(self.controller, 'emotion_manager'):
            emotion_manager = self.controller.emotion_manager
        
        if not emotion_manager:
            return {"success": False, "output": "❌ EmotionManager not available"}
        
        if validate_style(style):
            # Parse duration (optional for style)
            duration = None
            if len(parts) > 2:
                try:
                    duration = float(parts[2])
                except ValueError:
                    return {"success": False, "output": "❌ Invalid duration. Use number of seconds."}
            
            emotion_manager.set_style(style, duration=duration)
            if duration:
                duration_min = duration / 60
                return {"success": True, "output": f"✨ Style set to: {style} (for {duration_min:.1f} minutes)"}
            else:
                return {"success": True, "output": f"✨ Style set to: {style}"}
        
        from shared.personality_config import VALID_STYLES
        return {"success": False, "output": f"❌ Invalid style. Valid: {', '.join(sorted(VALID_STYLES))}"}

    async def _cmd_trigger(self, parts, full_cmd):
        if len(parts) < 2:
            return {"success": False, "output": "❌ Usage: /trigger <name>"}
        trigger_name = parts[1]
        emotion_engine = self.controller.emotion_engine
        if not emotion_engine:
            return {"success": False, "output": "❌ Emotion engine not available"}
        
        try:
            if hasattr(emotion_engine, 'fire_trigger'):
                emotion_engine.fire_trigger(trigger_name)
            if hasattr(emotion_engine, 'tick'):
                await emotion_engine.tick()
            if hasattr(emotion_engine, 'get_state_dict'):
                state = emotion_engine.get_state_dict()
                return {
                    "success": True,
                    "output": (
                        f"🔥 Fired trigger: {trigger_name}\n"
                        f"State: {state['mood']}/{state['style']} ({state['dominant_emotion']})"
                    ),
                }
        except Exception as e:
            return {"success": False, "output": f"❌ Trigger failed: {e}"}
        return {"success": False, "output": "❌ Trigger methods not available"}

    # =========================================================================
    # User Commands
    # =========================================================================

    async def _cmd_user(self, parts, full_cmd):
        memory = self.controller.memory
        if not memory:
            return {"success": False, "output": "❌ Memory system not available"}
        
        if len(parts) == 1:
            if hasattr(memory, 'get_user_info'):
                info = memory.get_user_info()
                output = (
                    f"\n📊 User Info:\n"
                    f"  Name: {info.get('name','Unknown')}\n"
                    f"  Nickname: {info.get('nickname','Unknown')}\n"
                    f"  Title: {info.get('refer_title','Unknown')}\n"
                    f"  Status: {info.get('status','Unknown')}"
                )
                return {"success": True, "output": output}
            return {"success": False, "output": "❌ User info not available"}
        
        sub = parts[1].lower()
        if sub == "set":
            if len(parts) < 4:
                return {"success": False, "output": "❌ Usage: /user set <field> <value>"}
            field = parts[2].lower()
            value = " ".join(parts[3:]).strip("'\"")
            try:
                if hasattr(memory, 'set_user_info'):
                    memory.set_user_info(**{field: value})
                if hasattr(memory, 'save_user'):
                    memory.save_user()
                return {"success": True, "output": f"✅ Updated {field} → {value}"}
            except Exception as e:
                return {"success": False, "output": f"❌ Failed to update: {e}"}
        return {"success": False, "output": f"❌ Unknown /user subcommand: {sub}"}

    # =========================================================================
    # Training Commands
    # =========================================================================

    async def _cmd_rate(self, parts, full_cmd):
        """
        Rate last response (m=normal, g=good, b=bad).

        Routes rating to:
          1. DesktopController.rate_last_response() (handles memory + compression)
          2. training_system  (LoRA training data)
          3. auto-train combo check
        """
        if len(parts) < 2:
            return {"success": False, "output": "❌ Usage: /rate <m|g|b> [comment]"}

        rating_code = parts[1].lower()
        comment = " ".join(parts[2:]) if len(parts) > 2 else ""
        rating_map  = {"m": 3, "g": 5, "b": 1, "1": 1, "2": 2, "3": 3, "4": 4, "5": 5}
        rating_names = {"m": "normal", "g": "good", "b": "bad"}

        if rating_code not in rating_map:
            return {"success": False, "output": "❌ Invalid rating. Use: m (normal), g (good), b (bad)"}

        numeric_rating = rating_map[rating_code]
        rating_name    = rating_names.get(rating_code, str(numeric_rating))

        try:
            # 1. Use DesktopController's rate method (handles memory + compression)
            if hasattr(self.controller, 'rate_last_response'):
                rate_result = self.controller.rate_last_response(numeric_rating)
            else:
                # Fallback: direct memory rating
                response_history = self.controller.response_history
                if response_history:
                    result = response_history.rate_response(
                        response_id=None,
                        rating=numeric_rating,
                        rater="user",
                        comment=comment,
                    )
                    if not result.get("ok"):
                        return {"success": False, "output": f"❌ {result.get('reason','Rating failed')}"}

            # 2. training_system (if available)
            training_system = getattr(self.controller, 'training_system', None)
            if training_system:
                ts = training_system
                
                # Handle both RealTimeTrainingSystem and PersonalityTrainer
                if hasattr(ts, 'training_examples') and ts.training_examples:
                    # RealTimeTrainingSystem case
                    last = ts.training_examples[-1]
                    last.reward_score = numeric_rating
                    ts._last_rating = {"rating": numeric_rating, "timestamp": time.time()}
                    normalized = (numeric_rating - 3) / 2
                    ts.reward_history.append({
                        "timestamp": __import__("datetime").datetime.now().isoformat(),
                        "reward": normalized,
                        "action_tokens": getattr(last, 'action_tokens', ''),
                        "auto_corrected": False,
                    })
                    if hasattr(ts, '_save_training_data'):
                        ts._save_training_data()
                elif hasattr(ts, 'rate_response'):
                    # PersonalityTrainer case
                    ts.rate_response(numeric_rating)

            output = f"✅ Rated as {rating_name} ({numeric_rating}/5)."
            if comment:
                output += f" Comment: {comment}"

            # 3. Auto-train combo check
            trigger_msg = await self._check_and_trigger_micro_train()
            if trigger_msg:
                output += f"\n{trigger_msg}"

            return {"success": True, "output": output}

        except Exception as e:
            log.exception("Rating command failed: %s", e)
            return {"success": False, "output": f"❌ Rating failed: {e}"}

    async def _cmd_train(self, parts, full_cmd):
        """
        Provide the correct response for the last turn.

        Routes correction to:
          1. training_system  (LoRA training data)
          2. compression pipeline — marks the binary features for this
             interaction as positive so online_update can reinforce them
          3. auto-train combo check
        """
        log.debug("Train command received: %s", full_cmd)
        if len(parts) < 2:
            return {"success": False, "output": '❌ Usage: /train <"correct response">'}

        response_text = " ".join(parts[1:]).strip("'\"")
        log.debug("Training response text: %s", response_text[:50])

        try:
            if not hasattr(self.engine, "training_system") or not self.engine.training_system:
                log.debug("Training system not available")
                return {"success": False, "output": "❌ Training system not available"}

            ts = self.engine.training_system
            
            # Handle both RealTimeTrainingSystem and PersonalityTrainer
            if hasattr(ts, 'training_examples') and ts.training_examples:
                # RealTimeTrainingSystem case
                last = ts.training_examples[-1]
                log.debug("Last training example: %s", last.input_text[:50])
                last.target_text = response_text
                last.reward_score = 1.0
                ts._last_correction = {"timestamp": time.time(), "response": response_text}
                ts.reward_history.append({
                    "timestamp": __import__("datetime").datetime.now().isoformat(),
                    "reward": 1.0,
                    "action_tokens": getattr(last, 'action_tokens', ''),
                    "auto_corrected": True,
                })
                if hasattr(ts, '_save_training_data'):
                    ts._save_training_data()
            elif hasattr(ts, 'correct_response'):
                # PersonalityTrainer case
                ts.correct_response(response_text)
            else:
                # Unknown training system type
                log.warning(f"Unknown training system type: {type(ts).__name__}")
                return {"success": False, "output": "❌ Training system not compatible"}

            # Update memory
            try:
                if hasattr(self.engine.memory, "sessions") and self.engine.memory.sessions:
                    for i in range(len(self.engine.memory.sessions) - 1, -1, -1):
                        s = self.engine.memory.sessions[i]
                        if s.get("role") == "kitsu":
                            s["text"] = response_text
                            s["score"] = 1.0
                            break
            except Exception as e:
                log.warning("Failed to update memory: %s", e)

            # Handle different training system save methods
            if hasattr(ts, '_save_training_data'):
                ts._save_training_data()
            elif hasattr(ts, 'load_state_training_data'):
                ts.load_state_training_data()
            elif hasattr(ts, 'save'):
                ts.save()

            # 2. Compression correction — full reward signal (rating 5)
            compress_note = await self._compression_rate(5, correction=response_text)

            output = f"✅ Response corrected: {response_text[:100]}{'...' if len(response_text) > 100 else ''}"
            if compress_note:
                output += f"\n{compress_note}"

            # 3. Auto-train combo check
            try:
                trigger_msg = await self._check_and_trigger_micro_train()
            except Exception as e:
                log.error("Micro-train check failed: %s", e, exc_info=True)
                trigger_msg = f"⚠️ Micro-train check failed: {e}"

            if trigger_msg:
                output += f"\n{trigger_msg}"

            return {"success": True, "output": output}

        except Exception as e:
            log.exception("Train command failed: %s", e)
            return {"success": False, "output": f"❌ Training failed: {e}"}

    # =========================================================================
    # Compression helper — called by /rate and /train
    # =========================================================================

    async def _compression_rate(
        self,
        rating: int,
        correction: str = None,
    ) -> str:
        """
        Forward a rating (and optional corrected response) to the compression
        pipeline's online_update().

        Returns a short status note to append to the command output,
        or "" if compression is not available.
        """
        compression = getattr(self.engine, "compression", None)
        if compression is None or not getattr(self.engine, "_compression_ready", False):
            return ""

        try:
            # Gather last interaction context from engine state
            kitsu_state = getattr(self.engine, "state", None)
            user_input = ""
            state_dict = None
            binary_features = None

            if kitsu_state:
                user_input    = kitsu_state.user_input or ""
                state_dict    = kitsu_state.to_dict()
                binary_features = dict(kitsu_state.binary_features)

            rebuilt = compression.online_update(
                text=user_input,
                state_dict=state_dict,
                binary_features=binary_features,
                rating=rating,
            )

            note = f"🔢 Compression updated (rating={rating}/5)"
            if rebuilt:
                note += " — encoder rebuilt"
                self.engine._compression_ready = compression.encoder._is_built
            return note

        except Exception as e:
            log.debug(f"Compression rate update failed (non-critical): {e}")
            return ""
    # =========================================================================
    # /compress command
    # =========================================================================
    async def _cmd_compress(self, parts, full_cmd):
        """
        /compress clear        — clear all compression data and reset
        /compress status       — show encoder + NN stats
        /compress train        — manual offline retrain from existing data
        /compress log          — show last binary debug log
        /compress debug [on|off]  — toggle binary debug log in conversation
        """
        sub = parts[1].lower() if len(parts) > 1 else "status"
        compression = getattr(self.engine, "compression", None)
        ready = getattr(self.engine, "_compression_ready", False)

        if sub == "status":
            if compression is None:
                return {"success": True, "output": "🔢 Compression pipeline: not initialised"}

            stats = compression.get_stats()
            enc = stats.get("encoder", {})
            nn  = stats.get("nn", {})
            output = (
                "\n" + "=" * 60 + "\n🔢 COMPRESSION PIPELINE STATUS\n" + "=" * 60 + "\n\n"
                f"Ready:              {'yes' if ready else 'no (needs offline_train)'}\n"
                f"Encoder built:      {enc.get('is_built', False)}\n"
                f"Vocab size:         {enc.get('vocab_size', 0)}\n"
                f"Symbols seen:       {enc.get('total_symbols_seen', 0)}\n"
                f"Sequences seen:     {enc.get('total_sequences_seen', 0)}\n"
                f"Markov contexts:    {enc.get('markov_contexts', 0)}\n"
                f"Avg code length:    {enc.get('avg_code_length', 0):.2f} bits\n"
                f"Updates since rebuild: {enc.get('updates_since_rebuild', 0)}/{enc.get('online_threshold', 100)}\n\n"
                f"NN trained:         {nn.get('is_trained', False)}\n"
                f"NN input dim:       {nn.get('input_dim', 0)}\n"
                f"NN output dim:      {nn.get('output_dim', 0)}\n"
                f"NN has EWC:         {nn.get('has_ewc', False)}\n"
                f"Binary debug log:   {'on' if self._show_binary_log else 'off'}\n"
                "\n" + "=" * 60 + "\n"
            )
            return {"success": True, "output": output}

        elif sub == "clear":
            if compression is None:
                return {"success": False, "output": "❌ Compression pipeline not initialised"}
            try:
                compression.clear()
                self.engine._compression_ready = False
                return {"success": True, "output": "✅ Compression data cleared and reset."}
            except Exception as e:
                return {"success": True, "output": f"❌ Clear failed: {e}"}

        elif sub == "train":
            if compression is None:
                return {"success": False, "output": "❌ Compression pipeline not initialised"}
            output = "🔢 Running offline retrain from existing data...\n"
            try:
                report = self.engine.train_compression_offline()
                enc = report.get("encoder_stats", {})
                output += (
                    f"✅ Done.\n"
                    f"  Vocab size: {enc.get('vocab_size', '?')}\n"
                    f"  Symbols seen: {enc.get('total_symbols_seen', '?')}\n"
                    f"  Avg code length: {enc.get('avg_code_length', 0):.2f} bits\n"
                )
                losses = report.get("nn_losses", [])
                if losses:
                    output += f"  NN final loss: {losses[-1]:.4f}\n"
            except Exception as e:
                output += f"❌ Retrain failed: {e}"
            return {"success": True, "output": output}

        elif sub == "log":
            # Show last binary debug log from engine state
            kitsu_state = getattr(self.engine, "state", None)
            last_response = getattr(self.engine, "_last_debug_log", None)

            # Also try desktop_controller if available
            if last_response is None:
                controller = getattr(self.engine, "_controller", None)
                if controller:
                    last_resp = getattr(controller, "_last_response", None)
                    if last_resp:
                        last_response = last_resp.get("debug_log")

            if not last_response:
                return {
                    "success": True,
                    "output": "❌ No binary debug log available. Send a message first.",
                }
            return {"success": True, "output": f"\n{last_response}"}

        elif sub == "debug":
            mode = parts[2].lower() if len(parts) > 2 else None
            if mode == "on":
                self._show_binary_log = True
                # Also enable on engine config if possible
                try:
                    self.engine.runtime_config["debug_mode"] = True
                except Exception:
                    pass
                return {"success": True, "output": "🔢 Binary debug log: ON — shown after each response"}
            elif mode == "off":
                self._show_binary_log = False
                try:
                    self.engine.runtime_config["debug_mode"] = False
                except Exception:
                    pass
                return {"success": True, "output": "🔢 Binary debug log: OFF"}
            else:
                status = "ON" if self._show_binary_log else "OFF"
                return {
                    "success": True,
                    "output": (
                        f"🔢 Binary debug log: {status}\n"
                        f"   Usage: /compress debug [on|off]"
                    ),
                }

        elif sub == "seed":
            try:
                from data.training_corpus import TRAINING_PAIRS, TRAINING_STATS
                report = self.engine.bootstrap_from_training_pairs(TRAINING_PAIRS)
                vocab  = report.get("encoder_stats", {}).get("vocab_size", "?")
                ctxs   = report.get("encoder_stats", {}).get("markov_contexts", "?")
                # Reset the seeded flag so launcher knows it's done
                Path("data/runtime/.compression_seeded").touch()
                return {
                    "success": True,
                    "output": (
                        f"✅ Compression seeded from {TRAINING_STATS['total_pairs']} pairs\n"
                        f"  Categories: {len(TRAINING_STATS['categories'])}\n"
                        f"  Vocab: {vocab} tokens\n"
                        f"  Markov contexts: {ctxs}\n"
                        f"  Run /compress status to verify"
                    ),
                }
            except Exception as e:
                return {"success": False, "output": f"❌ Seed failed: {e}"}

        else:
            return {
                "success": False,
                "output": (
                    "❌ Unknown /compress subcommand.\n"
                    "   Usage: /compress [status|train|clear|log|debug|seed]"
                ),
            }

    # =========================================================================
    # /binary command
    # =========================================================================

    async def _cmd_binary(self, parts, full_cmd):
        """
        /binary show                    — show current binary features
        /binary set <feature> <0|1>     — set a binary feature (0 or 1)
        /binary reset                   — reset all binary features to 0
        /binary list                    — list all available binary features
        /binary load <preset>           — load a preset binary feature configuration
        """
        sub = parts[1].lower() if len(parts) > 1 else "show"
        
        # Get the binary reasoner from engine
        binary_reasoner = getattr(self.engine, "reasoner", None)
        if not binary_reasoner:
            return {"success": False, "output": "❌ Binary reasoner not available"}

        if sub == "show":
            # Get current binary features from engine state
            current_features = getattr(self.engine.state, "binary_features", {})
            if not current_features:
                return {"success": True, "output": "🔢 No binary features currently set"}
            
            output = "\n" + "=" * 50 + "\n🔢 CURRENT BINARY FEATURES\n" + "=" * 50 + "\n\n"
            active_features = [k for k, v in current_features.items() if v == 1]
            inactive_features = [k for k, v in current_features.items() if v == 0]
            
            if active_features:
                output += "🟢 ACTIVE (1):\n"
                for feature in active_features:
                    output += f"  • {feature}\n"
                output += "\n"
            
            if inactive_features:
                output += "🔴 INACTIVE (0):\n"
                for feature in inactive_features[:10]:  # Show first 10 inactive
                    output += f"  • {feature}\n"
                if len(inactive_features) > 10:
                    output += f"  ... and {len(inactive_features) - 10} more\n"
            
            output += "\n" + "=" * 50 + "\n"
            return {"success": True, "output": output}

        elif sub == "set":
            if len(parts) < 4:
                return {
                    "success": False,
                    "output": "❌ Usage: /binary set <feature> <0|1>\n   Example: /binary set should_be_playful 1"
                }
            
            feature_name = parts[2]
            value = parts[3]
            
            if value not in ["0", "1"]:
                return {"success": False, "output": "❌ Value must be 0 or 1"}
            
            # Validate feature name against known features
            known_features = self._get_known_binary_features()
            if feature_name not in known_features:
                return {
                    "success": False,
                    "output": f"❌ Unknown feature: {feature_name}\n   Use /binary list to see available features"
                }
            
            # Set the feature in engine state
            if not hasattr(self.engine.state, "binary_features"):
                self.engine.state.binary_features = {}
            
            self.engine.state.binary_features[feature_name] = int(value)
            
            # ADD: mark as manually locked so reasoner skips it
            if not hasattr(self.engine.state, "_locked_features"):
                self.engine.state._locked_features = set()
            
            if value == "1":
                self.engine.state._locked_features.add(feature_name)
            elif feature_name in getattr(self.engine.state, "_locked_features", set()):
                self.engine.state._locked_features.discard(feature_name)
            
            status = "🟢 ACTIVATED" if value == "1" else "🔴 DEACTIVATED"
            return {"success": True, "output": f"✅ Feature '{feature_name}' {status}"}

        elif sub == "reset":
            # Reset all binary features to 0
            if hasattr(self.engine.state, "binary_features"):
                for feature in self.engine.state.binary_features:
                    self.engine.state.binary_features[feature] = 0
            # Clear locked features
            if hasattr(self.engine.state, "_locked_features"):
                self.engine.state._locked_features.clear()
            return {"success": True, "output": "✅ All binary features reset to 0"}

        elif sub == "list":
            # List all available binary features
            known_features = self._get_known_binary_features()
            current_features = getattr(self.engine.state, "binary_features", {})
            
            output = "\n" + "=" * 60 + "\n🔢 AVAILABLE BINARY FEATURES\n" + "=" * 60 + "\n\n"
            
            for feature in known_features:
                current_value = current_features.get(feature, 0)
                status = "🟢" if current_value == 1 else "🔴"
                output += f"{status} {feature} = {current_value}\n"
            
            output += "\n" + "=" * 60 + "\n"
            output += "💡 Use /binary set <feature> <0|1> to modify features\n"
            return {"success": True, "output": output}

        elif sub == "load":
            if len(parts) < 3:
                return {
                    "success": False,
                    "output": "❌ Usage: /binary load <preset>\n   Available presets: playful, caring, direct, analytical"
                }
            
            preset_name = parts[2].lower()
            presets = self._get_binary_presets()
            
            if preset_name not in presets:
                available = ", ".join(presets.keys())
                return {
                    "success": False,
                    "output": f"❌ Unknown preset: {preset_name}\n   Available: {available}"
                }
            
            # Load preset
            preset_features = presets[preset_name]
            if not hasattr(self.engine.state, "binary_features"):
                self.engine.state.binary_features = {}
            
            for feature, value in preset_features.items():
                self.engine.state.binary_features[feature] = value
            
            return {"success": True, "output": f"✅ Loaded preset '{preset_name}'"}

        else:
            return {
                "success": False,
                "output": (
                    "❌ Unknown /binary subcommand.\n"
                    "   Usage: /binary [show|set|reset|list|load]"
                ),
            }

    def _get_known_binary_features(self):
        """Get list of known binary features"""
        return [
            "needs_search", "user_is_questioning", "user_requests_help", "user_expresses_emotion",
            "user_is_frustrated", "memory_relevant", "emotional_support_needed", 
            "technical_answer_required", "creative_response_needed", "should_be_playful",
            "should_be_caring", "should_be_teasing", "should_be_direct", "use_memory",
            "ask_followup", "provide_examples", "keep_brief", "needs_safety_check",
            "is_sensitive_topic", "emotionally_charged", "high_resistance", 
            "emotion_stack_deep", "kitsu_is_hidden", "mood_unstable", 
            "should_use_fox_quirk", "style_allows_emojis", "response_length_constrained",
            "wants_to_tease", "wants_to_confuse", "wants_to_analyze", 
            "wants_to_soften", "wants_to_glitch", "wants_to_dominate"
        ]

    def _get_binary_presets(self):
        """Get predefined binary feature presets"""
        return {
            "playful": {
                "should_be_playful": 1,
                "should_use_fox_quirk": 1,
                "style_allows_emojis": 1,
                "creative_response_needed": 1,
                "keep_brief": 0,
                "should_be_direct": 0,
                "emotional_support_needed": 0,
                "technical_answer_required": 0
            },
            "caring": {
                "should_be_caring": 1,
                "emotional_support_needed": 1,
                "user_expresses_emotion": 1,
                "should_be_playful": 0,
                "should_be_teasing": 0,
                "keep_brief": 0,
                "technical_answer_required": 0,
                "creative_response_needed": 0
            },
            "direct": {
                "should_be_direct": 1,
                "keep_brief": 1,
                "response_length_constrained": 1,
                "should_be_playful": 0,
                "should_use_fox_quirk": 0,
                "style_allows_emojis": 0,
                "should_be_teasing": 0,
                "creative_response_needed": 0
            },
            "analytical": {
                "technical_answer_required": 1,
                "needs_search": 1,
                "provide_examples": 1,
                "should_be_direct": 1,
                "keep_brief": 0,
                "should_be_playful": 0,
                "should_use_fox_quirk": 0,
                "creative_response_needed": 0
            }
        }

    # =========================================================================
    # Auto-train combo checker (unchanged logic)
    # =========================================================================

    async def _check_and_trigger_micro_train(self) -> str:
        log.debug("Checking micro-train combo...")
        if not hasattr(self.engine, "training_system") or not self.engine.training_system:
            return ""

        ts = self.engine.training_system
        if not ts.auto_train_enabled:
            return ""

        last_rating     = getattr(ts, "_last_rating",     None)
        last_correction = getattr(ts, "_last_correction", None)

        if last_rating is None or last_correction is None:
            return ""

        now = time.time()
        if (
            now - last_rating.get("timestamp", 0)     > COMBO_WINDOW_SECONDS
            or now - last_correction.get("timestamp", 0) > COMBO_WINDOW_SECONDS
        ):
            return ""

        if ts.training_examples:
            last_ex = ts.training_examples[-1]
            try:
                import datetime as _dt
                ex_ts = _dt.datetime.fromisoformat(last_ex.timestamp).timestamp()
            except Exception:
                ex_ts = 0.0
            if (
                last_rating["timestamp"] < ex_ts
                or last_correction["timestamp"] < ex_ts
            ):
                return ""

        ts._last_rating     = None
        ts._last_correction = None
        return await self._trigger_micro_train_now(ts)

    async def _trigger_micro_train_now(self, ts) -> str:
        try:
            from runtime.learning.micro_trainer import MicroTrainer, MicroTrainRequest, MicroTrainConfig
        except Exception as e:
            log.error("MicroTrainer import failed: %s", e, exc_info=True)
            return f"⚠️ Micro-train unavailable (import error): {e}"

        if not ts.training_examples:
            return "⚠️ No training examples available for micro-train."

        try:
            last_ex = ts.training_examples[-1]
            original_resp = (
                last_ex.rejected_text
                if getattr(last_ex, "rejected_text", None)
                else getattr(last_ex, "_original_response", None)
            )

            req = MicroTrainRequest(
                user_input=last_ex.input_text,
                chosen_response=last_ex.target_text,
                rejected_response=original_resp,
                mood=last_ex.mood,
                style=last_ex.style,
                emotion=last_ex.emotion,
                rating=int(last_ex.reward_score or 5),
            )

            model_path = self._find_active_adapter()
            from pathlib import Path as _Path
            save_dir = model_path if _Path(model_path).is_dir() else None

            cfg = MicroTrainConfig(
                method=self._micro_train_method,
                output_base=_Path("data/lora"),
                device="cpu",
                num_epochs=1,
                use_qlora=True,
                save_dir=save_dir,
            )

            trainer = MicroTrainer(model_path=model_path, config=cfg)
            log.info(
                "🔥 Auto-train triggered: method=%s model=%s mood=%s style=%s",
                self._micro_train_method, model_path, req.mood, req.style,
            )

            result = await trainer.train_async(req)

            if result.success:
                qlora_tag = "+QLoRA" if cfg.effective_use_qlora() else ""
                adapter_info = f" → {result.adapter_path}" if result.adapter_path else ""
                metrics_str = ""
                if result.metrics:
                    if "loss" in result.metrics:
                        metrics_str = f" (loss: {result.metrics['loss']:.4f})"
                    elif "catboost_fit" in result.metrics:
                        metrics_str = f" (reward model updated: {result.metrics['catboost_fit']})"
                return (
                    f"🤖 Micro-train [{self._micro_train_method.upper()}{qlora_tag}] "
                    f"completed in {result.duration_seconds:.1f}s{metrics_str}{adapter_info}"
                )
            else:
                return f"⚠️ Micro-train [{self._micro_train_method.upper()}] failed: {result.error}"
        except Exception as e:
            log.error("_trigger_micro_train_now failed: %s", e, exc_info=True)
            return f"⚠️ Micro-train failed: {e}"

    def _find_active_adapter(self) -> str:
        def _is_valid(p) -> bool:
            if not p.is_dir():
                return False
            if (p / "adapter_config.json").exists():
                return True
            cfg = p / "config.json"
            if cfg.exists():
                try:
                    return "model_type" in json.loads(cfg.read_text(encoding="utf-8"))
                except Exception:
                    return False
            return False

        integration = getattr(self.engine, "lora_integration", None)
        if integration:
            try:
                info  = integration.adapter.get_model_info()
                stack = info.get("active_stack", []) or []
                if stack:
                    last = stack[-1].replace(":", "_")
                    p = Path("data/lora") / last
                    if _is_valid(p):
                        return str(p)
            except Exception:
                pass

        for candidate in [
            Path("data/lora/kitsu_character_micro"),
            Path("data/lora/kitsu_character"),
        ]:
            if _is_valid(candidate):
                return str(candidate)

        return "TinyLlama/TinyLlama-1.1B-Chat-v1.0"

    # =========================================================================
    # Auto-train toggle
    # =========================================================================

    async def _cmd_auto_train(self, parts, full_cmd):
        VALID_METHODS = {"qlora", "lora", "dora", "dpo", "rlhf", "prefix", "catboost", "panda"}

        if len(parts) < 2:
            if hasattr(self.engine, "training_system") and self.engine.training_system:
                status = "enabled" if self.engine.training_system.auto_train_enabled else "disabled"
                return {
                    "success": True,
                    "output": (
                        f"🤖 Auto-training: {status}  |  method: {self._micro_train_method}\n"
                        f"   Methods: {', '.join(sorted(VALID_METHODS))}\n"
                        f"   Usage:  /auto_train [on|off] [method]"
                    ),
                }
            return {"success": False, "output": "❌ Training system not available"}

        mode = parts[1].lower()
        if mode not in ("on", "off", "true", "false"):
            return {"success": False, "output": "❌ Usage: /auto_train [on|off] [method]"}

        enable = mode in ("on", "true")

        if len(parts) >= 3:
            method = parts[2].lower()
            if method not in VALID_METHODS:
                return {
                    "success": False,
                    "output": f"❌ Unknown method '{method}'. Valid: {', '.join(sorted(VALID_METHODS))}",
                }
            self._micro_train_method = method

        try:
            if hasattr(self.engine, "training_system") and self.engine.training_system:
                old = "enabled" if self.engine.training_system.auto_train_enabled else "disabled"
                self.engine.training_system.auto_train_enabled = enable
                new = "enabled" if enable else "disabled"
                return {
                    "success": True,
                    "output": f"🤖 Auto-training {old} → {new}  |  method: {self._micro_train_method}",
                }
            return {"success": False, "output": "❌ Training system not available"}
        except Exception as e:
            log.exception("Auto-train toggle failed: %s", e)
            return {"success": False, "output": f"❌ Auto-train failed: {e}"}

    async def _cmd_train_method(self, parts, full_cmd):
        VALID_METHODS = {"qlora", "lora", "dora", "dpo", "rlhf", "prefix", "catboost", "panda"}
        if len(parts) < 2:
            return {
                "success": True,
                "output": (
                    f"Current method: {self._micro_train_method}\n"
                    f"Valid methods:  {', '.join(sorted(VALID_METHODS))}\n"
                    f"Usage: /train_method <method>"
                ),
            }
        method = parts[1].lower()
        if method not in VALID_METHODS:
            return {
                "success": False,
                "output": f"❌ Unknown method '{method}'. Valid: {', '.join(sorted(VALID_METHODS))}",
            }
        old = self._micro_train_method
        self._micro_train_method = method
        return {"success": True, "output": f"✅ Micro-train method: {old} → {method}"}

    # =========================================================================
    # Remaining training commands
    # =========================================================================

    async def _cmd_train_status(self, parts, full_cmd):
        if not hasattr(self.engine, "training_system") or not self.engine.training_system:
            return {"success": False, "output": "❌ Training system not available"}
        ts = self.engine.training_system
        output = "\n" + "=" * 60 + "\n🤖 TRAINING SYSTEM STATUS\n" + "=" * 60 + "\n\n"
        output += f"📊 Auto-training: {'enabled' if ts.auto_train_enabled else 'disabled'}\n"
        output += f"🔧 Active method: {self._micro_train_method}\n"
        output += f"📝 Training examples: {len(ts.training_examples)}\n"
        output += f"🏆 Reward history: {len(ts.reward_history)}\n\n"

        last_rating = getattr(ts, "_last_rating", None)
        if last_rating:
            age = int((time.time() - last_rating.get("timestamp", 0)) / 60)
            output += f"⭐ Last rating: {last_rating.get('rating','?')}/5 ({age} min ago)\n"
        else:
            output += "⭐ Last rating: None\n"

        last_corr = getattr(ts, "_last_correction", None)
        if last_corr:
            age  = int((time.time() - last_corr.get("timestamp", 0)) / 60)
            text = last_corr.get("response", "")[:50]
            output += f"✏️ Last correction: '{text}...' ({age} min ago)\n\n"
        else:
            output += "✏️ Last correction: None\n\n"

        if ts.training_examples:
            output += "📋 RECENT TRAINING EXAMPLES:\n" + "-" * 60 + "\n"
            for i, ex in enumerate(ts.training_examples[-3:], 1):
                output += (
                    f"\n{i}. User: {ex.input_text[:50]}{'...' if len(ex.input_text)>50 else ''}\n"
                    f"   Kitsu: {ex.target_text[:50]}{'...' if len(ex.target_text)>50 else ''}\n"
                    f"   Mood: {ex.mood}/{ex.style} | Emotion: {ex.emotion}\n"
                    f"   Reward: {ex.reward_score or 'N/A'}\n"
                )
        output += "\n" + "=" * 60 + "\n"
        return {"success": True, "output": output}

    async def _cmd_train_clear(self, parts, full_cmd):
        if not hasattr(self.engine, "training_system") or not self.engine.training_system:
            return {"success": False, "output": "❌ Training system not available"}
        result = self.engine.training_system.clear_training_data()
        return {"success": True, "output": f"✅ {result}"}

    async def _cmd_delete_llm(self, parts, full_cmd):
        from llm.lora_registry import LoRARegistry
        from io_layer.llm.config_writer import ConfigWriter

        cfg_path = Path("data/config.json")
        try:
            cfg = json.loads(cfg_path.read_text()) if cfg_path.exists() else {}
        except Exception:
            cfg = {}

        model_cfg = cfg.get("model")
        if not model_cfg:
            return {"success": False, "output": "No model configured in data/config.json"}
        stack = (
            model_cfg.get("stack", []) if isinstance(model_cfg, dict)
            else model_cfg if isinstance(model_cfg, list)
            else []
        )
        if not stack:
            return {"success": False, "output": "No adapters in current stack"}

        target     = stack[-1]
        normalized = target.replace(":", "_")
        registry   = LoRARegistry(adapters_dir=Path("data/lora"))
        registry.discover()
        adapter = registry.get(target) or registry.get(normalized)
        if not adapter:
            return {"success": False, "output": f"Adapter '{target}' not found"}
        if adapter.type == "base":
            return {"success": False, "output": f"'{adapter.name}' is a base adapter; use script with --force"}
        try:
            import shutil
            if adapter.path.exists():
                shutil.rmtree(adapter.path)
            new_stack = [s for s in stack if s not in (adapter.name, normalized)]
            writer = ConfigWriter(config_path=cfg_path)
            writer.write_lora_stack(new_stack)
            return {"success": True, "output": f"Deleted {adapter.name}, new stack: {new_stack}"}
        except Exception as e:
            return {"success": False, "output": f"Deletion failed: {e}"}

    # =========================================================================
    # Memory Management Commands
    # =========================================================================

    async def _cmd_clear_short(self, parts, full_cmd):
        """Clear short-term memory (current session)"""
        try:
            if hasattr(self.engine.memory, 'clear_short_term'):
                self.engine.memory.clear_short_term()
                return {"success": True, "output": "🧹 Short-term memory cleared"}
            else:
                # Fallback: clear recent items only
                if hasattr(self.engine.memory, 'memory'):
                    # Keep only long-term memories, remove recent session data
                    long_term = [m for m in self.engine.memory.memory if m.get('type') == 'long_term']
                    self.engine.memory.memory = long_term
                    return {"success": True, "output": "🧹 Short-term memory cleared"}
                else:
                    return {"success": False, "output": "❌ Memory system doesn't support short-term clearing"}
        except Exception as e:
            return {"success": False, "output": f"❌ Failed to clear short-term memory: {e}"}

    async def _cmd_clear_long(self, parts, full_cmd):
        """Clear long-term memory (persistent data)"""
        try:
            if hasattr(self.engine.memory, 'clear_long_term'):
                self.engine.memory.clear_long_term()
                return {"success": True, "output": "🗑️ Long-term memory cleared"}
            else:
                # Fallback: clear only long-term items
                if hasattr(self.engine.memory, 'memory'):
                    # Keep only short-term memories, remove persistent data
                    short_term = [m for m in self.engine.memory.memory if m.get('type') != 'long_term']
                    self.engine.memory.memory = short_term
                    return {"success": True, "output": "🗑️ Long-term memory cleared"}
                else:
                    return {"success": False, "output": "❌ Memory system doesn't support long-term clearing"}
        except Exception as e:
            return {"success": False, "output": f"❌ Failed to clear long-term memory: {e}"}

    async def _cmd_auto_prompt(self, parts, full_cmd):
        """Toggle automatic prompt display after each response"""
        if len(parts) < 2:
            # Show current status
            status = "ON 🔵" if getattr(self.desktop_controller, '_auto_prompt_enabled', False) else "OFF 🔴"
            return {"success": True, "output": f"📝 Auto prompt display: {status}\nUsage: /auto_prompt [on|off]"}
        
        if self.desktop_controller is None:
            return {
                "success": False,
                "output": "❌ Auto-prompt toggle is only available via DesktopController runtime.",
            }

        mode = parts[1].lower()
        if mode == "on":
            # Set on DesktopController
            try:
                self.desktop_controller._auto_prompt_enabled = True
                return {"success": True, "output": "📝 Auto prompt display enabled 🔵\nPrompt will be shown after each response."}
            except Exception as e:
                return {"success": False, "output": f"❌ Failed to enable auto-prompt: {e}"}
        elif mode == "off":
            # Set on DesktopController
            try:
                self.desktop_controller._auto_prompt_enabled = False
                return {"success": True, "output": "📝 Auto prompt display disabled 🔴"}
            except Exception as e:
                return {"success": False, "output": f"❌ Failed to disable auto-prompt: {e}"}
        else:
            return {"success": False, "output": "❌ Usage: /auto_prompt [on|off]"}

    # =========================================================================
    # Help
    # =========================================================================

    async def _cmd_help(self, parts, full_cmd):
        output = "\n" + "=" * 60 + "\n  🦊 KITSU COMMANDS\n" + "=" * 60 + "\n\n"
        output += "📁 System:\n"
        output += "  /quit, /exit         - Exit Kitsu\n"
        output += "  /clear               - Clear all memory\n"
        output += "  /clear_short         - Clear short-term memory\n"
        output += "  /clear_long          - Clear long-term memory\n"
        output += "  /reload              - Reload templates\n"
        output += "  /debug [on|off]      - Toggle debug logs\n"
        output += "  /auto_prompt [on|off] - Auto show prompt after responses\n\n"
        output += "📊 Information:\n"
        output += "  /stats               - Memory statistics\n"
        output += "  /state               - Emotional state\n"
        output += "  /model               - Model info\n"
        output += "  /search <q>          - Search memory\n"
        output += "  /prompt              - Last prompt used\n\n"
        output += "😊 Personality:\n"
        output += "  /mood <mode>         - Set mood (behave|mean|flirty)\n"
        output += "  /style <s>           - Set style\n"
        output += "  /trigger <n>         - Fire trigger\n\n"
        output += "👤 User:\n"
        output += "  /user                - Show user info\n"
        output += "  /user set <f> <v>    - Update user field\n\n"
        output += "🤖 Training:\n"
        output += "  /train <resp>        - Provide correct response for last turn\n"
        output += "  /rate <m|g|b>        - Rate last response (m=normal, g=good, b=bad)\n"
        output += "  /auto_train [on|off] [method]\n"
        output += "                       - Toggle auto-training + set method\n"
        output += "                         Methods: qlora (default), lora, dora, dpo,\n"
        output += "                                  rlhf, prefix, catboost, panda\n"
        output += "  /train_method <m>    - Change method without toggling\n"
        output += "  /train_status        - Show training status\n"
        output += "  /train_clear         - Clear all training data\n"
        output += "  /delete_llm          - Delete active LoRA adapter\n\n"
        output += "  ★ When /rate + /train are both used on the SAME response\n"
        output += "    and /auto_train is ON, micro-training fires instantly.\n\n"
        output += "🔢 Compression:\n"
        output += "  /compress status     - Encoder + NN stats\n"
        output += "  /compress train      - Manual offline retrain from existing data\n"
        output += "  /compress log        - Show last binary decision log\n"
        output += "  /compress debug on   - Show binary log after every response\n"
        output += "  /compress debug off  - Hide binary log\n"
        output += "  /compress seed       - Seed compression from training pairs\n\n"
        output += "🔢 Binary Features:\n"
        output += "  /binary show         - Show current binary features\n"
        output += "  /binary set <f> <0|1> - Set binary feature (0 or 1)\n"
        output += "  /binary reset        - Reset all binary features to 0\n"
        output += "  /binary list         - List all available features\n"
        output += "  /binary load <preset> - Load preset (playful|caring|direct|analytical)\n"
        output += "=" * 60 + "\n"
        return {"success": True, "output": output}




