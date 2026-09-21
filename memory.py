import json
import os
import tempfile
from pathlib import Path

MEMORY_PATH = Path(os.path.join(tempfile.gettempdir(), "memory.json"))

DEFAULT_MEMORY = {
    "user_skin_type": None,
    "known_allergies": [],
    "escalations": [],
    "preferences": {
        "language": "en",
        "detail_level": "medium",
    },
}


def load_memory() -> dict:
    if MEMORY_PATH.exists():
        try:
            with open(MEMORY_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                return {**DEFAULT_MEMORY, **data}
        except (json.JSONDecodeError, IOError):
            return DEFAULT_MEMORY.copy()
    return DEFAULT_MEMORY.copy()


def save_memory(memory: dict) -> dict:
    os.makedirs(os.path.dirname(MEMORY_PATH), exist_ok=True)
    with open(MEMORY_PATH, "w", encoding="utf-8") as f:
        json.dump(memory, f, indent=2, ensure_ascii=False)
    return memory


def update_memory(memory: dict, **kwargs) -> dict:
    memory.update(kwargs)
    return save_memory(memory)