"""
interfaces/ui/dashboard.py - Quick UI for health monitoring dashboard

Provides a simple terminal-based dashboard showing system health status.
"""

import logging
from typing import Dict, Any

logger = logging.getLogger('kitsu.ui.dashboard')


class HealthDashboard:
    """Simple terminal dashboard for health monitoring."""
    
    def __init__(self):
        self.width = 50
        
    def render(self, status_data: Dict[str, Any]) -> None:
        """Render the health dashboard to terminal."""
        # Clear screen and render dashboard
        print("\033[2J\033[H")  # Clear screen
        
        self._render_header()
        self._render_status(status_data)
        self._render_modules(status_data.get('module_details', {}))
        self._render_footer()
        
    def _render_header(self) -> None:
        """Render dashboard header."""
        print("┌─ Kitsu Health Dashboard ──────────────────────┐")
        
    def _render_status(self, status: Dict[str, Any]) -> None:
        """Render main status indicators."""
        personality = status.get('personality', 'N/A')
        ai_tier = status.get('ai_tier', 'N/A')
        modules = status.get('modules', 'N/A')
        memory = status.get('memory_usage', 'N/A')
        resources = status.get('resources', 'N/A')
        
        # Determine status indicators
        personality_icon = "🟢" if personality != 'N/A' else "🔴"
        ai_tier_icon = "🟡" if "SLM" in ai_tier else "🟢" if ai_tier != 'N/A' else "🔴"
        modules_icon = "🟢" if "running" in modules else "🔴"
        
        print(f"│ {personality_icon} Personality: {personality.ljust(20)} │")
        print(f"│ {ai_tier_icon} AI Tier: {ai_tier.ljust(27)} │")
        print(f"│ {modules_icon} Modules: {modules.ljust(28)} │")
        print(f"│ Memory: {memory.ljust(20)} │ {resources.ljust(15)} │")
        
    def _render_modules(self, module_details: Dict[str, Any]) -> None:
        """Render detailed module status."""
        if not module_details:
            print("│ No module data available                        │")
            return
            
        print("├─ Module Status ────────────────────────────┤")
        
        # Sort modules by status (running first, then failed)
        running_modules = []
        failed_modules = []
        
        for module_id, details in module_details.items():
            if details.get('ok', True):
                running_modules.append((module_id, details))
            else:
                failed_modules.append((module_id, details))
        
        # Show running modules
        for module_id, details in running_modules[:5]:  # Limit to first 5
            latency = details.get('latency_ms', 0.0)
            print(f"│ 🟢 {module_id.ljust(20)}: {latency:.1f}ms{' ' * (10-len(f'{latency:.1f}ms'))} │")
        
        # Show failed modules
        for module_id, details in failed_modules[:3]:  # Limit to first 3 failed
            error = details.get('detail', 'Unknown error')[:15]
            print(f"│ 🔴 {module_id.ljust(20)}: {error.ljust(15)} │")
            
        # Show count if more modules exist
        total_running = len(running_modules)
        total_failed = len(failed_modules)
        total_shown = min(5, total_running) + min(3, total_failed)
        total_modules = total_running + total_failed
        
        if total_modules > total_shown:
            hidden = total_modules - total_shown
            print(f"│ ... {hidden} more modules not shown             │")
            
    def _render_footer(self) -> None:
        """Render dashboard footer."""
        print("└──────────────────────────────────────────────┘")
        
    def render_simple(self, status_data: Dict[str, Any]) -> None:
        """Render simple one-line status."""
        personality = status_data.get('personality', 'N/A')
        ai_tier = status_data.get('ai_tier', 'N/A') 
        modules = status_data.get('modules', 'N/A')
        
        print(f"Kitsu Status: {personality} | {ai_tier} | {modules}")


def render_dashboard(status_data: Dict[str, Any]) -> None:
    """Convenience function to render dashboard."""
    dashboard = HealthDashboard()
    dashboard.render(status_data)


def render_simple_status(status_data: Dict[str, Any]) -> None:
    """Convenience function to render simple status."""
    dashboard = HealthDashboard()
    dashboard.render_simple(status_data)
