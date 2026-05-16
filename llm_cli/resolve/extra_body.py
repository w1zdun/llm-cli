"""Resolve extra_body through the four-layer stack."""

from __future__ import annotations

from typing import Any

from llm_cli.config.models_schema import Model, Provider
from llm_cli.config.modes_schema import Mode
from llm_cli.resolve.deep_merge import deep_merge


def resolve_extra_body(
    provider: Provider,
    model: Model,
    mode: Mode,
    cli_overrides: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Merge extra_body through provider → model → mode → CLI.

    Args:
        provider: Provider definition.
        model: Model definition.
        mode: Mode definition.
        cli_overrides: CLI --set overrides.

    Returns:
        Resolved extra_body dict.
    """
    layers = [
        provider.extra_body,
        model.extra_body,
        mode.extra_body,
        cli_overrides,
    ]

    result: dict[str, Any] = {}
    for layer in layers:
        result = deep_merge(result, layer)
    return result
