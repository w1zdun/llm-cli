"""JSONC read-and-parse helper wrapping json5."""

from pathlib import Path
from typing import Any


class JsoncError(Exception):
    """Error parsing a JSONC file."""

    def __init__(
        self, path: Path, message: str, line: int | None = None
    ) -> None:
        self.path = path
        self.line = line
        if line is not None:
            msg = f"parse error in {path}:{line}: {message}"
        else:
            msg = f"parse error in {path}: {message}"
        super().__init__(msg)


def read_jsonc(path: Path) -> Any:
    """Read and parse a JSONC file (JSON with comments and trailing commas).

    Args:
        path: Path to the JSONC file.

    Returns:
        Parsed Python object (dict, list, etc.).

    Raises:
        JsoncError: On file not found or parse failure.
    """
    if not path.exists():
        raise JsoncError(path, "file not found")

    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise JsoncError(path, str(exc)) from exc

    try:
        import json5

        return json5.loads(text)
    except ValueError as exc:
        msg = str(exc)
        line = None
        # Try to extract line number from error message
        for prefix in ("at line", "line", "line:", "at position"):
            if prefix in msg.lower():
                parts = msg.split(prefix, 1)
                if len(parts) > 1:
                    try:
                        line = int(parts[1].strip().split()[0])
                    except (ValueError, IndexError):
                        pass
                break
        raise JsoncError(path, msg, line) from exc
