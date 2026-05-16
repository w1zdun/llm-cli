"""Classify HTTP responses into exit codes."""

from __future__ import annotations

import httpx


def classify_error(exc: Exception) -> int:
    """Classify an exception into an exit code.

    Exit codes:
        1 — user error (4xx other than 401/403)
        3 — provider/transport error (401, 403, 5xx, network, timeout)

    Args:
        exc: The exception to classify.

    Returns:
        Exit code (1 or 3).
    """
    if isinstance(exc, httpx.HTTPStatusError):
        status = exc.response.status_code
        if status in (401, 403):
            return 3
        if 400 <= status < 500:
            return 1
        return 3

    if isinstance(exc, httpx.TimeoutException):
        return 3

    if isinstance(exc, httpx.ConnectError):
        return 3

    if isinstance(exc, httpx.NetworkError):
        return 3

    # Default to transport error
    return 3
