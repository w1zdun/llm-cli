"""Resolve sampling parameters through the four-layer stack."""

from __future__ import annotations

from typing import Any

import typer

from llm_cli.config.models_schema import Model, Provider
from llm_cli.config.modes_schema import Mode
from llm_cli.resolve.deep_merge import deep_merge


def resolve_sampling(
    provider: Provider,
    model: Model,
    mode: Mode,
    cli_overrides: dict[str, Any] | None = None,
    templates_map: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Merge sampling through provider → model → mode → CLI.

    Expands `sampling_template` references by deep-merging template params
    BELOW the layer where the reference appears (layer's explicit keys win).

    Args:
        provider: Provider definition.
        model: Model definition.
        mode: Mode definition.
        cli_overrides: CLI flag overrides (--temperature, --top-p, etc.).
        templates_map: Resolved templates (built-in + user).

    Returns:
        Resolved sampling dict.

    Raises:
        SystemExit: If a referenced template is unknown (exit code 1).
    """
    layers: list[dict[str, Any] | None] = [
        provider.sampling,
        model.sampling,
        mode.sampling,
        cli_overrides,
    ]

    result: dict[str, Any] = {}
    for layer in layers:
        if layer is None:
            continue

        # Check for sampling_template reference
        template_name = layer.get("sampling_template")
        layer_copy = dict(layer)
        if template_name is not None:
            layer_copy.pop("sampling_template", None)
            if templates_map is None or template_name not in templates_map:
                available = list(templates_map.keys()) if templates_map else []
                typer.echo(
                    f"error: unknown sampling template '{template_name}'"
                    f"{': available: ' + ', '.join(sorted(available)) if available else ''}",
                    err=True,
                )
                raise typer.Exit(1)
            # Expand template BELOW this layer (template values, then layer overrides)
            template_params = dict(templates_map[template_name])
            result = deep_merge(result, template_params)
            result = deep_merge(result, layer_copy)
        else:
            result = deep_merge(result, layer_copy)

    return result
