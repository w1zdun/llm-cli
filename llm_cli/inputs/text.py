"""Read text files with extension whitelist."""

from __future__ import annotations

from pathlib import Path

import typer

from llm_cli.inputs.parser import TEXT_EXTENSIONS


def read_text_file(path: str) -> str:
    """Read a text file and format with header.

    Args:
        path: Path to the text file.

    Returns:
        Formatted string: '=== <basename> ===\n<content>'

    Raises:
        SystemExit: On missing file or non-UTF-8 content (exit code 1).
    """
    p = Path(path)
    if not p.exists():
        typer.echo(f"error: input not found: {path}", err=True)
        raise typer.Exit(1)

    ext = p.suffix.lower()
    if ext not in TEXT_EXTENSIONS:
        typer.echo(
            f"error: {path} has unsupported extension '{ext}' for text input",
            err=True,
        )
        raise typer.Exit(1)

    try:
        content = p.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        typer.echo(
            f"error: could not decode {path} as UTF-8",
            err=True,
        )
        raise typer.Exit(1)

    return f"=== {p.name} ===\n{content}"
