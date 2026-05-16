## ADDED Requirements

### Requirement: Built-in sampling template catalog

The system SHALL ship with built-in sampling templates as package data under `llm_cli/sampling/builtin/*.json`. The initial catalog SHALL include templates derived from the Unsloth Qwen3.6 recommendations:

- `qwen3.6-thinking-general` — `temperature=1.0, top_p=0.95, top_k=20, min_p=0.0, presence_penalty=1.5`
- `qwen3.6-thinking-code` — `temperature=0.6, top_p=0.95, top_k=20, min_p=0.0, presence_penalty=0.0`
- `qwen3.6-instruct-general` — `temperature=0.7, top_p=0.8, top_k=20, min_p=0.0, presence_penalty=1.5`
- `qwen3.6-instruct-reasoning` — `temperature=1.0, top_p=0.95, top_k=20, min_p=0.0, presence_penalty=1.5`

Each template definition SHALL be a JSON object whose keys are sampling parameter names and whose values are the recommended values. Templates SHALL NOT contain non-sampling fields (no `system_prompt`, no `extra_body`, no `schema`).

#### Scenario: Built-in template usable out of the box

- **WHEN** a fresh install is invoked with `llm-cli --mode general --sampling-template qwen3.6-thinking-code "…"`
- **THEN** the system resolves the template's params without requiring any user-declared template

#### Scenario: Built-in template visible via list

- **WHEN** the user runs `llm-cli list templates`
- **THEN** the system prints at least the four Unsloth-derived built-in templates with their names and a `builtin` source label

### Requirement: User-declared sampling templates

The system SHALL accept a top-level `samplingTemplates` block in `models.json` mapping template names to sampling-parameter bundles. User-declared templates SHALL be merged with built-ins; on name collision, the user's definition SHALL fully replace the built-in.

#### Scenario: User-declared template usable

- **WHEN** `models.json` declares `samplingTemplates = {my-conservative: {temperature: 0.0, top_p: 0.5}}` and the user passes `--sampling-template my-conservative`
- **THEN** the resolved request has `temperature = 0.0` and `top_p = 0.5`

#### Scenario: User template overrides built-in on name collision

- **WHEN** the user declares `samplingTemplates.qwen3.6-thinking-code = {temperature: 0.1, top_p: 0.9}` (only those two keys)
- **THEN** the resolved template `qwen3.6-thinking-code` has EXACTLY those two keys (the built-in's keys for the same name are NOT inherited)

### Requirement: Sampling template references

A `sampling_template: <name>` key MAY appear in `provider.sampling`, `model.sampling`, or `mode.sampling` (the resolved mode at any of its three sub-layers). At sampling resolution time, the system SHALL replace each `sampling_template` reference with the template's params, merging them into the stack at the layer just below the layer where the reference appears.

If a referenced template name is not found in either built-ins or user-declared templates, the system SHALL exit with code 1 and a message naming the unknown template and listing the available names.

#### Scenario: Reference at model level expands below model layer

- **WHEN** a model declares `sampling = {sampling_template: "qwen3.6-thinking-code", temperature: 0.55}`
- **THEN** the resolved sampling contains `temperature = 0.55` AND every other key from `qwen3.6-thinking-code`; the explicit `temperature` in the model layer overrides the template's `temperature`

#### Scenario: Reference at provider level expands below provider layer

- **WHEN** a provider declares `sampling = {sampling_template: "qwen3.6-instruct-general"}` and a model under it declares `sampling = {temperature: 0.5}`
- **THEN** the resolved sampling contains every key from `qwen3.6-instruct-general` with `temperature` overridden to `0.5`

#### Scenario: Unknown template name is a hard error

- **WHEN** a model declares `sampling = {sampling_template: "no-such-template"}`
- **THEN** the system writes an error naming the unknown template and listing the available built-in and user-declared template names to stderr and exits with code 1

### Requirement: Templates contain sampling keys only

The system SHALL reject template definitions whose values include non-sampling fields (`system_prompt`, `user_prompt_template`, `schema`, `extra_body`, `requires_input`, `modes`). Validation SHALL be structural at config load time.

#### Scenario: Template with extra_body rejected

- **WHEN** `models.json` declares a template with an `extra_body` key
- **THEN** the system writes an error explaining that templates contain only sampling keys to stderr and exits with code 1
