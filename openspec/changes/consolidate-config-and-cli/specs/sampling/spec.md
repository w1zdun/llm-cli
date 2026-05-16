## MODIFIED Requirements

### Requirement: Resolution stack and deep-merge semantics

The system SHALL resolve effective sampling parameters by deep-merging the following layers in order (later layers override earlier layers per key):
1. `provider.sampling` from `models.json`.
2. Sampling template referenced by `provider.sampling.sampling_template`, expanded in place.
3. `model.sampling` from the chosen model entry.
4. Sampling template referenced by `model.sampling.sampling_template`, expanded in place.
5. `mode.sampling` from the resolved mode (where the mode itself is the result of merging built-in, provider-level, and model-level mode definitions per the `modes` capability).
6. Sampling template referenced by `mode.sampling.sampling_template`, expanded in place.
7. CLI flag overrides (`--temperature`, `--top-p`, `--top-k`, `--enable-thinking`, `--preserve-thinking`, `--sampling-template`, and any `--set key=value` pairs).

A `sampling_template: <name>` key at any of the layers 1, 3, or 5 expands BELOW the layer where it appears: the template's params merge into the stack as a layer between this one and the next-higher one, so explicit keys in the SAME layer still win over template values.

The same merge semantics SHALL apply to `extra_body` independently, except that `extra_body` does NOT participate in sampling-template expansion.

#### Scenario: CLI flag overrides mode sampling

- **WHEN** the `code` mode sets `temperature = 0.2` and the user passes `--temperature 0.0`
- **THEN** the resolved `temperature` is `0.0`

#### Scenario: Mode adds a key without removing provider keys

- **WHEN** the provider sets `top_k = 20` and the mode sets `temperature = 0.2`
- **THEN** the resolved sampling contains both `top_k = 20` and `temperature = 0.2`

#### Scenario: extra_body merged separately from sampling

- **WHEN** the provider sets `extra_body = {guided_decoding_backend = "xgrammar"}` and the mode sets `extra_body = {logit_bias = {...}}`
- **THEN** the resolved `extra_body` contains both keys

#### Scenario: Sampling template expanded then overridden by same-layer keys

- **WHEN** a model declares `sampling = {sampling_template: "qwen3.6-thinking-code", temperature: 0.55}`
- **THEN** the resolved sampling contains `temperature = 0.55` AND every other key from `qwen3.6-thinking-code` (`top_p = 0.95`, `top_k = 20`, `min_p = 0.0`, `presence_penalty = 0.0`)

### Requirement: Thinking control is direct sampling keys

The system SHALL treat `enable_thinking` (boolean) and `preserve_thinking` (boolean) as plain sampling keys. They participate in the four-layer resolution stack like any other sampling key.

At request-build time, when the resolved model has `thinkingFormat = "qwen-chat-template"`:
- The system SHALL remove `enable_thinking` and `preserve_thinking` from the resolved `sampling` dict.
- The system SHALL move their values into `extra_body.chat_template_kwargs.enable_thinking` and `extra_body.chat_template_kwargs.preserve_thinking` respectively (creating `chat_template_kwargs` if absent).
- Either key MAY be absent in the resolved sampling; only the present keys SHALL be moved.

For any other `thinkingFormat` (including `"none"` and `"openai-reasoning-effort"`), the system SHALL leave `enable_thinking` / `preserve_thinking` unchanged in the resolved request (passed through to the provider for handling).

For `thinkingFormat = "openai-reasoning-effort"`, the `reasoning_effort` plain sampling key SHALL be passed through to the top-level request body. No mapping table is involved.

#### Scenario: enable_thinking routed into chat_template_kwargs

- **WHEN** a mode sets `enable_thinking = false` and the model has `thinkingFormat = "qwen-chat-template"`
- **THEN** the outgoing request body has `extra_body.chat_template_kwargs.enable_thinking = false` and no top-level `enable_thinking` field

