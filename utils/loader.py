import json
from pathlib import Path


CONFIG_PATH = Path("data/config.json")


def load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def deep_merge(base: dict, override: dict) -> dict:
    for k, v in override.items():
        if isinstance(v, dict) and isinstance(base.get(k), dict):
            base[k] = deep_merge(base[k], v)
        else:
            base[k] = v
    return base

