import json
from pathlib import Path
from typing import Optional

CONFIGS_DIR = Path(__file__).parent.parent / "configs"

# Cache loaded configs to avoid re-reading from disk on every parse call
_cache: dict[str, dict] = {}


def load_templates(telco: str) -> dict:
    """Load and cache a single telco's template config."""
    if telco in _cache:
        return _cache[telco]
    path = CONFIGS_DIR / f"{telco}_templates.json"
    if not path.exists():
        return {}
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    _cache[telco] = data
    return data


def load_all_templates() -> dict[str, dict]:
    """Load configs for every telco that has a JSON file in configs/."""
    result = {}
    for path in CONFIGS_DIR.glob("*_templates.json"):
        telco = path.stem.replace("_templates", "")
        result[telco] = load_templates(telco)
    return result


def get_sender_map() -> dict[str, str]:
    """Build a flat sender_id → telco mapping from all loaded configs."""
    mapping = {}
    for telco, config in load_all_templates().items():
        for sender_id in config.get("sender_ids", []):
            mapping[sender_id] = telco
    return mapping
