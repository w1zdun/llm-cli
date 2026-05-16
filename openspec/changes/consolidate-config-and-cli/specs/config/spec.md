## MODIFIED Requirements

### Requirement: Config file locations

The system SHALL read configuration from a single file:
- `${XDG_CONFIG_HOME:-~/.config}/llm-cli/models.json` — providers, models, modes, and sampling templates.

If `models.json` is missing, the system SHALL exit with code 1 and a message instructing the user to create it.

#### Scenario: Missing models.json is a hard error

- **WHEN** the user runs `llm-cli --mode general "hi"` and `~/.config/llm-cli/models.json` does not exist
- **THEN** the system writes an error pointing to the expected path to stderr and exits with code 1

#### Scenario: No modes.json needed

- **WHEN** the user runs `llm-cli --mode general "hi"` and only `~/.config/llm-cli/models.json` exists (no separate `modes.json`)
- **THEN** the system proceeds, using built-in modes merged with any modes declared inside `models.json`

### Requirement: `models.json` schema

`models.json` SHALL contain:
- A top-level `providers` object mapping provider names to provider definitions.
- An optional top-level `samplingTemplates` object mapping template names to sampling-parameter bundles.
- Optional top-level `default_provider` and `default_model` fields.

Each provider definition SHALL contain `base_url` (string, required), `api` (string, optional, defaults to `"openai-completions"`), `provider_kind` (string, optional, one of `llama.cpp|vllm|ollama|openai-generic`, defaults to `openai-generic`), `api_key` (string, optional), `compat` (object, optional, containing `param_mapping: dict[str, str]` and any future compat knobs), `file_passing` (string, optional, one of `path|inline`, defaults to `path` when `provider_kind ∈ {llama.cpp, vllm, ollama}` and to `inline` for `openai-generic`), `sampling` (object, optional, default sampling for the provider), `extra_body` (object, optional), `max_context_tokens` (integer, optional), `max_output_tokens` (integer, optional), `modes` (object, optional, mode definitions scoped to this provider), and `models` (array, required) of model definitions.

The `compat.param_mapping` object maps abstract parameter names (used in config and CLI) to provider-specific wire-format field names. See the `transport` capability for the resolution rule and per-`provider_kind` defaults.

Each model definition SHALL contain `id` (string, required), `name` (string, optional), `input` (array of strings, required, subset of `["text", "image"]`), `context_window` (integer, optional), `reasoning` (boolean, optional, defaults to `false`), `thinkingFormat` (string, optional, one of `qwen-chat-template|openai-reasoning-effort|none`), `supports_developer_role` (boolean, optional, defaults to `false`), `sampling` (object, optional), `extra_body` (object, optional), `max_context_tokens` (integer, optional), `max_output_tokens` (integer, optional), and `modes` (object, optional, mode definitions scoped to this model).

`models.json` MAY also contain a top-level `modes` object (the "global" mode layer) mapping mode names to mode definitions. This layer applies regardless of which provider/model is selected and is merged with built-in modes, per-provider modes, and per-model modes per the `modes` capability.

#### Scenario: Modes nested under a provider load

- **WHEN** `models.json` declares `providers.nuc.modes = {code: {sampling: {temperature: 0.2}}}`
- **THEN** the system makes `code` available as a mode whose `temperature` defaults to `0.2` whenever provider `nuc` is selected

#### Scenario: Modes nested under a model load

- **WHEN** `models.json` declares a mode `code` under a specific model's `modes` block
- **THEN** the system makes that mode available whenever both the provider and that specific model are selected

#### Scenario: Missing required field reports the field name

- **WHEN** a provider in `models.json` lacks `base_url`
- **THEN** the system writes an error naming the missing field and the provider to stderr and exits with code 1

#### Scenario: Camel-case and snake-case keys both accepted

- **WHEN** a model defines `contextWindow` (camelCase) or `context_window` (snake_case)
- **THEN** the system accepts both spellings interchangeably during config load

#### Scenario: thinkingLevelMap rejected

- **WHEN** a model in `models.json` declares a `thinkingLevelMap` field
- **THEN** the system writes an error explaining that `thinkingLevelMap` is no longer supported and naming the replacement keys (`enable_thinking`, `preserve_thinking`) to stderr and exits with code 1

#### Scenario: file_passing defaults per provider_kind

- **WHEN** a provider declares `provider_kind = "llama.cpp"` and does not declare `file_passing`
- **THEN** the resolved `file_passing` is `"path"`

#### Scenario: file_passing inline for openai-generic

- **WHEN** a provider declares `provider_kind = "openai-generic"` and does not declare `file_passing`
- **THEN** the resolved `file_passing` is `"inline"`

#### Scenario: Global modes load

- **WHEN** `models.json` declares a top-level `modes = {summary-brief: {sampling: {temperature: 0.3}, system_prompt: "Summarize in one paragraph."}}`
- **THEN** the system makes `summary-brief` available regardless of which provider is selected, with the declared sampling and system prompt

#### Scenario: supports_developer_role defaults to false

- **WHEN** a model definition does not declare `supports_developer_role`
- **THEN** the resolved capability is `false`

## REMOVED Requirements

### Requirement: `modes.json` schema

**Reason**: Modes are now declared inside `models.json` under each provider and/or each model. The separate `modes.json` file is no longer read.
**Migration**: Move every entry from `~/.config/llm-cli/modes.json` into the appropriate `providers.<name>.modes` block inside `~/.config/llm-cli/models.json`, or delete it if the equivalent built-in mode is sufficient. Delete `~/.config/llm-cli/modes.json`.
