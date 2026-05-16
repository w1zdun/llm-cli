"""Resolve schema from --schema flag or mode-bound schema."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import typer

from llm_cli.config.modes_schema import Mode


def resolve_schema(
    schema_path: str | None,
    mode: Mode,
) -> dict[str, Any] | None:
    """Resolve the schema to use.

    --schema flag takes precedence over mode-bound schema.

    Args:
        schema_path: Path from --schema flag (or None).
        mode: Resolved mode.

    Returns:
        Schema dict or None.

    Raises:
        SystemExit: On file not found or parse error (exit code 1).
    """
    # --schema flag takes precedence
    if schema_path:
        return _load_schema_file(schema_path)

    # Fall back to mode-bound schema
    if mode.output_schema is not None:
        return mode.output_schema

    return None


def _load_schema_file(path: str) -> dict[str, Any]:
    """Load and parse a JSON schema file.

    Args:
        path: Path to the JSON schema file.

    Returns:
        Parsed schema dict.

    Raises:
        SystemExit: On file not found or parse error (exit code 1).
    """
    import json

    p = Path(path)
    if not p.exists():
        typer.echo(f"error: schema file not found: {path}", err=True)
        raise typer.Exit(1)

    try:
        text = p.read_text(encoding="utf-8")
        schema = json.loads(text)
    except json.JSONDecodeError as exc:
        typer.echo(
            f"error: schema file {path} is not valid JSON: {exc}",
            err=True,
        )
        raise typer.Exit(1)
    except OSError as exc:
        typer.echo(f"error: could not read {path}: {exc}", err=True)
        raise typer.Exit(1)

    if not isinstance(schema, dict):
        typer.echo(
            f"error: schema file {path} must contain a JSON object", err=True
        )
        raise typer.Exit(1)

    return schema
