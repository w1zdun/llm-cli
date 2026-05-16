## ADDED Requirements

### Requirement: Resolution stack and deep-merge semantics

The system SHALL resolve effective sampling parameters by deep-merging four layers in this order (later layers override earlier layers per key):
1. `provider.sampling` from `models.json`.
2. `model.sampling` from the chosen model entry in `models.json`.
3. `mode.sampling` from the resolved mode.
4. CLI flag overrides (`--temperature`, `--top-p`, `--top-k`, and any `--set key=value` pairs).

The same four-layer stack with identical merge semantics SHALL apply to `extra_body` independently.

#### Scenario: CLI flag overrides mode sampling

- **WHEN** the `code` mode sets `temperature = 0.2` and the user passes `--temperature 0.0`
- **THEN** the resolved `temperature` is `0.0`

#### Scenario: Mode adds a key without removing provider keys

- **WHEN** the provider sets `top_k = 20` and the mode sets `temperature = 0.2`
- **THEN** the resolved sampling contains both `top_k = 20` and `temperature = 0.2`

#### Scenario: extra_body merged separately from sampling

- **WHEN** the provider sets `extra_body = {guided_decoding_backend = "xgrammar"}` and the mode sets `extra_body = {logit_bias = {...}}`
- **THEN** the resolved `extra_body` contains both keys

### Requirement: Validation off — pass-through

The system SHALL pass all resolved sampling and `extra_body` keys through to the provider's `/v1/chat/completions` payload without filtering, normalization, or validation against any client-side schema. Unknown keys SHALL not generate warnings.

#### Scenario: Exotic sampling key reaches provider

- **WHEN** a mode sets `sampling.dry_multiplier = 0.8` and the chosen provider is `llama.cpp`
- **THEN** `dry_multiplier: 0.8` appears in the outgoing JSON payload exactly as configured

#### Scenario: Typo not caught client-side

- **WHEN** the user passes `--set temperture=0.2` (misspelled)
- **THEN** the system sends `temperture: 0.2` to the provider; if the provider rejects it, the system exits with code 3 reporting the provider's error message

### Requirement: Reasoning is a sampling key with model-mapped encoding

The system SHALL treat `sampling.reasoning` as an abstract value drawn from `{"off", "minimal", "low", "medium", "high", "xhigh"}`. At request-build time, the system SHALL look up the resolved model's `thinkingLevelMap[level]` to obtain a model-specific encoding value, then encode it according to the model's `thinkingFormat`:
- `qwen-chat-template` — add `chat_template_kwargs.enable_thinking = <value>` to `extra_body`.
- `openai-reasoning-effort` — add top-level `reasoning_effort = <value>` to the request.
- `none` — drop the reasoning key from the outgoing request.

If `thinkingLevelMap[level]` is missing or `null`, the system SHALL exit with code 1 and a message naming supported levels for that model.

#### Scenario: Reasoning level mapped via thinkingLevelMap

- **WHEN** mode sets `reasoning = "high"` and the model has `thinkingLevelMap = {"high": "true"}` with `thinkingFormat = "qwen-chat-template"`
- **THEN** the outgoing request includes `extra_body.chat_template_kwargs.enable_thinking = "true"`

#### Scenario: Unsupported reasoning level is a hard error

- **WHEN** mode sets `reasoning = "medium"` and the model has `thinkingLevelMap = {"off": "false", "high": "true"}` (no entry for `"medium"`)
- **THEN** the system writes "reasoning level 'medium' not supported by model X; supported: off, high" to stderr and exits with code 1

#### Scenario: thinkingFormat=none drops the reasoning key

- **WHEN** the model has `thinkingFormat = "none"` and mode sets `reasoning = "off"`
- **THEN** the outgoing request contains no reasoning-related field

### Requirement: CLI `--set` for arbitrary sampling overrides

The system SHALL accept zero or more `--set <key>=<value>` flags on `run`. Each `<value>` SHALL be parsed as JSON; if JSON parsing fails, it SHALL be treated as a string. Keys MAY include nested paths using dot notation (e.g., `--set chat_template_kwargs.enable_thinking=true`), which SHALL be expanded into nested objects in the resolved request.

#### Scenario: Set nested key via dot notation

- **WHEN** the user passes `--set chat_template_kwargs.enable_thinking=true`
- **THEN** the outgoing request contains `extra_body.chat_template_kwargs.enable_thinking = true` (boolean)

#### Scenario: String values supported

- **WHEN** the user passes `--set custom_label=experiment-1`
- **THEN** the outgoing request contains `custom_label = "experiment-1"` (string, JSON-parse fell through to string)
