import json
from pathlib import Path


REGISTRY_PATH = Path("data/concepts/concept-registry.json")


def load_registry():
    """
    Load Wingman's concept registry.
    """

    if not REGISTRY_PATH.exists():
        return {}

    with open(REGISTRY_PATH, "r") as file:
        return json.load(file)


def save_registry(registry):
    """
    Save Wingman's concept registry.
    """

    REGISTRY_PATH.parent.mkdir(parents=True, exist_ok=True)

    with open(REGISTRY_PATH, "w") as file:
        json.dump(
            registry,
            file,
            indent=4,
        )