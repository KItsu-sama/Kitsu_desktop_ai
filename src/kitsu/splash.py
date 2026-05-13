"""
src/kitsu/splash.py


Modern Kitsu Splash Screen - Simple ASCII art for modern system.
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)

class ModernSplash:
    """Simple splash screen for modern Kitsu system."""
    
    def __init__(self):
        self._ascii_art = self._get_ascii_art()
    
    def _get_ascii_art(self) -> str:
        """Get Kitsu ASCII art."""
        return r"""
╭────────────────────────────────────────────────────────── 🦊 KITSU AI - Modern Edition ──────────────────────────────────────────────────────────╮
│                                                                                                                                                            │     
│ Modern Event-Driven Architecture                                                                                                                               │ 
│ • InputMux (Sanity Layer) → EventBus → AI Pipeline                                                                                                            │  
│ • Multi-tier processing: FastBrain → SLM → LLM                                                                                                                │  
│ • Judge validation and behavior gating                                                                                                                           │
│                                                                                                                                                            │     
│ Type /help for commands or start chatting below!                                                                                                                  │
╰────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
"""
    
    def display_splash(self, mode: str = "text", model: str = "kitsu:character") -> None:
        """
        Display the complete splash screen.
        
        Args:
            mode: Application mode (text, voice, etc.)
            model: Model name being used
        """
        print(self._ascii_art)
        print(f"\n🎯 Mode: {mode}")
        print(f"🧠 Model: {model}")
        print("\n💡 Type your message below and press Enter to chat.")
        print("💡 Type 'exit' or 'quit' to stop.\n")
    
    def display_ascii_art_only(self) -> None:
        """Display just the ASCII art."""
        print(self._ascii_art)
