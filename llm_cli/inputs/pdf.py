"""PDF handling via PyMuPDF — text extraction and image rasterization."""

from __future__ import annotations

import base64
import tempfile
from pathlib import Path
from typing import Any

import fitz  # PyMuPDF

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


def read_pdf_images(
    path: str,
    max_pages: int = _MAX_PAGES_DEFAULT,
    dpi: int = 150,
    file_passing: str = "inline",
) -> list[dict[str, Any]]:
    """Rasterize PDF pages to images."""
    doc = _open_pdf(path, max_pages)
    zoom = dpi / 72
    mat = fitz.Matrix(zoom, zoom)
    entries: list[dict[str, Any]] = []

    if file_passing == "path":
        tmp_dir = tempfile.mkdtemp(prefix="llm_pdf_")
        for i, page in enumerate(doc):
            pix = page.get_pixmap(matrix=mat)
            png_path = Path(tmp_dir) / f"page_{i + 1}.png"
            pix.save(str(png_path))
            entries.append(
                {
                    "type": "image_url",
                    "image_url": {"url": f"file://{png_path}"},
                }
            )
        entries[0]["_temp_dir"] = tmp_dir
    else:
        for i, page in enumerate(doc):
            pix = page.get_pixmap(matrix=mat)
            b64 = base64.b64encode(pix.tobytes("png")).decode("ascii")
            entries.append(
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/png;base64,{b64}"},
                }
            )

    doc.close()
    return entries
