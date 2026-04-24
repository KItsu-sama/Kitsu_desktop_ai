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
try:
    from config.personality_config import VALID_MOODS, VALID_STYLES
    EMOTION_CONFIG_AVAILABLE = True
except ImportError:
    EMOTION_CONFIG_AVAILABLE = False
    VALID_MOODS = {"behave", "mean", "flirty", "protective"}
    VALID_STYLES = {"chaotic", "sweet", "cold", "direct", "sarcastic", "playful", "eerie"}

# UI library imports (optional)
try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.prompt import Prompt, Confirm
    from rich import box
    RICH_AVAILABLE = True
except ImportError:
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
        self.console = Console() if RICH_AVAILABLE else None
        
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
        
        # 1. User Profile
        results["user_profile"] = self._setup_user_profile()
        
        # 2. Permissions
        results["permissions"] = self._setup_permissions()
        
        # 3. Personality
        results["personality"] = self._setup_personality()
        
        # 4. Runtime Settings
        results["runtime"] = self._setup_runtime()
        
        # 5. Feature Selection
        results["features"] = self._setup_features()
        
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
        
        return {
            "user_profile": {
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
            "runtime": {
                "mode": "text",
                "model": "kitsu:character",
                "is_character_model": True,
                "temperature": 0.8,
                "streaming": True,
                "greet_on_startup": True,
                "continuous_decay": False,
                "enable_tts": False,
                "enable_stt": False,
                "enable_avatar": False,
                "memory_max_history": 200
            },
            "features": self._get_default_features(capabilities)
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
        self._print_section("👤 User Profile")
        
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
        self._print_section("🔒 Permissions")
        
        self._print_info(
            "Kitsu can integrate with your system.",
            ["All features are opt-in", "Can be changed later in config"]
        )
        
        browser = self._ask_yes_no(
            "Allow browser integration?",
            default=False
        )
        
        self._print_info(
            "⚠️  System control allows:",
            [
                "Monitor idle time",
                "Read system stats (CPU, memory)"
            ]
        )
        
        system_control = self._ask_yes_no(
            "Allow system control?",
            default=False
        )
        
        file_access = self._ask_yes_no(
            "Allow file access outside data/?",
            default=False
        )
        
        safe_mode = self._ask_yes_no(
            "Enable safe mode? (Recommended)",
            default=True
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
        self._print_section("😊 Personality")
        
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
        """Configure runtime settings"""
        self._print_section("⚙️  Runtime Settings")
        
        # Model selection
        self._print_info(
            "Available models:",
            [
                "1. Kitsu:Character (optimized character AI, recommended) ⭐",
                "2. TinyLlama 1.1B (fastest, low-end GPU)",
                "3. Gemma 2B (balanced)",
                "4. Qwen 1.8B (smarter, slower)",
                "5. Custom model"
            ]
        )
        
        model_choice = self._ask_question(
            "Choose model",
            default="1",
            options=["1", "2", "3", "4", "5"]
        )
        
        MODEL_MAP = {
            "1": "kitsu:character",
            "2": "tinyllama:1.1b",
            "3": "gemma:2b",
            "4": "qwen:1.8b"
        }
        
        if model_choice == "5":
            model = self._ask_question("Enter model name")
        else:
            model = MODEL_MAP[model_choice]
        
        capabilities = self.system_info.get("capabilities", {})
        
        # Voice features
        enable_tts = False
        enable_stt = False
        
        if capabilities.get("audio_output"):
            self._print("✓ Audio output detected")
            enable_tts = self._ask_yes_no(
                "Enable text-to-speech?",
                default=False
            )
        
        if capabilities.get("audio_input") and enable_tts:
            self._print("✓ Audio input detected")
            enable_stt = self._ask_yes_no(
                "Enable speech-to-text?",
                default=False
            )
        
        # Avatar
        enable_avatar = False
        if capabilities.get("gpu"):
            self._print("✓ GPU detected")
            enable_avatar = self._ask_yes_no(
                "Enable 3D avatar?",
                default=False
            )
        
        greet_on_startup = self._ask_yes_no(
            "Show greeting on startup?",
            default=True
        )
        
        continuous_decay = self._ask_yes_no(
            "Enable continuous emotion decay?",
            default=False
        )
        
        # Determine if using character model
        is_character_model = model.lower().startswith("kitsu:")
        
        return {
            "mode": "voice" if (enable_tts and enable_stt) else "text",
            "model": model,
            "is_character_model": is_character_model,
            "temperature": 0.8,
            "streaming": True,
            "greet_on_startup": greet_on_startup,
            "continuous_decay": continuous_decay,
            "enable_tts": enable_tts,
            "enable_stt": enable_stt,
            "enable_avatar": enable_avatar,
            "memory_max_history": 200
        }
    
    def _setup_features(self) -> Dict[str, bool]:
        """Configure optional features from featurespec.json"""
        self._print_section("🔌 Optional Features")
        
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
        if self.console:
            self.console.clear()
            self.console.print(Panel.fit(
                "[bold magenta]🦊 KITSU SETUP WIZARD[/bold magenta]\n"
                "[white]Let's configure Kitsu together![/white]",
                border_style="magenta",
                box=box.DOUBLE_EDGE
            ))
            self.console.print("")
        else:
            print("\n" + "=" * 60)
            print("  🦊 KITSU SETUP WIZARD")
            print("=" * 60)
            print("\nLet's configure Kitsu together!\n")
    
    def _print_section(self, title: str):
        """Print section header"""
        if self.console:
            self.console.print(f"\n[bold cyan]{title}[/bold cyan]")
            self.console.print("[cyan]" + "─" * 60 + "[/cyan]\n")
        else:
            print(f"\n{title}")
            print("─" * 60 + "\n")
    
    def _print_info(self, title: str, items: List[str]):
        """Print informational list"""
        if self.console:
            self.console.print(f"\n{title}")
            for item in items:
                self.console.print(f"  - {item}")
        else:
            print(f"\n{title}")
            for item in items:
                print(f"  - {item}")
    
    def _print(self, message: str):
        """Print message"""
        if self.console:
            self.console.print(message)
        else:
            print(message)
    
    def _print_summary(self, results: Dict[str, Any]):
        """Print configuration summary"""
        profile = results.get("user_profile", {})
        personality = results.get("personality", {})
        runtime = results.get("runtime", {})
        features = results.get("features", {})
        
        enabled_features = [k for k, v in features.items() if v]
        
        summary = f"""
Configuration Summary:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

User: {profile.get('name')} ({profile.get('nickname')})
Admin: {profile.get('permissions', {}).get('is_admin', False)}

Personality: {personality.get('default_mood')} / {personality.get('default_style')}
Sass: {personality.get('enable_sass', False)}

Model: {runtime.get('model')}
Mode: {runtime.get('mode')}
Voice: {runtime.get('enable_tts', False)}
Avatar: {runtime.get('enable_avatar', False)}

Features: {len(enabled_features)} enabled
{chr(10).join('  ✓ ' + f for f in enabled_features) if enabled_features else '  (none)'}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
        
        if self.console:
            self.console.print(Panel(summary, border_style=".GREEN", box=box.DOUBLE_EDGE))
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
                if RICH_AVAILABLE and self.console:
                    if options:
                        answer = Prompt.ask(prompt.rstrip(': '), choices=options, default=default)
                    else:
                        answer = Prompt.ask(prompt.rstrip(': '), default=default)
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
    
    def _ask_yes_no(self, prompt: str, default: bool = False) -> bool:
        """Ask yes/no question"""
        default_str = "Y/n" if default else "y/N"
        
        if RICH_AVAILABLE and self.console:
            return Confirm.ask(f"{prompt}", default=default)
        else:
            answer = self._ask_question(
                f"{prompt} ({default_str})",
                default="y" if default else "n",
                options=["y", "n", "yes", "no"]
            )
            return answer.lower() in ["y", "yes"]


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