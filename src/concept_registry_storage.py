# Loads and saves Wingman's persistent concept registry.

import json
from pathlib import Path


REGISTRY_PATH = Path(
    "data/concepts/concept-registry.json"
)


def load_registry():
    """
    Load Wingman's concept registry.
    """
    if not REGISTRY_PATH.exists():
        return {}

    with REGISTRY_PATH.open(
        "r",
        encoding="utf-8",
    ) as file:
        return json.load(file)


def save_registry(registry):
    """
    Save the concept registry using an atomic replacement.
    """
    REGISTRY_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    temporary_path = Path(
        f"{REGISTRY_PATH}.tmp"
    )

    with temporary_path.open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            registry,
            file,
            indent=4,
        )

    temporary_path.replace(
        REGISTRY_PATH
    )