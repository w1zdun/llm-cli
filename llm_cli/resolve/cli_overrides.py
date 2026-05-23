"""Parse --set key=value flags into sampling vs extra_body overrides."""

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


def parse_set_flags(
    flags: list[str],
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Parse --set key=value flags.

    Routes by dotted-ness: flat keys (no '.') become sampling overrides;
    dotted keys (e.g. 'chat_template_kwargs.enable_thinking') become
    nested extra_body overrides.

    Args:
        flags: List of "key=value" strings.

    Returns:
        Tuple of (sampling_overrides, extra_body_overrides).
    """
    sampling: dict[str, Any] = {}
    extra_body: dict[str, Any] = {}
    for flag in flags:
        if "=" not in flag:
            continue
        key, _, value = flag.partition("=")
        parsed = _try_json_decode(value)
        if "." in key:
            _expand_dotted_key(extra_body, key, parsed)
        else:
            sampling[key] = parsed
    return sampling, extra_body
