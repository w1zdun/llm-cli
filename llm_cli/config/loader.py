"""Config file loading with typed errors."""

from __future__ import annotations

from pathlib import Path
from typing import Callable, TypeVar

import typer
from pydantic import ValidationError

from llm_cli.config.jsonc import JsoncError, read_jsonc
from llm_cli.config.models_schema import ProvidersFile

from llm_cli.config.paths import config_path

T = TypeVar("T")


def _read_config(path: Path, label: str, parser: Callable[[dict], T]) -> T:
    try:
        raw = read_jsonc(path)
    except JsoncError as exc:
        typer.echo(f"error: {exc}", err=True)
        raise typer.Exit(1) from exc

    if not isinstance(raw, dict):
        typer.echo(f"error: {path} must contain a JSON object", err=True)
        raise typer.Exit(1)

    try:
        return parser(raw)
    except ValidationError as exc:
        typer.echo(f"error: invalid {label}: {exc}", err=True)
        raise typer.Exit(1) from exc


def load_models() -> ProvidersFile:
    """Load and validate models.json. Missing file is a hard error."""
    path = config_path("models.json")
    if not path.exists():
        typer.echo(
            f"error: models.json not found at {path}\n"
            "Create it with provider definitions first.",
            err=True,
        )
        raise typer.Exit(1)

    return _read_config(path, "models.json", lambda raw: ProvidersFile(**raw))
