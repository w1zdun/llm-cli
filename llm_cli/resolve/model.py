"""Model selection by flag or default."""

from __future__ import annotations

import typer

from llm_cli.config.models_schema import Model, Provider, ProvidersFile


def select_model(
    providers_file: ProvidersFile,
    provider: Provider,
    flag: str | None = None,
) -> Model:
    """Select a model by id or name.

    Raises:
        SystemExit: On missing, unknown, or ambiguous model (exit code 1).
    """
    name = flag or providers_file.default_model
    available = ", ".join(m.name or m.id for m in provider.models)

    if name is None:
        typer.echo(
            f"error: --model is required (no default for provider "
            f"'{provider.base_url}')\navailable: {available}",
            err=True,
        )
        raise typer.Exit(1)

    for m in provider.models:
        if m.id == name or m.name == name:
            return m

    if flag is not None:
        matches = [
            f"{pname}/{(m.name or m.id)}"
            for pname, p in providers_file.providers.items()
            for m in p.models
            if m.id == name or m.name == name
        ]
        if matches:
            typer.echo(
                f"error: model '{name}' found under multiple providers:\n"
                f"  {', '.join(matches)}\n"
                f"use --provider to disambiguate",
                err=True,
            )
            raise typer.Exit(1)

    typer.echo(
        f"error: unknown model '{name}'\navailable: {available}",
        err=True,
    )
    raise typer.Exit(1)
