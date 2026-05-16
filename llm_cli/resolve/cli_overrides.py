"""Parse --set key=value flags into nested dicts."""

from __future__ import annotations

from typing import Any


def _expand_dotted_key(result: dict[str, Any], key: str, value: Any) -> None:
    """Expand a dotted key into nested dicts.

    Example: 'chat_template_kwargs.enable_thinking' with value True
    produces {'chat_template_kwargs': {'enable_thinking': True}}
    """
    parts = key.split(".")
    current = result
    for part in parts[:-1]:
        if part not in current or not isinstance(current[part], dict):
            current[part] = {}
        current = current[part]
    current[parts[-1]] = value


def _try_json_decode(value: str) -> Any:
    """Try to parse value as JSON, fall back to string."""
    import json

    try:
        return json.loads(value)
    except (json.JSONDecodeError, ValueError):
        return value


def parse_set_flags(flags: list[str]) -> dict[str, Any]:
    """Parse --set key=value flags.

    Args:
        flags: List of "key=value" strings.

    Returns:
        Nested dict with expanded dotted keys.
    """
    result: dict[str, Any] = {}
    for flag in flags:
        if "=" not in flag:
            continue
        key, _, value = flag.partition("=")
        parsed = _try_json_decode(value)
        _expand_dotted_key(result, key, parsed)
    return result
