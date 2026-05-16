"""Built-in modes loading and user mode merging."""

import importlib.resources

import json5

from llm_cli.config.modes_schema import Mode

_BUILTIN_DIR = "llm_cli.modes.builtin"


def load_builtin_modes() -> dict[str, Mode]:
    """Load built-in modes from package data."""
    try:
        resources = importlib.resources.files(_BUILTIN_DIR)
    except ModuleNotFoundError:
        return {}

    modes: dict[str, Mode] = {}
    for entry in resources.iterdir():
        if entry.is_file() and entry.name.endswith(".json"):
            name = entry.name[: -len(".json")]
            raw = json5.loads(entry.read_text(encoding="utf-8"))
            if isinstance(raw, dict):
                modes[name] = Mode(**raw)
    return modes


def resolve_modes(user_modes: dict[str, Mode]) -> dict[str, Mode]:
    """Merge built-in modes with user-defined modes (user wins)."""
    return {**load_builtin_modes(), **user_modes}


def get_mode_source(mode_name: str, user_modes: dict[str, Mode]) -> str:
    """Return 'user' if user-defined, otherwise 'builtin'."""
    return "user" if mode_name in user_modes else "builtin"
