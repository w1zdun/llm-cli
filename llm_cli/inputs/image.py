"""Read image files and encode as data URLs."""

from __future__ import annotations

import base64
import mimetypes
from pathlib import Path

import typer

from llm_cli.inputs.parser import IMAGE_EXTENSIONS


def read_image_file(path: str) -> dict:
    """Read an image file and return OpenAI-compatible vision content entry.

    Raises:
        SystemExit: On missing file or unsupported format (exit code 1).
    """
    p = Path(path)
    if not p.exists():
        typer.echo(f"error: input not found: {path}", err=True)
        raise typer.Exit(1)

    ext = p.suffix.lower()
    if ext not in IMAGE_EXTENSIONS:
        typer.echo(
            f"error: {path} has unsupported extension '{ext}' for image input",
            err=True,
        )
        raise typer.Exit(1)

    mime = mimetypes.guess_type(path)[0] or "application/octet-stream"
    b64 = base64.b64encode(p.read_bytes()).decode("ascii")

    return {
        "type": "image_url",
        "image_url": {"url": f"data:{mime};base64,{b64}"},
    }
