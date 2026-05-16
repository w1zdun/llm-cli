"""Per-key deep-merge for nested dicts (last writer wins per key)."""

from __future__ import annotations

from typing import Any


def deep_merge(
    base: dict[str, Any] | None, override: dict[str, Any] | None
) -> dict[str, Any]:
    """Deep-merge two dicts. Override wins per key.

    - If both values are dicts, recurse.
    - Otherwise, override replaces base.

    Args:
        base: Base dict (may be None).
        override: Override dict (may be None).

    Returns:
        Merged dict.
    """
    if not base:
        return dict(override) if override else {}
    if not override:
        return dict(base)

    result = dict(base)
    for key, val in override.items():
        if (
            key in result
            and isinstance(result[key], dict)
            and isinstance(val, dict)
        ):
            result[key] = deep_merge(result[key], val)
        else:
            result[key] = val
    return result
