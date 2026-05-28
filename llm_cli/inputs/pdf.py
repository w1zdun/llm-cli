"""PDF handling via PyMuPDF — text extraction and image rasterization."""

from __future__ import annotations

import base64
import tempfile
from pathlib import Path
from typing import Any

import fitz  # PyMuPDF

from llm_cli.inputs._tmp import register_tmp_dir_cleanup
from llm_cli.inputs.image_preprocess import (
    ImagePreprocessing,
    preprocess_image_bytes,
)

_MAX_PAGES_DEFAULT = 25


def _open_pdf(path: str, max_pages: int) -> fitz.Document:
    """Open a PDF and validate page count.

    Returns:
        Opened fitz.Document.

    Raises:
        typer.Exit: On missing file or page limit exceeded (exit code 1).
    """
    import typer

    p = Path(path)
    if not p.exists():
        typer.echo(f"error: input not found: {path}", err=True)
        raise typer.Exit(1)

    try:
        doc = fitz.open(str(p))
    except Exception as exc:
        typer.echo(f"error: could not open {path}: {exc}", err=True)
        raise typer.Exit(1)

    if len(doc) > max_pages:
        typer.echo(
            f"error: PDF has {len(doc)} pages, exceeds --max-pages {max_pages}",
            err=True,
        )
        doc.close()
        raise typer.Exit(1)

    if len(doc) == 0:
        typer.echo(f"error: PDF {path} has no pages", err=True)
        doc.close()
        raise typer.Exit(1)

    return doc


def read_pdf_text(
    path: str,
    max_pages: int = _MAX_PAGES_DEFAULT,
) -> str:
    """Extract text from a PDF."""
    p = Path(path)
    doc = _open_pdf(path, max_pages)

    parts: list[str] = []
    for i, page in enumerate(doc):
        text = page.get_text()
        parts.append(f"=== {p.name} page {i + 1} ===\n{text}")

    doc.close()
    return "\n\n".join(parts)


_EXT_BY_FORMAT = {"png": ".png", "jpeg": ".jpg"}


def read_pdf_images(
    path: str,
    max_pages: int = _MAX_PAGES_DEFAULT,
    dpi: int = 150,
    file_passing: str = "inline",
    image_preprocessing: ImagePreprocessing | None = None,
) -> list[dict[str, Any]]:
    """Rasterize PDF pages to images, optionally running preprocessing."""
    doc = _open_pdf(path, max_pages)
    zoom = dpi / 72
    mat = fitz.Matrix(zoom, zoom)
    entries: list[dict[str, Any]] = []
    use_preproc = (
        image_preprocessing is not None and image_preprocessing.enabled
    )
    out_ext = (
        _EXT_BY_FORMAT[image_preprocessing.output_format]
        if use_preproc
        else ".png"
    )

    if file_passing == "path":
        tmp_dir = tempfile.mkdtemp(prefix="llm_pdf_")
        register_tmp_dir_cleanup(tmp_dir)
        for i, page in enumerate(doc):
            pix = page.get_pixmap(matrix=mat)
            page_path = Path(tmp_dir) / f"page_{i + 1}{out_ext}"
            if use_preproc:
                processed, _mime = preprocess_image_bytes(
                    pix.tobytes("png"), "image/png", image_preprocessing
                )
                page_path.write_bytes(processed)
            else:
                pix.save(str(page_path))
            entries.append(
                {
                    "type": "image_url",
                    "image_url": {"url": f"file://{page_path}"},
                }
            )
    else:
        for i, page in enumerate(doc):
            pix = page.get_pixmap(matrix=mat)
            raw = pix.tobytes("png")
            if use_preproc:
                payload, mime = preprocess_image_bytes(
                    raw, "image/png", image_preprocessing
                )
            else:
                payload, mime = raw, "image/png"
            b64 = base64.b64encode(payload).decode("ascii")
            entries.append(
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:{mime};base64,{b64}"},
                }
            )

    doc.close()
    return entries
