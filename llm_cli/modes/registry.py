"""Built-in modes loading and four-layer mode resolution."""

from __future__ import annotations

import importlib.resources

import json5

from llm_cli.config.models_schema import Model, ProvidersFile
from llm_cli.config.modes_schema import Mode
from llm_cli.resolve.deep_merge import deep_merge

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


def _get_mode_layers(
    providers_file: ProvidersFile,
    provider_name: str,
    model: Model,
) -> tuple[dict[str, Mode], dict[str, Mode], dict[str, Mode], dict[str, Mode]]:
    """Return (builtin, global, provider, model) mode dicts."""
    builtin_modes = load_builtin_modes()
    global_modes = providers_file.modes or {}
    provider_modes = (
        providers_file.providers[provider_name].modes or {}
        if provider_name in providers_file.providers
        else {}
    )
    model_modes = model.modes or {}
    return builtin_modes, global_modes, provider_modes, model_modes


def resolve_modes(
    providers_file: ProvidersFile,
    provider_name: str,
    model: Model,
) -> dict[str, Mode]:
    """Merge built-in → global → provider → model modes.

    For each mode name that appears in any layer, deep-merge across
    all four layers. Later layers win per key.
    """
    builtin_modes, global_modes, provider_modes, model_modes = _get_mode_layers(
        providers_file, provider_name, model
    )

    all_names = (
        set(builtin_modes)
        | set(global_modes)
        | set(provider_modes)
        | set(model_modes)
    )

    result: dict[str, Mode] = {}
    for name in all_names:
        merged: dict = {}
        for layer in (builtin_modes, global_modes, provider_modes, model_modes):
            mode = layer.get(name)
            if mode is not None:
                merged = deep_merge(merged, mode.model_dump(exclude_none=True))
        if merged:
            result[name] = Mode(**merged)

    return result


def get_mode_source(
    mode_name: str,
    providers_file: ProvidersFile,
    provider_name: str,
    model: Model,
) -> str:
    """Return the most-specific source layer for a mode."""
    builtin_modes, global_modes, provider_modes, model_modes = _get_mode_layers(
        providers_file, provider_name, model
    )
    for source, layer in [
        ("model", model_modes),
        ("provider", provider_modes),
        ("global", global_modes),
        ("builtin", builtin_modes),
    ]:
        if mode_name in layer:
            return source
    return "unknown"
