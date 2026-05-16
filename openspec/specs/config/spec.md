## ADDED Requirements

### Requirement: Config file locations

The system SHALL read configuration from two files:
- `${XDG_CONFIG_HOME:-~/.config}/llm-cli/models.json` — providers and models registry.
- `${XDG_CONFIG_HOME:-~/.config}/llm-cli/modes.json` — user-defined modes.

If `models.json` is missing, the system SHALL exit with code 1 and a message instructing the user to create it. If `modes.json` is missing, the system SHALL proceed using only the built-in mode catalog.

#### Scenario: Missing models.json is a hard error

- **WHEN** the user runs `llm-cli run --mode general "hi"` and `~/.config/llm-cli/models.json` does not exist
- **THEN** the system writes an error pointing to the expected path to stderr and exits with code 1

#### Scenario: Missing modes.json falls back to built-ins

- **WHEN** the user runs `llm-cli run --mode general "hi"` and `~/.config/llm-cli/modes.json` does not exist
- **THEN** the system proceeds using only the built-in modes shipped with the package

### Requirement: JSONC parsing

The system SHALL parse both config files as JSONC, tolerating `//` line comments, `/* */` block comments, and trailing commas. Parse errors SHALL be reported with file path and line number to stderr and SHALL exit with code 1.

#### Scenario: JSONC comments are tolerated

- **WHEN** a config file contains `// comment` lines or trailing commas
- **THEN** the system parses the file successfully

#### Scenario: Malformed JSONC reports line number

- **WHEN** a config file contains a syntax error
- **THEN** the system writes a message including the file path and offending line to stderr and exits with code 1

### Requirement: `models.json` schema

`models.json` SHALL contain a top-level `providers` object mapping provider names to provider definitions. Each provider definition SHALL contain `base_url` (string, required), `api` (string, optional, defaults to `"openai-completions"`), `provider_kind` (string, optional, one of `llama.cpp|vllm|ollama|openai-generic`, defaults to `openai-generic`), `api_key` (string, optional), `compat` (object, optional), `sampling` (object, optional, default sampling for the provider), `extra_body` (object, optional), and `models` (array, required) of model definitions.

Each model definition SHALL contain `id` (string, required, the value sent in the `model` field on requests), `name` (string, optional, a display name), `input` (array of strings, required, subset of `["text", "image"]`), `context_window` (integer, optional), `max_tokens` (integer, optional), `reasoning` (boolean, optional, defaults to `false`), `thinkingFormat` (string, optional), `thinkingLevelMap` (object, optional), `sampling` (object, optional, per-model sampling overrides), and `extra_body` (object, optional).

#### Scenario: Pi-shaped models.json loads

- **WHEN** the user places a `models.json` matching the shape of `~/.pi/agent/models.json` (providers with `baseUrl`, `apiKey`, nested `models[]`, etc.) at the configured location
- **THEN** the system loads it without error

#### Scenario: Missing required field reports the field name

- **WHEN** a provider in `models.json` lacks `base_url`
- **THEN** the system writes an error naming the missing field and the provider to stderr and exits with code 1

#### Scenario: Camel-case and snake-case keys both accepted

- **WHEN** a model defines `contextWindow` (camelCase, as pi uses) or `context_window` (snake_case)
- **THEN** the system accepts both spellings interchangeably during config load

### Requirement: `modes.json` schema

`modes.json` SHALL contain a top-level object mapping mode names to mode definitions. Each mode definition SHALL contain `sampling` (object, optional), `system_prompt` (string, optional), `user_prompt_template` (string, optional, a Jinja2 template), `schema` (object, optional, a JSON Schema), `requires_input` (string or array of strings, optional, one of `text|image|pdf`), and `extra_body` (object, optional).

#### Scenario: User mode overrides built-in mode of the same name

- **WHEN** the user defines a `code` mode in `modes.json` and a built-in `code` mode also ships with the package
- **THEN** the user-defined mode is used; the built-in is ignored for that name

#### Scenario: Built-in modes available without user modes.json

- **WHEN** the user has no `modes.json` and runs `llm-cli list modes`
- **THEN** the system prints the built-in modes (`code`, `general`, `design`, `image`, `ocr`, `summarize`, `classify`, `extract`)

### Requirement: Config validation is structural only

The system SHALL validate the structural shape of config files (required fields present, types correct) but SHALL NOT validate the semantics of sampling parameters against any per-provider schema. Unknown sampling keys SHALL be accepted at config load and passed through to the provider at request time.

#### Scenario: Unknown sampling parameter loads without error

- **WHEN** a mode declares `sampling.experimental_new_sampler = 0.5` in `modes.json`
- **THEN** the system loads the config without warning or error

#### Scenario: Wrong type in required field rejected

- **WHEN** a provider declares `base_url = 42` (integer instead of string)
- **THEN** the system writes a type-mismatch error naming the field and exits with code 1
