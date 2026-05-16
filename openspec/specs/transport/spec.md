## ADDED Requirements

### Requirement: OpenAI-compatible Chat Completions endpoint

The system SHALL send all generation requests as HTTP `POST` to `<provider.base_url>/chat/completions` with `Content-Type: application/json`. The request body SHALL conform to the OpenAI Chat Completions schema, with provider-specific extensions placed in `extra_body` and merged into the top-level body before sending.

#### Scenario: Request URL composed from base_url

- **WHEN** the resolved provider has `base_url = "http://localhost:8080/v1"`
- **THEN** the outgoing request goes to `http://localhost:8080/v1/chat/completions`

#### Scenario: extra_body flattened into top-level

- **WHEN** the resolved request has `extra_body = {guided_json: {...}, dry_multiplier: 0.8}`
- **THEN** the outgoing JSON body contains `guided_json` and `dry_multiplier` as top-level keys

### Requirement: Max-tokens field selection per provider compat

The system SHALL use the field name specified by `provider.compat.maxTokensField` for the maximum-tokens parameter, defaulting to `max_tokens` when the field is unset. The value SHALL be drawn from the resolved sampling stack key `max_tokens` (or from the resolved model's `max_tokens` if not overridden).

#### Scenario: Provider uses max_completion_tokens

- **WHEN** the provider declares `compat.maxTokensField = "max_completion_tokens"` and resolved `max_tokens = 4096`
- **THEN** the outgoing body contains `max_completion_tokens: 4096` and no `max_tokens` field

### Requirement: Timeouts

The system SHALL apply a connect timeout of 10 seconds and a read timeout of 600 seconds by default. The user MAY override these via `--connect-timeout <s>` and `--read-timeout <s>` flags on `run`.

#### Scenario: Read timeout exceeded

- **WHEN** a request takes longer than the read timeout
- **THEN** the system writes "read timeout after <s>s" to stderr and exits with code 3

### Requirement: Error classification

The system SHALL classify provider failures into exit codes as follows:
- HTTP 4xx other than 401/403 → exit `1` (treated as user error — bad request, bad arguments).
- HTTP 401, 403, 5xx, network failure, or timeout → exit `3` (treated as provider/transport error).

Each failure SHALL include the HTTP status and provider's response body (or transport error message) on stderr.

#### Scenario: HTTP 400 surfaced as user error

- **WHEN** the provider returns HTTP 400 with body "unknown parameter: temperture"
- **THEN** the system writes the status and body to stderr and exits with code 1

#### Scenario: HTTP 401 surfaced as transport error

- **WHEN** the provider returns HTTP 401
- **THEN** the system writes the status and body to stderr and exits with code 3

#### Scenario: Connection refused surfaced as transport error

- **WHEN** the configured provider is not running and the connection is refused
- **THEN** the system writes the connection error to stderr and exits with code 3

### Requirement: No streaming at v1

The system SHALL set `stream = false` (or omit `stream`) on every chat completions request. The system SHALL ignore any `stream` setting in modes or `--set` flags at v1.

#### Scenario: Stream true in mode is ignored

- **WHEN** a mode sets `sampling.stream = true`
- **THEN** the outgoing request still sends `stream = false` (or omits it)

### Requirement: Response shape parsing

The system SHALL extract the assistant response from `response.choices[0].message.content`. If `choices` is empty or `message.content` is missing, the system SHALL exit with code 3 and write the full raw response to stderr.

#### Scenario: Standard response parsed

- **WHEN** the provider returns `{"choices": [{"message": {"content": "hello"}}]}`
- **THEN** the system extracts `"hello"` as the assistant's content

#### Scenario: Missing content is a transport error

- **WHEN** the provider returns `{"choices": []}`
- **THEN** the system writes "unexpected response shape" and the raw body to stderr and exits with code 3
