"""Provider selection by flag or default."""

from __future__ import annotations

import typer

from llm_cli.config.models_schema import Provider, ProvidersFile


def select_provider(
    providers_file: ProvidersFile,
    flag: str | None = None,
) -> tuple[str, Provider]:
    """Select a provider by name.

    Raises:
        SystemExit: On missing or unknown provider (exit code 1).
    """
    name = flag or providers_file.default_provider
    available = ", ".join(sorted(providers_file.providers.keys()))

    if name is None:
        typer.echo(
            f"error: --provider is required (no default set)\n"
            f"available: {available}",
            err=True,
        )
        raise typer.Exit(1)

    if name not in providers_file.providers:
        typer.echo(
            f"error: unknown provider '{name}'\navailable: {available}",
            err=True,
        )
        raise typer.Exit(1)

    return name, providers_file.providers[name]
