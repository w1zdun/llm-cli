"""Read image files — inline (base64) or path (file:// URL) modes."""

from __future__ import annotations

import base64
import mimetypes
import tempfile
from pathlib import Path

import typer

from llm_cli.inputs._tmp import register_tmp_file_cleanup
from llm_cli.inputs.image_preprocess import (
    ImagePreprocessing,
    preprocess_image_bytes,
)
from llm_cli.inputs.parser import IMAGE_EXTENSIONS

_EXT_BY_FORMAT = {"png": ".png", "jpeg": ".jpg"}


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


def _load_image(p: Path, cfg: ImagePreprocessing | None) -> tuple[bytes, str]:
    """Read image bytes, optionally preprocessing. Returns (data, mime)."""
    mime = mimetypes.guess_type(str(p))[0] or "application/octet-stream"
    data = p.read_bytes()
    if cfg is None or not cfg.enabled:
        return data, mime
    return preprocess_image_bytes(data, mime, cfg)


def image_entry_inline(
    path: str, image_preprocessing: ImagePreprocessing | None = None
) -> dict:
    """Read an image file and return base64 data-URL content entry."""
    p = _validate_image(path)
    data, mime = _load_image(p, image_preprocessing)
    b64 = base64.b64encode(data).decode("ascii")

    return {
        "type": "image_url",
        "image_url": {"url": f"data:{mime};base64,{b64}"},
    }


def image_entry_path(
    path: str, image_preprocessing: ImagePreprocessing | None = None
) -> dict:
    """Return a file:// URL content entry for an image."""
    p = _validate_image(path)

    if image_preprocessing is None or not image_preprocessing.enabled:
        return {
            "type": "image_url",
            "image_url": {"url": f"file://{p}"},
        }

    data, _mime = _load_image(p, image_preprocessing)
    ext = _EXT_BY_FORMAT[image_preprocessing.output_format]
    fd, tmp_path = tempfile.mkstemp(prefix="llm_img_", suffix=ext)
    try:
        with open(fd, "wb") as f:
            f.write(data)
    except Exception:
        Path(tmp_path).unlink(missing_ok=True)
        raise
    register_tmp_file_cleanup(tmp_path)
    return {
        "type": "image_url",
        "image_url": {"url": f"file://{tmp_path}"},
    }


def read_image_file(
    path: str,
    file_passing: str = "inline",
    image_preprocessing: ImagePreprocessing | None = None,
) -> dict:
    """Read an image file, dispatching to inline or path mode.

    Args:
        path: Path to the image file.
        file_passing: 'inline' for base64, 'path' for file:// URL.
        image_preprocessing: Optional preprocessing config; None or disabled
            passes raw bytes through unchanged.

    Returns:
        OpenAI-compatible vision content entry.
    """
    if file_passing == "path":
        return image_entry_path(path, image_preprocessing)
    return image_entry_inline(path, image_preprocessing)
