"""Resolve sampling parameters through the four-layer stack."""

from __future__ import annotations

from typing import Any

import typer

from llm_cli.config.models_schema import Model, Provider
from llm_cli.config.modes_schema import Mode
from llm_cli.resolve.deep_merge import deep_merge


def _expand_template(
    template_name: str,
    templates_map: dict[str, dict[str, Any]] | None,
    visited: set[str],
) -> dict[str, Any]:
    """Resolve a template, recursing through nested sampling_template refs.

    The referenced template wins over its own template reference, mirroring
    how a layer's explicit keys win over the template it references.
    """
    if templates_map is None or template_name not in templates_map:
        available = list(templates_map.keys()) if templates_map else []
        typer.echo(
            f"error: unknown sampling template '{template_name}'"
            f"{': available: ' + ', '.join(sorted(available)) if available else ''}",
            err=True,
        )
        raise typer.Exit(1)
    if template_name in visited:
        cycle = " → ".join([*visited, template_name])
        typer.echo(
            f"error: cycle in sampling_template references: {cycle}",
            err=True,
        )
        raise typer.Exit(1)

    template = dict(templates_map[template_name])
    nested = template.pop("sampling_template", None)
    if nested is None:
        return template
    base = _expand_template(nested, templates_map, visited | {template_name})
    return deep_merge(base, template)


def resolve_sampling(
    provider: Provider,
    model: Model,
    mode: Mode,
    cli_overrides: dict[str, Any] | None = None,
    templates_map: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Merge sampling through provider → model → mode → CLI.

    Expands `sampling_template` references by deep-merging template params
    UNDER the running result (template fills gaps left by lower-priority
    layers), and then merging the layer's explicit keys ON TOP (layer wins
    over its own template).

    Args:
        provider: Provider definition.
        model: Model definition.
        mode: Mode definition.
        cli_overrides: CLI flag overrides (--temperature, --top-p, etc.).
        templates_map: Resolved templates (built-in + user).

    Returns:
        Resolved sampling dict.

    Raises:
        SystemExit: If a referenced template is unknown or self-referential
            (exit code 1).
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

        layer_copy = dict(layer)
        template_name = layer_copy.pop("sampling_template", None)
        if template_name is not None:
            template_params = _expand_template(
                template_name, templates_map, set()
            )
            # Template fills gaps the running result didn't supply;
            # then layer keys override both.
            result = deep_merge(template_params, result)
            result = deep_merge(result, layer_copy)
        else:
            result = deep_merge(result, layer_copy)

    return result
