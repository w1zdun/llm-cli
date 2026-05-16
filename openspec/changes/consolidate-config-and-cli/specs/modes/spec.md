## MODIFIED Requirements

### Requirement: `--mode` is mandatory

The system SHALL require a `--mode <name>` flag on every request invocation. If `--mode` is omitted, the system SHALL exit with code 1 with a message listing all available modes. The system SHALL NOT provide an implicit default mode, an `LLM_CLI_MODE` environment variable, or any other fallback mechanism.

#### Scenario: Missing --mode aborts with available modes listed

- **WHEN** the user runs `llm-cli "hello"` without `--mode`
- **THEN** the system writes "error: --mode is required" followed by a list of available modes to stderr and exits with code 1

#### Scenario: LLM_CLI_MODE environment variable is ignored

- **WHEN** the user sets `LLM_CLI_MODE=general` in the environment and runs `llm-cli "hi"` without `--mode`
- **THEN** the system still exits with code 1

### Requirement: User mode overrides

Mode definitions SHALL resolve through four layers, deep-merged per key (later wins):
1. Built-in modes shipped with the package.
2. Global modes from the top-level `modes` block in `models.json`.
3. `provider.modes.<name>` from the selected provider in `models.json`.
4. `model.modes.<name>` from the selected model in `models.json`.

A layer MAY define only a subset of fields; unspecified fields SHALL inherit from earlier layers. A layer's `sampling` and `extra_body` objects SHALL themselves be deep-merged with earlier layers' (not replaced wholesale).

#### Scenario: Model-level mode overrides provider-level for the same name

- **WHEN** provider `nuc` declares `modes.code = {sampling: {temperature: 0.2}}` and a model under `nuc` declares `modes.code = {sampling: {temperature: 0.1}}`
- **THEN** the resolved `code` mode for that model has `temperature = 0.1`, with all other provider-level fields inherited

#### Scenario: Provider-level mode inherits built-in defaults

- **WHEN** the built-in `code` mode declares `system_prompt = "You are a precise coding assistant."` and provider `nuc` declares `modes.code = {sampling: {temperature: 0.2}}`
- **THEN** the resolved `code` mode for `nuc` has `temperature = 0.2` AND `system_prompt = "You are a precise coding assistant."`

#### Scenario: Global mode provides system_prompt across providers

- **WHEN** `models.json` declares a top-level `modes.code = {system_prompt: "You are a precise coding assistant."}` and a provider declares `modes.code = {sampling: {temperature: 0.2}}` without a `system_prompt`
- **THEN** the resolved `code` mode for any model under that provider has `temperature = 0.2` (from provider) AND `system_prompt = "You are a precise coding assistant."` (from global)

#### Scenario: Each layer can extend with new fields

- **WHEN** the built-in `code` mode has `sampling.temperature = 0.2`, global declares `modes.code = {system_prompt: "..."}`, provider declares `modes.code = {sampling: {top_p: 0.9}}`, and model declares `modes.code = {max_output_tokens: 1024}`
- **THEN** the resolved `code` mode has all four contributions merged: `temperature = 0.2`, `system_prompt = "..."`, `top_p = 0.9`, `max_output_tokens = 1024`

#### Scenario: Mode unknown at all four layers is an error

- **WHEN** the user passes `--mode obscure` and no built-in, global, provider-level, or model-level definition of `obscure` exists
- **THEN** the system writes an error listing available modes to stderr and exits with code 1

## ADDED Requirements

### Requirement: Mode `role` with model capability check

A mode definition MAY include a `role` field with value `"user"` or `"developer"` (default `"user"`). The system SHALL use this value as the `role` of the message containing the assembled prompt and file inputs.

When the resolved mode declares `role = "developer"`:
- If the resolved model has `supports_developer_role = true`, the outgoing chat request SHALL send `{"role": "developer", "content": [...]}` as the (typically second) message.
- If the resolved model has `supports_developer_role = false` (the default), the system SHALL exit with code 1 and an error message naming the mode, the model, and the missing capability.

The `system` message (when the mode declares `system_prompt`) keeps `role: "system"` regardless of the mode's `role` field.

#### Scenario: developer role used when model supports it

- **WHEN** the `code` mode declares `role = "developer"` and the selected model declares `supports_developer_role = true`
- **THEN** the outgoing request's prompt message has `role = "developer"` (the system message, if present, still uses `role = "system"`)

#### Scenario: developer role on unsupporting model is hard error

- **WHEN** the `code` mode declares `role = "developer"` and the selected model has `supports_developer_role = false` (or omits it)
- **THEN** the system writes an error naming the mode, the model id, and explaining that the developer role is not supported, to stderr and exits with code 1

#### Scenario: default user role

- **WHEN** a mode does not declare a `role` field
- **THEN** the outgoing request's prompt message has `role = "user"`

### Requirement: Mode `max_context_tokens` and `max_output_tokens`

A mode definition MAY include `max_context_tokens` (positive integer) and `max_output_tokens` (positive integer). Both SHALL participate in the four-layer resolution stack (`provider → model → mode → CLI`) but SHALL live outside the `sampling` block. `max_context_tokens` SHALL trigger input-size enforcement (see the `inputs` capability). `max_output_tokens` SHALL be routed into the outgoing request body's max-tokens field via the provider's `compat.param_mapping["max_output_tokens"]` (see the `transport` capability).

#### Scenario: Mode overrides model output budget

- **WHEN** a model declares `max_output_tokens = 4096` and a mode declares `max_output_tokens = 512`
- **THEN** the resolved `max_output_tokens` is `512`

#### Scenario: CLI flag overrides mode output budget

- **WHEN** a mode declares `max_output_tokens = 512` and the user passes `--max-output-tokens 200`
- **THEN** the resolved `max_output_tokens` is `200`

#### Scenario: max_context_tokens enforced at request build

- **WHEN** a mode declares `max_context_tokens = 1000` and the user passes a file whose estimated token count is `1500`
- **THEN** the system writes a budget-exceeded error to stderr and exits with code 1 (see the `inputs` capability for the estimation rule)

## REMOVED Requirements

### Requirement: User mode overrides (full replacement)

**Reason**: Mode resolution is now per-key deep-merge across builtin/provider/model layers (D1), not full replacement. Full replacement loses the ability to inherit a `system_prompt` from a built-in while overriding only `sampling`.
**Migration**: Users who previously declared a mode in `modes.json` that intentionally cleared a built-in field SHALL re-declare that field explicitly with the desired value (e.g., `system_prompt: ""` to clear it).
