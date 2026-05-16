## ADDED Requirements

### Requirement: Entry point and subcommands

The system SHALL expose a single console-script entry point `llm-cli` with subcommands `run`, `list`, `ping`, and `show`. Running `llm-cli` with no arguments SHALL print usage and exit with code 1.

#### Scenario: Invocation with no args prints usage

- **WHEN** the user runs `llm-cli` with no arguments
- **THEN** the system writes usage text to stderr and exits with code 1

#### Scenario: Unknown subcommand

- **WHEN** the user runs `llm-cli frobnicate`
- **THEN** the system writes an error explaining the unknown subcommand to stderr and exits with code 1

### Requirement: `run` command surface

The `run` subcommand SHALL accept a single optional positional prompt string, zero or more `@<path>` positional file inputs, a required `--mode <name>` flag, and optional flags `--provider <name>`, `--model <name>`, `--schema <path>`, `--pdf-strategy {auto|images|text}`, `--max-pages <int>`, `--temperature <float>`, `--top-p <float>`, `--top-k <int>`, `--quiet`, `--compact`, and `--dry-run`. Additional sampling overrides MAY be passed as `--set <key>=<value>` for arbitrary keys.

#### Scenario: Run with prompt and mode

- **WHEN** the user runs `llm-cli run --mode general "what is 2+2"`
- **THEN** the system resolves the request and emits the model's text response on stdout with exit code 0

#### Scenario: Mode is required

- **WHEN** the user runs `llm-cli run "hello"` without `--mode`
- **THEN** the system writes an error stating that `--mode` is required to stderr and exits with code 1

#### Scenario: File inputs are recognized by `@` prefix

- **WHEN** the user runs `llm-cli run --mode summarize @article.md`
- **THEN** the system treats `@article.md` as a file input, not as part of the prompt string

#### Scenario: Arbitrary sampling override via `--set`

- **WHEN** the user runs `llm-cli run --mode general --set dry_multiplier=0.8 "hi"`
- **THEN** `dry_multiplier=0.8` SHALL appear in the resolved request sent to the provider

### Requirement: `--dry-run` shows resolved request without calling provider

When `--dry-run` is passed, the system SHALL build the full resolved request (merged sampling, encoded inputs, encoded schema) and print it as pretty-printed JSON to stdout without making any HTTP call. Exit code SHALL be 0.

#### Scenario: Dry-run prints resolved request

- **WHEN** the user runs `llm-cli run --mode code --dry-run "write hello world"`
- **THEN** the system writes a JSON object containing `model`, `messages`, `temperature` (and other resolved sampling fields), and any `extra_body`/`response_format` to stdout, makes no HTTP call, and exits with code 0

### Requirement: `list` subcommand introspection

The `list` subcommand SHALL support `list providers`, `list models [--provider <name>]`, and `list modes`, each printing a human-readable table to stdout and exiting with code 0.

#### Scenario: List providers

- **WHEN** the user runs `llm-cli list providers`
- **THEN** the system prints one row per provider in `models.json` with name, base URL, and provider kind, and exits with code 0

#### Scenario: List models scoped to a provider

- **WHEN** the user runs `llm-cli list models --provider nuc`
- **THEN** the system prints only the models defined under provider `nuc`, including id, name, input modalities, context window, and reasoning support, and exits with code 0

#### Scenario: List modes shows built-ins and user overrides

- **WHEN** the user runs `llm-cli list modes`
- **THEN** the system prints one row per mode (built-ins shipped with the package merged with user overrides) and indicates which source each row came from

### Requirement: `ping` subcommand

The `ping` subcommand SHALL perform a `GET /v1/models` (or equivalent health endpoint) against one or all configured providers and report status, latency, and any error per provider. Exit code SHALL be 0 if all reachable, 3 otherwise.

#### Scenario: Ping a healthy provider

- **WHEN** the user runs `llm-cli ping --provider nuc` against a reachable provider
- **THEN** the system prints `nuc OK <latency>ms` to stdout and exits with code 0

#### Scenario: Ping all when one provider is down

- **WHEN** the user runs `llm-cli ping` and one of two providers is unreachable
- **THEN** the system prints status lines for each provider, with the unreachable one labeled with its error, and exits with code 3

### Requirement: `show` subcommand

The `show` subcommand SHALL accept `show provider <name>`, `show model <name>`, or `show mode <name>` and print the full effective definition (including default sampling) as pretty-printed JSON to stdout.

#### Scenario: Show mode

- **WHEN** the user runs `llm-cli show mode ocr`
- **THEN** the system prints the resolved `ocr` mode definition (sampling, system_prompt, schema, requires_input) as JSON to stdout and exits with code 0

### Requirement: stdout/stderr discipline

The system SHALL write only the final result to stdout (raw text or JSON) and only diagnostics and error messages to stderr. The `--quiet` flag SHALL silence diagnostic stderr output but SHALL NOT silence error messages.

#### Scenario: Quiet suppresses diagnostics but not errors

- **WHEN** the user runs `llm-cli run --mode general --quiet "hi"` and the provider returns 500
- **THEN** the system writes nothing to stdout, writes the error to stderr, and exits with code 3

### Requirement: Exit code categories

The system SHALL use exit codes as follows:
- `0` — success
- `1` — user error (bad arguments, missing config, unknown mode/provider/model, unsupported input, max-pages exceeded)
- `2` — schema validation failed (a response was received but failed JSON Schema validation)
- `3` — provider/transport error (HTTP non-2xx, network failure, timeout, auth)

#### Scenario: Schema validation failure produces exit 2

- **WHEN** a provider returns a response that does not validate against the requested schema
- **THEN** the system writes the raw response to stderr and exits with code 2

#### Scenario: HTTP 500 from provider produces exit 3

- **WHEN** the provider returns HTTP 500
- **THEN** the system writes the error to stderr and exits with code 3
