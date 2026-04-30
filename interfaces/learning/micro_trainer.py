from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List

from domain.ai.fast_brain.trainer import Trainer

logger = logging.getLogger('kitsu.core.learning.micro_trainer')


class MicroTrainer:
    """Lightweight trainer for background FastBrain updates."""

    def verify_dataset(self, dataset_path: str) -> bool:
        """Verify dataset integrity before any destructive cleanup."""
        path = Path(dataset_path)
        if not path.exists():
            logger.error('Dataset path does not exist: %s', dataset_path)
            return False

        try:
            with path.open('r', encoding='utf-8') as handle:
                data = json.load(handle)
        except Exception as exc:
            logger.error('Failed to parse dataset file: %s', exc)
            return False

        if not isinstance(data, list):
            logger.error('Dataset must be a JSON list of conversation records')
            return False

        for index, item in enumerate(data):
            if not isinstance(item, dict):
                logger.error('Dataset entry %d is not a JSON object', index)
                return False
            if 'user_input' not in item or 'response' not in item:
                logger.error('Dataset entry %d missing required fields', index)
                return False
            if not isinstance(item['user_input'], str) or not isinstance(item['response'], str):
                logger.error('Dataset entry %d has invalid field types', index)
                return False

        logger.info('Dataset integrity verified: %s entries', len(data))
        return True

    def train(self, dataset: list[dict[str, Any]] | dict[str, Any]) -> dict[str, Any]:
        """Train FastBrain models from a verified dataset."""
        if isinstance(dataset, dict):
            dataset = [dataset]

        if not isinstance(dataset, list):
            raise ValueError('Dataset must be a list or dict')

        records = []
        for record in dataset:
            if not isinstance(record, dict):
                continue
            user_input = record.get('user_input')
            response = record.get('response')
            if not isinstance(user_input, str) or not isinstance(response, str):
                continue
            records.append((user_input.strip(), response.strip(), float(record.get('quality', 0.5))))

        trainer = Trainer()
        trainer.min_examples_for_training = 0
        trainer.max_examples = max(len(records), trainer.max_examples)

        for user_input, response, quality in records:
            trainer.add_training_example(
                user_input=user_input,
                response=response,
                quality=quality,
                context={}
            )

        trained = trainer.train_models()
        trainer.save_models('data/models')

        return {
            'trained': trained,
            'samples': len(records),
            'loss': None,
            'accuracy': None,
        }
