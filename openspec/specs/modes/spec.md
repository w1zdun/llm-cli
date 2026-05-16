## ADDED Requirements

### Requirement: `--mode` is mandatory

The system SHALL require a `--mode <name>` flag on every `run` invocation. If `--mode` is omitted, the system SHALL exit with code 1 with a message listing all available modes. The system SHALL NOT provide an implicit default mode, an `LLM_CLI_MODE` environment variable, or any other fallback mechanism.

#### Scenario: Missing --mode aborts with available modes listed

- **WHEN** the user runs `llm-cli run "hello"` without `--mode`
- **THEN** the system writes "error: --mode is required" followed by a list of available modes to stderr and exits with code 1

#### Scenario: LLM_CLI_MODE environment variable is ignored

- **WHEN** the user sets `LLM_CLI_MODE=general` in the environment and runs `llm-cli run "hi"` without `--mode`
- **THEN** the system still exits with code 1

### Requirement: Built-in mode catalog

The system SHALL ship with built-in modes named `code`, `general`, `design`, `image`, `ocr`, `summarize`, `classify`, and `extract`. These SHALL be available without requiring the user to create `modes.json`. The full definition of each (sampling values, system prompts, schemas where applicable) SHALL be visible via `llm-cli show mode <name>`.

#### Scenario: Built-in mode usable out of the box

- **WHEN** a fresh install is invoked with `llm-cli run --mode ocr @scan.png`
- **THEN** the system uses the shipped `ocr` mode definition without requiring any user `modes.json`

### Requirement: User mode overrides

A user-defined mode in `modes.json` SHALL completely replace a built-in mode of the same name (not merge with it). Modes not redefined by the user SHALL remain available from the built-in catalog.

#### Scenario: Full replacement of built-in by user mode

- **WHEN** the user defines `code` in `modes.json` with only `sampling = {temperature = 0.0}` and no `system_prompt`
- **THEN** the resolved `code` mode has `temperature = 0.0` and no system prompt from the built-in is inherited

### Requirement: Mode fields

A mode definition SHALL support the fields:
- `sampling` — object of sampling parameters (including `reasoning` if applicable).
- `system_prompt` — string; becomes the system message in the chat request.
- `user_prompt_template` — Jinja2 template string; if present, the user's literal prompt and file inputs are rendered through this template. If absent, the user's literal prompt and file content are concatenated into the user message.
- `schema` — object; a JSON Schema bound to this mode. If both `--schema` and `mode.schema` are present, `--schema` SHALL take precedence.
- `requires_input` — string or array of strings from `{"text", "image", "pdf"}`; the system SHALL verify the user passed at least one input of each required type.
- `extra_body` — object; merged into the request `extra_body` according to the sampling-resolution stack.

#### Scenario: Mode with bound schema triggers JSON output

- **WHEN** the `ocr` mode has `schema = {...}` and the user runs `llm-cli run --mode ocr @img.png`
- **THEN** the system emits validated JSON on stdout

#### Scenario: requires_input enforced

- **WHEN** the `ocr` mode declares `requires_input = "image"` and the user runs `llm-cli run --mode ocr "transcribe this"` with no image input
- **THEN** the system writes an error explaining the missing input type to stderr and exits with code 1

#### Scenario: --schema overrides mode-bound schema

- **WHEN** the `extract` mode has a bound schema and the user passes `--schema invoice.json`
- **THEN** the system uses `invoice.json` and ignores the mode's bound schema

### Requirement: Mode `system_prompt` becomes the system message

When a mode declares a non-empty `system_prompt`, the system SHALL include a `{"role": "system", "content": <system_prompt>}` message as the first entry in the chat request's `messages` array. When no `system_prompt` is declared, no system message SHALL be added.

#### Scenario: System prompt prepended to messages

- **WHEN** the `code` mode has `system_prompt = "You are a precise coding assistant."`
- **THEN** the outgoing chat request begins with `{"role": "system", "content": "You are a precise coding assistant."}`
