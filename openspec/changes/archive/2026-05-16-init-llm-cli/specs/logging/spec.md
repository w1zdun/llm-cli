## ADDED Requirements

### Requirement: Diagnostics on stderr

After a `run` completes (successfully or with an error), the system SHALL write a single-line diagnostic record to stderr containing at minimum: provider name, model id, mode name, latency in milliseconds, prompt token count (if provider reports it), completion token count (if provider reports it), run-id (UUIDv4), and the run-log file path. The diagnostic line SHALL be suppressed when `--quiet` is passed; error messages SHALL still be written under `--quiet`.

#### Scenario: Diagnostic line printed on success

- **WHEN** a `run` completes successfully
- **THEN** stderr contains one line of the form `provider=<p> model=<m> mode=<n> latency=<L>ms tokens=<P>/<C> run=<uuid> log=<path>`

#### Scenario: --quiet suppresses diagnostics

- **WHEN** the user passes `--quiet` and the run succeeds
- **THEN** stderr is empty

#### Scenario: --quiet does not suppress errors

- **WHEN** the user passes `--quiet` and the provider returns HTTP 500
- **THEN** the error message still appears on stderr and exit code is 3

### Requirement: JSONL run log file

The system SHALL append exactly one JSON object per `run` invocation to `${XDG_DATA_HOME:-~/.local/share}/llm-cli/runs.jsonl`. The directory SHALL be created on first use with mode `0700`. The system SHALL NOT rotate the file at v1.

#### Scenario: Run log directory created on first use

- **WHEN** the system runs and the data directory does not exist
- **THEN** the system creates `~/.local/share/llm-cli/` with mode `0700`

#### Scenario: One JSON line per run

- **WHEN** the user runs two `llm-cli run` invocations
- **THEN** `runs.jsonl` contains exactly two new lines, each parseable as JSON independently

### Requirement: Run log record fields

Each run log record SHALL contain the keys:
- `ts` — ISO 8601 UTC timestamp with timezone suffix `Z`.
- `run_id` — UUIDv4 string matching the diagnostic line.
- `provider` — provider name.
- `model` — model id.
- `mode` — mode name.
- `resolved_request` — the full POST body sent to the provider.
- `resolved_headers` — request headers with the value of `Authorization` redacted as `"Bearer ***"`.
- `response_status` — HTTP status code received, or `null` on transport failure.
- `response` — the full provider response JSON, or `null` on transport failure.
- `latency_ms` — total time from request start to response end (or to failure), as integer milliseconds.
- `exit_code` — final exit code (`0|1|2|3`).
- `error` — optional string; present only when `exit_code != 0`.

#### Scenario: Authorization header redacted in log

- **WHEN** a request is made with `api_key = "ollama"`
- **THEN** the log record's `resolved_headers.Authorization` is exactly `"Bearer ***"` and never contains the literal key

#### Scenario: Transport failure still logged

- **WHEN** the provider connection is refused
- **THEN** a log record is appended with `response_status = null`, `response = null`, `exit_code = 3`, and `error` set to the connection error message

#### Scenario: Schema validation failure logged with raw response

- **WHEN** the assistant returns text that fails schema validation
- **THEN** the log record contains the full provider `response` object and `exit_code = 2`

### Requirement: Run-id consistency

The `run_id` field in the log record SHALL match the `run=<uuid>` field in the stderr diagnostic line for the same invocation. The system SHALL generate the UUIDv4 once at the start of `run` and reuse it for both outputs.

#### Scenario: Run-id appears in stderr and log

- **WHEN** a `run` produces both stderr diagnostics and a log entry
- **THEN** the UUID in stderr matches the `run_id` field in the corresponding log line
