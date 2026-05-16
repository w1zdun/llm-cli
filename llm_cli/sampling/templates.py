"""Built-in sampling templates loading and user template merging."""

from __future__ import annotations

import importlib.resources
from typing import Any

import json5

from llm_cli.config.models_schema import ProvidersFile
from llm_cli.config.modes_schema import _SAMPLING_KEYS

_BUILTIN_DIR = "llm_cli.sampling.builtin"


def load_builtin_templates() -> dict[str, dict[str, Any]]:
    """Load built-in sampling templates from package data."""
    try:
        resources = importlib.resources.files(_BUILTIN_DIR)
    except ModuleNotFoundError:
        return {}

    templates: dict[str, dict[str, Any]] = {}
    for entry in resources.iterdir():
        if entry.is_file() and entry.name.endswith(".json"):
            name = entry.name[: -len(".json")]
            raw = json5.loads(entry.read_text(encoding="utf-8"))
            if isinstance(raw, dict):
                # Validate only sampling keys
                non_sampling = set(raw.keys()) - _SAMPLING_KEYS
                if non_sampling:
                    raise ValueError(
                        f"built-in template '{name}' contains non-sampling keys: "
                        f"{', '.join(sorted(non_sampling))}"
                    )
                templates[name] = raw
    return templates


def resolve_templates(
    providers_file: ProvidersFile,
) -> dict[str, dict[str, Any]]:
    """Merge built-in templates with user-declared templates.

    User templates (from providers_file.sampling_templates) fully replace
    built-ins on name collision.

    Args:
        providers_file: Loaded providers file.

    Returns:
        Dict mapping template names to sampling param dicts.

    Raises:
        ValueError: If a user template contains non-sampling keys.
    """
    builtin = load_builtin_templates()
    user_templates = providers_file.sampling_templates or {}

    # Validate user templates
    for name, data in user_templates.items():
        non_sampling = set(data.keys()) - _SAMPLING_KEYS
        if non_sampling:
            raise ValueError(
                f"sampling template '{name}' contains non-sampling keys: "
                f"{', '.join(sorted(non_sampling))}. "
                f"Only sampling keys are allowed in templates."
            )

    # User wins on name collision (full replacement)
    return {**builtin, **user_templates}
