"""JSONL run log writer."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from llm_cli.config.paths import ensure_data_dir, runs_log_path


def _redact_headers(headers: dict[str, str]) -> dict[str, str]:
    """Redact Authorization header values."""
    result = dict(headers)
    if "Authorization" in result:
        result["Authorization"] = "Bearer ***"
    return result


def write_run_log(
    run_id: str,
    provider_name: str,
    model_id: str,
    mode_name: str,
    resolved_request: dict[str, Any],
    resolved_headers: dict[str, str],
    response_status: int | None,
    response: Any,
    latency_ms: int,
    exit_code: int,
    error: str | None = None,
) -> None:
    """Append a JSONL record to the run log.

    Args:
        run_id: UUIDv4 for this run.
        provider_name: Provider name.
        model_id: Model id.
        mode_name: Mode name.
        resolved_request: Full POST body sent.
        resolved_headers: Request headers.
        response_status: HTTP status code (or None).
        response: Full provider response (or None).
        latency_ms: Total latency in milliseconds.
        exit_code: Final exit code.
        error: Error message (optional).
    """
    ensure_data_dir()

    now = datetime.now(timezone.utc)
    record: dict[str, Any] = {
        "ts": now.strftime("%Y-%m-%dT%H:%M:%S.") + now.strftime("%f")[:3] + "Z",
        "run_id": run_id,
        "provider": provider_name,
        "model": model_id,
        "mode": mode_name,
        "resolved_request": resolved_request,
        "resolved_headers": _redact_headers(resolved_headers),
        "response_status": response_status,
        "response": response,
        "latency_ms": latency_ms,
        "exit_code": exit_code,
    }
    if error:
        record["error"] = error

    log_path = runs_log_path()
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")
