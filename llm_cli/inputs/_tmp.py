"""Temporary file/dir helpers for inputs pipeline."""

from __future__ import annotations

import atexit
import os
import shutil


def register_tmp_dir_cleanup(path: str) -> None:
    """Schedule removal of a temp directory at process exit."""

    def _cleanup() -> None:
        shutil.rmtree(path, ignore_errors=True)

    atexit.register(_cleanup)


def register_tmp_file_cleanup(path: str) -> None:
    """Schedule removal of a temp file at process exit."""

    def _cleanup() -> None:
        try:
            os.unlink(path)
        except OSError:
            pass

    atexit.register(_cleanup)
