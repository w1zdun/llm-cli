"""Token budget estimation for input messages."""

from __future__ import annotations

import json
import math
from typing import Any


def estimate_tokens(messages: list[dict[str, Any]]) -> int:
    """Rough heuristic estimate of input token count.

    Text: ceil(len(serialized_text) / 4).
    Image: 1024 tokens per image entry.

    Args:
        messages: Chat messages array.

    Returns:
        Estimated token count.
    """
    total = 0
    for msg in messages:
        content = msg.get("content", "")
        if isinstance(content, str):
            total += max(math.ceil(len(content) / 4), 1)
        elif isinstance(content, list):
            for part in content:
                part_type = part.get("type", "")
                if part_type == "text":
                    text = part.get("text", "")
                    total += max(math.ceil(len(text) / 4), 1)
                elif part_type == "image_url":
                    total += 1024
                else:
                    # Serialize the part as fallback
                    total += max(math.ceil(len(json.dumps(part)) / 4), 1)

        # Role overhead
        total += 2

    return total
