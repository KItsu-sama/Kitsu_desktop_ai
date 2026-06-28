"""
scripts/setup_wizard.py — Interactive Setup Wizard (Architecture Compliant)

RESPONSIBILITIES:
- Ask user questions interactively
- Return configuration dict (does NOT write files itself)
- Validate user inputs
- Recommend features based on system capabilities

MUST NOT:
- Write configuration files (first_run.py does this)
- Start runtime
- Import core runtime modules (except emotion_config for validation)
- Assume interactive environment
"""

import sys
from typing import Dict, Any, Optional, List

# Only import for validation (allowed exception per architecture)

from domain.personality.emotion_config import VALID_MOODS, VALID_STYLES

# UI library rendering + prompts are centralized.
try:
    from application.terminal_ui import (
        capabilities as _terminal_capabilities,
        terminal_print as _terminal_print,
        terminal_print_panel as _terminal_print_panel,
        terminal_ask_question as _terminal_ask_question,
        terminal_ask_yes_no as _terminal_ask_yes_no,
    )


    RICH_AVAILABLE = bool(_terminal_capabilities().supports_rich)

    # Backward-compatible alias: wizard previously used rich Console/Prompt/Confirm.
    # Now we route interactive IO through application.terminal_ui.
    Console = None  # type: ignore
    Panel = None  # type: ignore
    Prompt = None  # type: ignore
    Confirm = None  # type: ignore
    box = None  # type: ignore
except Exception:
    RICH_AVAILABLE = False
    Console = None  # type: ignore
    Panel = None  # type: ignore
    Prompt = None  # type: ignore
    Confirm = None  # type: ignore
    box = None  # type: ignore
    _terminal_print = print
    _terminal_print_panel = None
    _terminal_ask_question = input
    _terminal_ask_yes_no = None



# Check for Windows encoding issues
import platform
if platform.system() == "Windows":
    try:
        import sys
        if sys.stdout.encoding.lower() not in ['utf-8', 'utf8']:
            RICH_AVAILABLE = False
    except Exception:
        RICH_AVAILABLE = False


