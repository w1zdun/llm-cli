## ADDED Requirements

### Requirement: Provider selection

The system SHALL accept a `--provider <name>` flag to choose which provider entry from `models.json` is used. If `--provider` is omitted, the system SHALL use the provider designated by an optional top-level `default_provider` field in `models.json`. If no default is set and `--provider` is omitted, the system SHALL exit with code 1 and a message listing available providers.

#### Scenario: Explicit provider flag

- **WHEN** the user runs `llm-cli run --provider nuc --mode general --model Qwen3.6-27B-vision "hi"`
- **THEN** the system uses the `nuc` provider entry

#### Scenario: Default provider used when flag omitted

- **WHEN** `models.json` declares `default_provider = "nuc"` and the user runs `llm-cli run --mode general "hi"`
- **THEN** the system uses the `nuc` provider entry

#### Scenario: No default and no flag is a hard error

- **WHEN** `models.json` has no `default_provider` and the user omits `--provider`
- **THEN** the system writes an error listing all configured providers to stderr and exits with code 1

### Requirement: Model selection within a provider

The system SHALL accept a `--model <name>` flag matching either a model's `id` or its `name` within the chosen provider's `models` array. If `--model` is omitted, the system SHALL use a model designated by an optional top-level `default_model` field in `models.json`, scoped to the chosen provider. If no default is set and `--model` is omitted, the system SHALL exit with code 1 and a message listing available models for the chosen provider.

#### Scenario: Model resolved by name

- **WHEN** the user passes `--model Qwen3.6-27B-vision` and that name appears under the chosen provider
- **THEN** the system selects the matching model entry

#### Scenario: Model resolved by id

- **WHEN** the user passes `--model ./Qwen3.6-35B-A3B-MLX-8bit` and that id appears under the chosen provider
- **THEN** the system selects the matching model entry

#### Scenario: Ambiguous match between providers requires explicit provider

- **WHEN** the same model `name` appears under two providers and the user omits `--provider`
- **THEN** the system writes an error explaining the ambiguity and exits with code 1

### Requirement: Provider kinds drive structured-output encoding

Each provider definition's `provider_kind` field SHALL determine how schemas (see schemas spec) are encoded on the wire. The system SHALL support `provider_kind` values of `llama.cpp`, `vllm`, `ollama`, and `openai-generic`. Unknown values SHALL be treated as `openai-generic` with a stderr warning at load time.

#### Scenario: Vllm provider uses guided_json encoding

- **WHEN** a request is built for a provider with `provider_kind = "vllm"` and a schema is present
- **THEN** the schema is placed in `extra_body.guided_json`

#### Scenario: Unknown provider_kind warns and falls back

- **WHEN** a provider declares `provider_kind = "exotic-fork"`
- **THEN** the system writes a warning to stderr at load time and treats the provider as `openai-generic`

### Requirement: Capability flags on models

Each model entry SHALL declare its supported input modalities via an `input` array containing `"text"`, `"image"`, or both. The system SHALL use this array to reject incompatible input combinations (see inputs spec). The model entry MAY declare `reasoning = true|false` to indicate support for reasoning-level control via `thinkingLevelMap`.

#### Scenario: Image input refused for text-only model

- **WHEN** the user invokes `llm-cli run` with an `@image.png` input against a model whose `input` is `["text"]`
- **THEN** the system writes an error explaining the mismatch to stderr and exits with code 1

#### Scenario: Reasoning level requested against non-reasoning model

- **WHEN** a mode requests `sampling.reasoning = "high"` and the resolved model has `reasoning = false`
- **THEN** the system writes an error to stderr and exits with code 1

### Requirement: Authentication header construction

When a provider definition includes `api_key`, the system SHALL send it as `Authorization: Bearer <api_key>` on every request. When `api_key` is absent or empty, no `Authorization` header SHALL be sent.

#### Scenario: API key sent as bearer token

- **WHEN** the resolved provider has `api_key = "ollama"`
- **THEN** the outgoing request carries header `Authorization: Bearer ollama`

#### Scenario: No api_key omits authorization header

- **WHEN** the resolved provider has no `api_key`
- **THEN** the outgoing request has no `Authorization` header
