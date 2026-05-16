"""Format one-line stderr diagnostic."""

from __future__ import annotations

from llm_cli.config.paths import runs_log_path


def format_diagnostics(
    provider: str,
    model: str,
    mode: str,
    latency_ms: int,
    prompt_tokens: int | None = None,
    completion_tokens: int | None = None,
    run_id: str | None = None,
) -> str:
    """Format a one-line diagnostic record.

    Args:
        provider: Provider name.
        model: Model id.
        mode: Mode name.
        latency_ms: Latency in milliseconds.
        prompt_tokens: Prompt token count (optional).
        completion_tokens: Completion token count (optional).
        run_id: Run UUID (optional).

    Returns:
        Formatted diagnostic string.
    """
    tokens = "unknown"
    if prompt_tokens is not None and completion_tokens is not None:
        tokens = f"{prompt_tokens}/{completion_tokens}"
    elif prompt_tokens is not None:
        tokens = f"{prompt_tokens}/?"

    parts = [
        f"provider={provider}",
        f"model={model}",
        f"mode={mode}",
        f"latency={latency_ms}ms",
        f"tokens={tokens}",
    ]
    if run_id:
        parts.append(f"run={run_id}")
    parts.append(f"log={runs_log_path()}")

    return " ".join(parts)
