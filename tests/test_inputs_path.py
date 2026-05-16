"""Tests for file-by-path image input."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from llm_cli.inputs.image import image_entry_inline, image_entry_path


def _create_test_png() -> str:
    """Create a minimal PNG file."""
    import base64

    # Minimal valid PNG (1x1 red pixel)
    png_data = base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8B"
        "QDwADhQGfQX/1WAAAAABJRU5ErkJggg=="
    )
    tmp = Path(tempfile.mktemp(suffix=".png"))
    tmp.write_bytes(png_data)
    return str(tmp)


class TestImageEntryInline:
    def test_inline_returns_data_url(self):
        path = _create_test_png()
        try:
            entry = image_entry_inline(path)
            assert entry["type"] == "image_url"
            url = entry["image_url"]["url"]
            assert url.startswith("data:")
            assert "base64" in url
        finally:
            Path(path).unlink()

    def test_inline_missing_file(self):
        import click

        with pytest.raises(click.exceptions.Exit) as exc_info:
            image_entry_inline("/nonexistent/file.png")
        assert exc_info.value.exit_code == 1


class TestImageEntryPath:
    def test_path_returns_file_url(self):
        path = _create_test_png()
        try:
            entry = image_entry_path(path)
            assert entry["type"] == "image_url"
            url = entry["image_url"]["url"]
            assert url.startswith("file:///")
        finally:
            Path(path).unlink()

    def test_path_missing_file(self):
        import click

        with pytest.raises(click.exceptions.Exit) as exc_info:
            image_entry_path("/nonexistent/file.png")
        assert exc_info.value.exit_code == 1

    def test_path_resolves_absolute(self):
        path = _create_test_png()
        try:
            entry = image_entry_path(path)
            url = entry["image_url"]["url"]
            # Should be absolute path
            assert url[8:] != path  # after "file://"
        finally:
            Path(path).unlink()
