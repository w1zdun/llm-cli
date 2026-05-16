"""PDF handling via PyMuPDF — text extraction and image rasterization."""

from __future__ import annotations

import base64
from pathlib import Path

_MAX_PAGES_DEFAULT = 25


def read_pdf_text(
    path: str,
    max_pages: int = _MAX_PAGES_DEFAULT,
) -> str:
    """Extract text from a PDF.

    Args:
        path: Path to the PDF file.
        max_pages: Maximum pages to process.

    Returns:
        Text content with per-page headers.

    Raises:
        SystemExit: On missing file or page limit exceeded (exit code 1).
    """
    import typer

    import fitz  # PyMuPDF

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

    parts: list[str] = []
    for i, page in enumerate(doc):
        text = page.get_text()
        header = f"=== {p.name} page {i + 1} ==="
        parts.append(f"{header}\n{text}")

    doc.close()
    return "\n\n".join(parts)


def read_pdf_images(
    path: str,
    max_pages: int = _MAX_PAGES_DEFAULT,
    dpi: int = 150,
) -> list[dict]:
    """Rasterize PDF pages to images.

    Args:
        path: Path to the PDF file.
        max_pages: Maximum pages to process.
        dpi: Rasterization DPI.

    Returns:
        List of image_url content entries.

    Raises:
        SystemExit: On missing file or page limit exceeded (exit code 1).
    """
    import typer

    import fitz  # PyMuPDF

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

    entries: list[dict] = []
    zoom = dpi / 72
    mat = fitz.Matrix(zoom, zoom)

    for i, page in enumerate(doc):
        pix = page.get_pixmap(matrix=mat)
        png_data = pix.tobytes("png")
        b64 = base64.b64encode(png_data).decode("ascii")
        data_url = f"data:image/png;base64,{b64}"
        entries.append(
            {
                "type": "image_url",
                "image_url": {"url": data_url},
            }
        )

    doc.close()
    return entries