#### Scenario: preserve_thinking routed into chat_template_kwargs

- **WHEN** a mode sets `preserve_thinking = true` and the model has `thinkingFormat = "qwen-chat-template"`
- **THEN** the outgoing request body has `extra_body.chat_template_kwargs.preserve_thinking = true`

#### Scenario: Both thinking keys routed together

- **WHEN** a mode sets `enable_thinking = true` and `preserve_thinking = true` and the model has `thinkingFormat = "qwen-chat-template"`
- **THEN** the outgoing `extra_body.chat_template_kwargs` contains both keys with their boolean values

#### Scenario: reasoning_effort passed through for openai-reasoning-effort

- **WHEN** a mode sets `reasoning_effort = "high"` and the model has `thinkingFormat = "openai-reasoning-effort"`
- **THEN** the outgoing request body has a top-level `reasoning_effort = "high"` field

#### Scenario: thinkingFormat=none leaves keys untouched

- **WHEN** a mode sets `enable_thinking = false` and the model has `thinkingFormat = "none"`
- **THEN** the outgoing request body has top-level `enable_thinking = false` (no routing into `chat_template_kwargs`)

## ADDED Requirements

### Requirement: CLI flags for thinking control

The system SHALL accept `--enable-thinking / --no-enable-thinking` and `--preserve-thinking / --no-preserve-thinking` flags on the default (request) invocation. These flags SHALL merge into the CLI layer of the sampling stack as `enable_thinking` and `preserve_thinking` boolean values.

#### Scenario: --no-enable-thinking overrides mode default

- **WHEN** the resolved `code` mode has `enable_thinking = true` and the user passes `--no-enable-thinking`
- **THEN** the outgoing request body has `extra_body.chat_template_kwargs.enable_thinking = false` (assuming a Qwen model)

#### Scenario: --preserve-thinking flag sets the key

- **WHEN** the user passes `--preserve-thinking` against a Qwen model
- **THEN** the outgoing request body has `extra_body.chat_template_kwargs.preserve_thinking = true`

### Requirement: CLI `--sampling-template` flag

The system SHALL accept `--sampling-template <name>` as an optional flag on the default invocation. When present, the named template's params SHALL merge into the CLI layer of the sampling stack BELOW any other CLI flags (so `--temperature` still wins over a template's `temperature`).

#### Scenario: --sampling-template applies template values

- **WHEN** the user passes `--sampling-template qwen3.6-thinking-general` and no other sampling flags
- **THEN** the resolved request includes every param from that template

#### Scenario: --temperature beats template

- **WHEN** the user passes `--sampling-template qwen3.6-thinking-general --temperature 0.5`
- **THEN** the resolved `temperature = 0.5` (CLI flag wins over template), other template params unchanged

#### Scenario: Unknown template name is a hard error

- **WHEN** the user passes `--sampling-template not-a-real-template`
- **THEN** the system writes an error naming the unknown template and listing the available built-in and user-declared templates to stderr and exits with code 1

## REMOVED Requirements

### Requirement: Reasoning is a sampling key with model-mapped encoding

**Reason**: The `reasoning: off/low/medium/high/xhigh` abstraction and the per-model `thinkingLevelMap` indirection are gone. Thinking is now controlled by two direct boolean keys (`enable_thinking`, `preserve_thinking`) that route into the provider's chat-template kwargs without any mapping table. For OpenAI-style reasoning effort, the standard `reasoning_effort` sampling key passes through unchanged.
**Migration**: Replace any `sampling.reasoning = "off"` with `sampling.enable_thinking = false`. Replace any `sampling.reasoning = "low" | "medium" | "high" | "xhigh"` with `sampling.enable_thinking = true` (the granularity is gone; if you used different levels to mean different things, decide whether to set `preserve_thinking` differently per mode). For OpenAI-style models, replace with `sampling.reasoning_effort = "low" | "medium" | "high"` directly. Delete any `thinkingLevelMap` blocks from `models.json`.
