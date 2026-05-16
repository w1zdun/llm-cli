## ADDED Requirements

### Requirement: Schema sources and precedence

The system SHALL accept a JSON Schema from either:
1. A `--schema <path>` CLI flag pointing to a `.json` file containing a JSON Schema document.
2. A `schema` field on the resolved mode.

If both are present, `--schema` SHALL take precedence and the mode's schema SHALL be ignored.

#### Scenario: --schema overrides mode-bound schema

- **WHEN** the user invokes a mode with `schema = {A}` and passes `--schema fileB.json` containing `{B}`
- **THEN** the system uses schema `{B}` and ignores `{A}`

#### Scenario: Schema file not found is a hard error

- **WHEN** the user passes `--schema /path/does-not-exist.json`
- **THEN** the system writes "schema file not found" to stderr and exits with code 1

#### Scenario: Schema file malformed JSON is a hard error

- **WHEN** the `--schema` file is not valid JSON
- **THEN** the system writes a parse error including line number to stderr and exits with code 1

### Requirement: Schema-present triggers JSON output

When any schema source is active, the system SHALL emit the assistant's response on stdout as JSON. When no schema source is active, the system SHALL emit the assistant's response on stdout as raw text.

#### Scenario: Text output when no schema

- **WHEN** the user runs `llm-cli run --mode general "hi"` and `general` has no bound schema
- **THEN** stdout contains the raw text response (no surrounding JSON envelope)

#### Scenario: JSON output when schema present

- **WHEN** the user runs `llm-cli run --mode ocr @img.png` and `ocr` has a bound schema
- **THEN** stdout contains a JSON object matching the schema

### Requirement: Encoding per `provider_kind`

The system SHALL encode the schema in the outgoing request based on the resolved provider's `provider_kind`:
- `llama.cpp` — set top-level `response_format = {"type": "json_schema", "json_schema": {"name": "schema", "schema": <schema>, "strict": true}}`.
- `vllm` — set `extra_body.guided_json = <schema>`.
- `ollama` — set top-level `format = <schema>`.
- `openai-generic` — set top-level `response_format = {"type": "json_schema", "json_schema": {"name": "schema", "schema": <schema>, "strict": true}}` and write a one-line stderr warning that fallback encoding is in use.

#### Scenario: vLLM uses guided_json

- **WHEN** the resolved provider has `provider_kind = "vllm"` and a schema is active
- **THEN** the outgoing request contains `extra_body.guided_json = <schema>` and no `response_format`

#### Scenario: Ollama uses format

- **WHEN** the resolved provider has `provider_kind = "ollama"` and a schema is active
- **THEN** the outgoing request contains top-level `format = <schema>`

#### Scenario: openai-generic warns on stderr

- **WHEN** the resolved provider has `provider_kind = "openai-generic"` and a schema is active
- **THEN** the system writes a one-line stderr warning naming the fallback encoding and proceeds

### Requirement: Output validation against schema

After receiving the assistant's response, when a schema is active, the system SHALL parse the assistant's `content` field as JSON and validate it against the schema using JSON Schema Draft 2020-12. On validation success, the validated JSON SHALL be printed to stdout (pretty-printed by default; compact with `--compact`). On parse or validation failure, the raw assistant content SHALL be written to stderr, an explanatory message SHALL be written to stderr, and the system SHALL exit with code 2.

#### Scenario: Valid response printed pretty by default

- **WHEN** the assistant returns `{"text": "hello"}` and the schema accepts it
- **THEN** stdout contains pretty-printed JSON with newlines/indentation and the process exits 0

#### Scenario: Valid response compact

- **WHEN** the user passes `--compact` and the assistant returns valid JSON
- **THEN** stdout contains the JSON on a single line with no extraneous whitespace

#### Scenario: Invalid JSON returns exit 2

- **WHEN** the assistant returns text that does not parse as JSON
- **THEN** the system writes the raw content to stderr, writes a parse error to stderr, and exits with code 2

#### Scenario: JSON that fails validation returns exit 2

- **WHEN** the assistant returns parseable JSON that does not match the schema (e.g., missing required field)
- **THEN** the system writes the raw content and the validator's error path to stderr and exits with code 2
