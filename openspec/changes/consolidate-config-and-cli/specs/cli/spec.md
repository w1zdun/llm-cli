## MODIFIED Requirements

### Requirement: Entry point and subcommands

The system SHALL expose a single console-script entry point `llm-cli`. The default action (no subcommand) SHALL run a chat-completion request. Named subcommands `list`, `ping`, and `show` SHALL also be available. Running `llm-cli` with no arguments at all SHALL print usage and exit with code 1.

#### Scenario: Invocation with no args prints usage

- **WHEN** the user runs `llm-cli` with no arguments
- **THEN** the system writes usage text to stderr and exits with code 1

#### Scenario: Default action runs a request

- **WHEN** the user runs `llm-cli --mode general "what is 2+2"`
- **THEN** the system resolves and executes the request and emits the model's response on stdout (no `run` subcommand needed)

#### Scenario: `run` is not a subcommand

- **WHEN** the user runs `llm-cli run --mode general "hi"`
- **THEN** the system either treats `run` as a positional prompt token (so the resolved prompt becomes `"run hi"`) OR exits with a usage error — but SHALL NOT interpret `run` as the legacy subcommand

#### Scenario: Unknown subcommand

- **WHEN** the user runs `llm-cli frobnicate`
- **THEN** the system treats `frobnicate` as a positional prompt token (just like any other unrecognized argument) and continues parsing; if `--mode` is missing, exits with code 1

### Requirement: Default-action command surface

The default invocation (no subcommand) SHALL accept a single optional positional prompt string, zero or more `@<path>` positional file inputs, a required `--mode <name>` flag, and optional flags `--provider <name>`, `--model <name>`, `--schema <path>`, `--pdf-strategy {auto|images|text}`, `--max-pages <int>`, `--temperature <float>`, `--top-p <float>`, `--top-k <int>`, `--enable-thinking / --no-enable-thinking`, `--preserve-thinking / --no-preserve-thinking`, `--sampling-template <name>`, `--quiet`, `--compact`, and `--dry-run`. Additional sampling overrides MAY be passed as `--set <key>=<value>` for arbitrary keys.

#### Scenario: Run with prompt and mode

- **WHEN** the user runs `llm-cli --mode general "what is 2+2"`
- **THEN** the system resolves the request and emits the model's text response on stdout with exit code 0

#### Scenario: Mode is required

- **WHEN** the user runs `llm-cli "hello"` without `--mode`
- **THEN** the system writes an error stating that `--mode` is required to stderr and exits with code 1

#### Scenario: File inputs are recognized by `@` prefix

- **WHEN** the user runs `llm-cli --mode summarize @article.md`
- **THEN** the system treats `@article.md` as a file input, not as part of the prompt string

#### Scenario: Arbitrary sampling override via `--set`

- **WHEN** the user runs `llm-cli --mode general --set dry_multiplier=0.8 "hi"`
- **THEN** `dry_multiplier=0.8` SHALL appear in the resolved request sent to the provider

### Requirement: `--dry-run` shows resolved request without calling provider

When `--dry-run` is passed, the system SHALL build the full resolved request (merged sampling, expanded sampling templates, routed thinking kwargs, encoded inputs, encoded schema) and print it as pretty-printed JSON to stdout without making any HTTP call. Exit code SHALL be 0.

#### Scenario: Dry-run prints resolved request

- **WHEN** the user runs `llm-cli --mode code --dry-run "write hello world"`
- **THEN** the system writes a JSON object containing `model`, `messages`, sampling fields, and any `extra_body`/`response_format` to stdout, makes no HTTP call, and exits with code 0

## ADDED Requirements

### Requirement: `list templates` subcommand

The `list` subcommand SHALL support `list templates`, which prints one row per known sampling template (built-ins merged with user-declared) and indicates the source of each row. Exit code SHALL be 0.

#### Scenario: List templates shows builtins and user overrides

- **WHEN** the user runs `llm-cli list templates`
- **THEN** the system prints one row per template (built-in and user-declared) with name and source, and exits with code 0
