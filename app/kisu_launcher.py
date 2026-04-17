from __future__ import annotations

import logging
from pathlib import Path

from app.launcher import Launcher
from config.schema import load_character_config
from core.events import EventType, EventPayload

logger = logging.getLogger('kitsu.app.kisu_launcher')


class KisuLauncher(Launcher):
    async def startup(self) -> bool:
        success = await super().startup()
        if not success:
            return False

        character = self._load_default_character()
        self.event_bus.emit(
            EventType.CHARACTER_LOADED,
            EventPayload(source='kisu_launcher', data={'character': character.name}),
        )
        logger.info('Kisu character loaded: %s', character.name)
        return True

    def _load_default_character(self):
        character_path = Path('characters') / 'en_nuke_debate.yaml'
        if not character_path.exists():
            raise FileNotFoundError('Character config not found: %s' % character_path)
        return load_character_config(character_path)
