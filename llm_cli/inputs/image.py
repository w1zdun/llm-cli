"""Read image files — inline (base64) or path (file:// URL) modes."""

from __future__ import annotations

import base64
import mimetypes
from pathlib import Path

import typer

from llm_cli.inputs.parser import IMAGE_EXTENSIONS


def _validate_image(path: str) -> Path:
    """Validate image file exists and has supported extension.

    Returns:
        Resolved Path.

    Raises:
        typer.Exit: On missing file or unsupported format (exit code 1).
    """
    p = Path(path).resolve()
    if not p.exists():
        typer.echo(f"error: input not found: {path}", err=True)
        raise typer.Exit(1)

    if p.suffix.lower() not in IMAGE_EXTENSIONS:
        typer.echo(
            f"error: {path} has unsupported extension '{p.suffix}' for image input",
            err=True,
        )
        raise typer.Exit(1)

    return p


def image_entry_inline(path: str) -> dict:
    """Read an image file and return base64 data-URL content entry."""
    p = _validate_image(path)
    mime = mimetypes.guess_type(str(p))[0] or "application/octet-stream"
    b64 = base64.b64encode(p.read_bytes()).decode("ascii")

    return {
        "type": "image_url",
        "image_url": {"url": f"data:{mime};base64,{b64}"},
    }


def image_entry_path(path: str) -> dict:
    """Return a file:// URL content entry for an image."""
    p = _validate_image(path)
    return {
        "type": "image_url",
        "image_url": {"url": f"file://{p}"},
    }


def read_image_file(path: str, file_passing: str = "inline") -> dict:
    """Read an image file, dispatching to inline or path mode.

    Args:
        path: Path to the image file.
        file_passing: 'inline' for base64, 'path' for file:// URL.

    Returns:
        OpenAI-compatible vision content entry.
    """
    if file_passing == "path":
        return image_entry_path(path)
    return image_entry_inline(path)