class SetupWizard:
    """
    Interactive configuration wizard.
    
    Returns configuration dict without writing files.
    File writing is delegated to first_run.py.
    """
    
    def __init__(self, system_info: Optional[Dict[str, Any]] = None):
        """
        Initialize wizard.
        
        Args:
            system_info: System capabilities from first_run.detect_system_info()
        """
        self.system_info = system_info or {}
        # All terminal rendering + prompts must go through application.terminal_ui.
        self.console = None

        
        # Load feature specs if available
        self.features = self._load_feature_specs()
    
    def _load_feature_specs(self) -> Dict[str, Any]:
        """Load feature specifications from docs/featurespec.json"""
        try:
            import json
            from pathlib import Path
            
            spec_path = Path("docs/featurespec.json")
            if spec_path.exists():
                return json.loads(spec_path.read_text(encoding='utf-8'))
            return {"features": []}
        except Exception:
            return {"features": []}
    
    def run(self) -> Dict[str, Any]:
        """
        Run interactive wizard.
        
        Returns:
            Complete configuration dict with all settings
        """
        # Check if running in interactive terminal
        if sys.stdin and sys.stdin.isatty():
            return self._run_interactive()
        else:
            # Headless/non-interactive fallback
            return self.apply_defaults()
    
    def _run_interactive(self) -> Dict[str, Any]:
        """Run full interactive wizard"""
        self._print_welcome()
        
        results = {}
        
        # 0. Strip System (device scan)
        results["system"] = self._strip_system_scan()
        
        # 1. Kitsu (runtime/settings)
        results["kitsu"] = self._setup_kitsu_block()
        
        # 2. User
        results["user"] = self._setup_user_block()
        
        # 3. Finalize
        accept = self._confirm_accept_or_customize(results)
        results["customized"] = not accept
        
        self._print_summary(results)
        
        return results
    
    def apply_defaults(self) -> Dict[str, Any]:
        """
        Generate default configuration without interaction.

        Used for headless/non-interactive environments.

        Returns:
            Default configuration dict
        """
        capabilities = self.system_info.get("capabilities", {})

        # Unified 3-part structure: system / kitsu / user
        return {
            "system": self._strip_system_scan(),
            "kitsu": {
                "permissions": {
                    "browser_hooks": False,
                    "system_control": False,
                    "file_access": False,
                    "safe_mode": True,
                    "can_train": False,
                    "can_modify_memory": True
                },
                "personality": {
                    "default_mood": "behave",
                    "default_style": "chaotic",
                    "enable_sass": True,
                    "enable_pranks": False,
                    "sass_level": 0.3,
                    "prank_frequency": 0.0,
                    "emotion_decay_rate": 0.1,
                    "emotion_threshold": 0.3,
                    "max_stack_size": 5
                },
                "runtime": self._get_default_runtime_from_capabilities(capabilities),
                "features": self._get_default_features(capabilities)
            },
            "user": {
                "name": "User",
                "nickname": "User",
                "refer_title": "User",
                "gender": "unspecified",
                "status": "user",
                "permissions": {
                    "is_admin": False,
                    "dev_console": False
                },
                "relationship": {
                    "trust_level": 0.5,
                    "affinity": 0.5,
                    "lore_tag": "stranger"
                }
            },
            "customized": False
        }
    
    def _get_default_features(self, capabilities: Dict[str, bool]) -> Dict[str, bool]:
        """Determine default feature enablement based on capabilities"""
        features = {}
        
        # Parse feature specs and set defaults
        for feature in self.features.get("features", []):
            feature_id = feature.get("id")
            requirements = feature.get("requirements", {})
            
            # Check if requirements are met
            can_enable = True
            
            if requirements.get("audio_out") and not capabilities.get("audio_output"):
                can_enable = False
            if requirements.get("audio_in") and not capabilities.get("audio_input"):
                can_enable = False
            if requirements.get("browser") and self.system_info.get("headless"):
                can_enable = False
            
            # Default to False unless it's a core feature
            is_core = feature.get("tier") == "core"
            features[feature_id] = is_core and can_enable
        
        return features
    
    # =========================================================================
    # Setup Sections
    # =========================================================================
    
    def _setup_user_profile(self) -> Dict[str, Any]:
        """Configure user profile"""
        self._print_section("USER PROFILE")
        
        name = self._ask_question(
            "What's your name?",
            default="User"
        )
        
        nickname = self._ask_question(
            "What should Kitsu call you?",
            default=name
        )
        
        refer_title = self._ask_question(
            "How should Kitsu address you?",
            default=nickname,
            options=["Master", "Boss", "Friend", "Senpai", nickname]
        )
        
        gender = self._ask_question(
            "Gender (for pronoun context)?",
            default="unspecified",
            options=["male", "female", "non-binary", "unspecified"]
        )
        
        # Admin status
        self._print_info(
            "⚠️  Admin privileges enable:",
            [
                "Dev console access",
                "System configuration changes",
                "Model training/fine-tuning"
            ]
        )
        
        is_admin = self._ask_yes_no(
            "Grant admin privileges?",
            default=False
        )
        
        return {
            "name": name,
            "nickname": nickname,
            "refer_title": refer_title,
            "gender": gender,
            "status": "admin" if is_admin else "user",
            "permissions": {
                "is_admin": is_admin,
                "dev_console": is_admin
            },
            "relationship": {
                "trust_level": 0.5,
                "affinity": 0.5,
                "lore_tag": "stranger"
            }
        }
    
    def _setup_permissions(self) -> Dict[str, Any]:
        """Configure system permissions"""
        self._print_section("PERMISSIONS")

        _terminal_print("\n[bold yellow]Kitsu can integrate with your system.[/bold yellow]")
        _terminal_print("[cyan]All features are opt-in[/cyan]")
        _terminal_print("[cyan]Can be changed later in config[/cyan]")


        self._print_info(
            'Tip: type "h" in the prompt to see risk details.',
            [

                "system control = extra privileges (safe to leave off)",
                "file access outside data/? = broader filesystem access",
                "safe mode = restricts dangerous behavior on crashes/edge cases",
            ],
        )

        browser = self._ask_yes_no(
            "Allow browser integration?",
            default=False,
            help_text="Browser integration can read limited page context depending on the plugin. Leave off if you want zero browser access.",
        )

        system_control = self._ask_yes_no(
            "Allow system control?",
            default=False,
            help_text=(
                "System control may monitor idle time and read system stats (CPU/RAM). Enabling it increases permissions. "
                "Recommended: keep OFF unless you trust the local installation."
            ),
        )

        file_access = self._ask_yes_no(
            "Allow file access outside data/?",
            default=False,
            help_text=(
                "File access outside data/ can expose or overwrite user files. Recommended: keep OFF unless you need it."
            ),
        )

        safe_mode = self._ask_yes_no(
            "Enable safe mode? (Recommended)",
            default=True,
            help_text=(
                "Safe mode restricts risky behaviors, and can fall back to safer operation after crashes. "
                "Recommended for first-time runs."
            ),
        )

        
        return {
            "browser_hooks": browser,
            "system_control": system_control,
            "file_access": file_access,
            "safe_mode": safe_mode,
            "can_train": False,  # Set separately
            "can_modify_memory": True
        }
    
    def _setup_personality(self) -> Dict[str, Any]:
        """Configure personality defaults"""
        self._print_section("PERSONALITY")
        
        self._print_info(
            "Personality modes:",
            [
                "behave: Cooperative and helpful",
                "mean: Teasing and sassy",
                "flirty: Affectionate and playful",
                "protective: Caring and defensive"
            ]
        )
        
        mood = self._ask_question(
            "Default mood?",
            default="behave",
            options=sorted(list(VALID_MOODS))
        )
        
        self._print_info(
            "Expression styles:",
            [
                "chaotic: Energetic and unpredictable",
                "sweet: Warm and gentle",
                "cold: Emotionally distant",
                "direct: Minimal and blunt",
                "sarcastic: Dry humor",
                "playful: Light teasing",
                "eerie: Mysterious"
            ]
        )
        
        style = self._ask_question(
            "Default style?",
            default="chaotic",
            options=sorted(list(VALID_STYLES))
        )
        
        enable_sass = self._ask_yes_no(
            "Enable sassy responses?",
            default=True
        )
        
        enable_pranks = self._ask_yes_no(
            "Enable harmless pranks?",
            default=False
        )
        
        return {
            "default_mood": mood,
            "default_style": style,
            "enable_sass": enable_sass,
            "enable_pranks": enable_pranks,
            "sass_level": 0.3 if enable_sass else 0.0,
            "prank_frequency": 0.1 if enable_pranks else 0.0,
            "emotion_decay_rate": 0.1,
            "emotion_threshold": 0.3,
            "max_stack_size": 5
        }
    
    def _setup_runtime(self) -> Dict[str, Any]:
        """Legacy runtime setup (kept for compatibility)."""
        return self._setup_runtime_from_adaptive_model()

    def _setup_runtime_from_adaptive_model(self) -> Dict[str, Any]:
        """Runtime settings with adaptive model selection (API-driven when available)."""
        self._print_section("RUNTIME SETTINGS")

        capabilities = self.system_info.get("capabilities", {})

        # Model selection
        # Goal: let user choose SLM + LLM independently.
        # LLM models must be provided via API (using LLM_BASE_URL) or free-text.

        api_mode = self._ask_question(
            "Choose LLM backend mode",
            default="api",
            options=["api", "none"],
        )

        llm_base_url = ""
        llm_model = ""

        if api_mode == "api":
            llm_base_url = self._ask_question(
                "Enter LLM_BASE_URL (e.g., http://localhost:11434 or https://...)",
                default="http://localhost:11434",
            ).strip().rstrip("/")

            # If we have an API client for available models, use it.
            available_models = self._fetch_available_models_from_api(llm_base_url) or []
            if not available_models:
                llm_model = self._ask_question("Enter LLM model name", default="")
            else:
                self._print_info(
                    "Available LLM models:",
                    [f"{i}. {m}" for i, m in enumerate(available_models, start=1)] + ["0. Custom model"],
                )
                model_choice = self._ask_question(
                    "Choose LLM model",
                    default="1",
                    options=[str(i) for i in range(1, len(available_models) + 1)] + ["0"],
                )
                if model_choice == "0":
                    llm_model = self._ask_question("Enter LLM model name", default=available_models[0])
                else:
                    llm_model = available_models[int(model_choice) - 1]

        # SLM selection: choose whether to enable SLM tier at all.
        slm_enabled = self._ask_yes_no(
            "Enable SLM tier?",
            default=True,
        )

        # LLM tier selection: choose whether to enable LLM tier at all.
        llm_enabled = self._ask_yes_no(
            "Enable LLM tier?",
            default=True,
        )

        # kitsu:character is treated as an unavailable model.
        if isinstance(llm_model, str) and llm_model.lower().startswith("kitsu:"):
            llm_model = ""

        # Voice features
        enable_tts = False
        enable_stt = False
        slm_enabled = slm_enabled
        llm_enabled = llm_enabled

        if capabilities.get("audio_output"):
            self._print("✓ Audio output detected")
            enable_tts = self._ask_yes_no("Enable text-to-speech?", default=False)

        if capabilities.get("audio_input") and enable_tts:
            self._print("✓ Audio input detected")
            enable_stt = self._ask_yes_no("Enable speech-to-text?", default=False)

        # Avatar
        enable_avatar = False
        if capabilities.get("gpu"):
            self._print("✓ GPU detected")
            enable_avatar = self._ask_yes_no("Enable 3D avatar?", default=False)

        greet_on_startup = self._ask_yes_no("Show greeting on startup?", default=True)
        continuous_decay = self._ask_yes_no("Enable continuous emotion decay?", default=False)

        return {
            "mode": "voice" if (enable_tts and enable_stt) else "text",
            # canonical runtime selection no longer hardcodes kitsu:character
            "is_character_model": False,
            "temperature": 0.8,
            "streaming": True,
            "greet_on_startup": greet_on_startup,
            "continuous_decay": continuous_decay,
            "enable_tts": enable_tts,
            "enable_stt": enable_stt,
            "enable_avatar": enable_avatar,
            "memory_max_history": 200,
            "slm": {
                "enabled": slm_enabled,
            },
            "llm": {
                "enabled": llm_enabled,
                "base_url": llm_base_url,
                "model": llm_model,
            },
        }


    def _fetch_available_models_from_api(self, llm_base_url: str) -> Optional[list]:
        """Best-effort API call to discover models for a given LLM_BASE_URL.

        This wizard must not assume network availability; errors are swallowed.
        """
        try:
            # Prefer local API inside the app (if implemented)
            from interfaces.api.client import get_available_models  # type: ignore
            models = get_available_models(llm_base_url=llm_base_url)  # type: ignore[arg-type]
            if isinstance(models, list) and models:
                return models
        except Exception:
            pass
        return None

    def _strip_system_scan(self) -> Dict[str, Any]:
        """Strip System: scan device/capabilities and present as system block."""
        platform_name = self.system_info.get("platform", "unknown")
        caps = self.system_info.get("capabilities", {})

        return {
            "platform": platform_name,
            "capabilities": {
                "gpu": bool(caps.get("gpu", False)),
                "cuda": bool(caps.get("cuda", False)),
                "audio_input": bool(caps.get("audio_input", False)),
                "audio_output": bool(caps.get("audio_output", False)),
                "display": bool(caps.get("display", True)),
                "network": bool(caps.get("network", True)),
            },
            "headless": bool(self.system_info.get("headless", False)),
        }

    def _get_default_runtime_from_capabilities(self, capabilities: Dict[str, bool]) -> Dict[str, Any]:
        """Compute safe default runtime based on detected capabilities."""
        # Keep a safe default model; first_run/app will adapt further if needed.
        default_model = "kitsu:character"

        enable_tts = bool(capabilities.get("audio_output", False)) and False
        enable_stt = bool(capabilities.get("audio_input", False)) and enable_tts and False

        return {
            "mode": "voice" if (enable_tts and enable_stt) else "text",
            "model": default_model,
            "is_character_model": True,
            "temperature": 0.8,
            "streaming": True,
            "greet_on_startup": True,
            "continuous_decay": False,
            "enable_tts": enable_tts,
            "enable_stt": enable_stt,
            "enable_avatar": bool(capabilities.get("gpu", False)) and False,
            "memory_max_history": 200,
        }

    def _setup_kitsu_block(self) -> Dict[str, Any]:
        """Kitsu block: permissions + personality + runtime + features."""
        permissions = self._setup_permissions()
        personality = self._setup_personality()
        runtime = self._setup_runtime_from_adaptive_model()
        features = self._setup_features()
        return {
            "permissions": permissions,
            "personality": personality,
            "runtime": runtime,
            "features": features,
        }

    def _setup_user_block(self) -> Dict[str, Any]:
        """User block."""
        return self._setup_user_profile()

    def _confirm_accept_or_customize(self, results: Dict[str, Any]) -> bool:
        """Final gate: accept defaults or customize."""
        self._print_section("FINALIZE")
        choice = self._ask_yes_no("Accept these settings?", default=True)

        if choice:
            return True

        # Customize flow (minimal: rerun blocks)
        self._print("\nCustomize selected sections now...")
        # Allow user to redo kitsu section; system/user are scanned/collected already.
        redo_kitsu = self._ask_yes_no("Customize Kitsu settings (permissions/personality/runtime/features)?", default=True)
        if redo_kitsu:
            results["kitsu"] = self._setup_kitsu_block()

        results["customized"] = True
        return False
    
    def _setup_features(self) -> Dict[str, bool]:
        """Configure optional features from featurespec.json"""
        self._print_section("OPTIONAL FEATURES")
        
        if not self.features.get("features"):
            self._print("No optional features available")
            return {}
        
        self._print("Select features to enable:")
        
        capabilities = self.system_info.get("capabilities", {})
        selected = {}
        
        for feature in self.features.get("features", []):
            feature_id = feature.get("id")
            feature_name = feature.get("name")
            description = feature.get("description", "")
            requirements = feature.get("requirements", {})
            tier = feature.get("tier", "optional")
            
            # Check if requirements are met
            can_enable = self._check_feature_requirements(requirements, capabilities)
            
            if not can_enable:
                self._print(f"  ✗ {feature_name} (requirements not met)")
                selected[feature_id] = False
                continue
            
            # Core features enabled by default
            default = (tier == "core")
            
            prompt = f"  {feature_name}? ({description})"
            enabled = self._ask_yes_no(prompt, default=default)
            selected[feature_id] = enabled
        
        return selected
    
    def _check_feature_requirements(
        self,
        requirements: Dict[str, Any],
        capabilities: Dict[str, bool]
    ) -> bool:
        """Check if system meets feature requirements"""
        if requirements.get("audio_out") and not capabilities.get("audio_output"):
            return False
        if requirements.get("audio_in") and not capabilities.get("audio_input"):
            return False
        if requirements.get("browser") and self.system_info.get("headless"):
            return False
        if requirements.get("online") and not capabilities.get("network", True):
            return False
        
        return True
    
    # =========================================================================
    # Display Utilities
    # =========================================================================
    
    def _print_welcome(self):
        """Print welcome message"""
        if _terminal_print_panel is not None:
            _terminal_print_panel(
                title="Kitsu setup wizard",
                body="Let's configure Kitsu together!",
                border_style="magenta",
            )
            return

        print("\n" + "=" * 60)
        print("  KITSU SETUP WIZARD")
        print("=" * 60)
        print("\nLet's configure Kitsu together!\n")
    
    def _print_section(self, title: str):
        """Print section header"""
        _terminal_print(f"\n[bold cyan]{title}[/bold cyan]")
        _terminal_print("[cyan]" + "─" * 60 + "[/cyan]\n")
    
    def _print_info(self, title: str, items: List[str]):
        """Print informational list"""
        _terminal_print(f"\n{title}")
        for item in items:
            _terminal_print(f"  - {item}")
    
    def _print(self, message: str):
        """Print message"""
        _terminal_print(message)
    
    def _print_summary(self, results: Dict[str, Any]):
        """Print configuration summary"""
        system = results.get("system", {})
        kitsu = results.get("kitsu", {})
        user = results.get("user", {})

        personality = kitsu.get("personality", {})
        runtime = kitsu.get("runtime", {})
        features = kitsu.get("features", {})

        enabled_features = [k for k, v in features.items() if v]

        model = runtime.get('model')
        if not model:
            model = "(auto)"

        summary = f"""
Configuration Summary:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

System: {system.get('platform', 'unknown')}\r
GPU: {system.get('capabilities', {}).get('gpu', False)}\r
Headless: {system.get('headless', False)}

User: {user.get('name')} ({user.get('nickname')})
Admin: {user.get('permissions', {}).get('is_admin', False)}

Personality: {personality.get('default_mood')} / {personality.get('default_style')}
Sass: {personality.get('enable_sass', False)}

Model: {model}
Mode: {runtime.get('mode')}
Voice: {runtime.get('enable_tts', False)}
Avatar: {runtime.get('enable_avatar', False)}

Features: {len(enabled_features)} enabled
{chr(10).join('  ✓ ' + f for f in enabled_features) if enabled_features else '  (none)'}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

        if _terminal_print_panel is not None:
            _terminal_print_panel(
                title="Configuration summary",
                body=summary,
                border_style="green",
            )
        else:
            print(summary)
    
    # =========================================================================
    # Input Utilities
    # =========================================================================
    
    def _ask_question(
        self,
        prompt: str,
        default: str = "",
        options: Optional[List[str]] = None
    ) -> str:
        """Ask a question with validation"""
        if options:
            prompt += f" ({'/'.join(options[:3])}{'...' if len(options) > 3 else ''})"
        
        if default:
            prompt += f" [{default}]"
        
        prompt += ": "
        
        while True:
            try:
                if _terminal_ask_question is not input and options:
                    answer = _terminal_ask_question(prompt.rstrip(": "), default=default, options=options)
                elif _terminal_ask_question is not input:
                    answer = _terminal_ask_question(prompt.rstrip(": "), default=default)
                else:
                    answer = input(prompt).strip()
                    if not answer:
                        answer = default
                
                if options and answer not in options:
                    self._print(f"Invalid option. Choose from: {', '.join(options)}")
                    continue
                
                return answer
            
            except KeyboardInterrupt:
                self._print(f"\nUsing default: {default}")
                return default
            except EOFError:
                return default
    
    def _ask_yes_no(self, prompt: str, default: bool = False, help_text: Optional[str] = None) -> bool:
        """Ask yes/no question.

        If help_text is provided, the user can press [h] to view risk details.
        """
        if _terminal_ask_yes_no is not None:
            return _terminal_ask_yes_no(prompt, default=default, help_text=help_text)

        # Exact formatting to match required output:
        #   - default=False => show: [y/n] (n)  and accept Enter => (n)
        #   - default=True  => show: [y/n] (y)  and accept Enter => (y)
        choice_suffix = "(y)" if default else "(n)"
        while True:
            raw = input(f"{prompt} [y/n] {choice_suffix}").strip()
            if raw.lower() == "h":
                if help_text:
                    self._print(help_text)
                continue
            if not raw:
                raw = "y" if default else "n"
            if raw.lower() in ["y", "yes"]:
                return True
            if raw.lower() in ["n", "no"]:
                return False
            self._print("Please enter y or n (or 'h' for help).")



# =============================================================================
# Test
# =============================================================================

if __name__ == "__main__":
    import json
    
    # Mock system info for testing
    system_info = {
        "platform": "Windows",
        "capabilities": {
            "gpu": True,
            "cuda": True,
            "audio_input": True,
            "audio_output": True,
            "display": True,
            "network": True
        },
        "headless": False
    }
    
    wizard = SetupWizard(system_info)
    
    # Test interactive mode
    if sys.stdin and sys.stdin.isatty():
        results = wizard.run()
    else:
        # Test headless mode
        results = wizard.apply_defaults()
    
    print("\n📄 Generated Configuration:")
    print(json.dumps(results, indent=2))