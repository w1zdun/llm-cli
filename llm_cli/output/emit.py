"""Emit result to stdout (JSON or raw text)."""

from __future__ import annotations

import json
import sys
from typing import Any


def emit_result(
    content: Any,
    is_json: bool = False,
    compact: bool = False,
) -> None:
    """Emit the result to stdout.

    Args:
        content: Content to emit (string or parsed JSON object).
        is_json: If True, emit as JSON.
        compact: If True and is_json, use compact JSON (no whitespace).
    """
    if is_json:
        if compact:
            sys.stdout.write(json.dumps(content, separators=(",", ":")))
        else:
            json.dump(content, sys.stdout, indent=2, ensure_ascii=False)
        sys.stdout.write("\n")
    else:
        sys.stdout.write(str(content))
        if not str(content).endswith("\n"):
            sys.stdout.write("\n")
