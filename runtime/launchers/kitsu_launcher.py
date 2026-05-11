from __future__ import annotations

import logging
from pathlib import Path

from runtime.legacy.launcher import Launcher
from shared.schemas import load_character_config
from runtime.communication.events import EventType, EventPayload

logger = logging.getLogger('kitsu.app.kitsu_launcher')


class kitsuLauncher(Launcher):
    async def startup(self) -> bool:
        success = await super().startup()
        if not success:
            return False

        character = self._load_default_character()
        self.event_bus.publish(
            EventPayload(
                event_type=EventType.CHARACTER_LOADED,
                source='kitsu_launcher',
                data={'character': character.name}
            )
        )
        logger.info('kitsu character loaded: %s', character.name)
        return True

    def _load_default_character(self):
        character_path = Path('characters') / 'en_nuke_debate.yaml'
        if not character_path.exists():
            raise FileNotFoundError('Character config not found: %s' % character_path)
        return load_character_config(character_path)
