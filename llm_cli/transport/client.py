"""HTTP client with configurable timeouts."""

from __future__ import annotations

import httpx

from llm_cli.config.models_schema import Provider

_DEFAULT_CONNECT_TIMEOUT = 10.0
_DEFAULT_READ_TIMEOUT = 600.0


def create_client(
    provider: Provider,
    connect_timeout: float = _DEFAULT_CONNECT_TIMEOUT,
    read_timeout: float = _DEFAULT_READ_TIMEOUT,
) -> httpx.Client:
    """Create an httpx.Client configured for the provider.

    Args:
        provider: Provider definition.
        connect_timeout: Connect timeout in seconds.
        read_timeout: Read timeout in seconds.

    Returns:
        Configured httpx.Client.
    """
    headers = {"Content-Type": "application/json"}

    if provider.api_key:
        headers["Authorization"] = f"Bearer {provider.api_key}"

    return httpx.Client(
        timeout=httpx.Timeout(
            connect=connect_timeout,
            read=read_timeout,
            write=60.0,
            pool=10.0,
        ),
        headers=headers,
    )
