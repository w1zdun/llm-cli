## MODIFIED Requirements

### Requirement: Provider parameter mapping (compat.param_mapping)

Each provider MAY declare a `compat.param_mapping: dict[str, str]` table that maps abstract parameter names (used in `models.json` and the CLI) to the wire-format field names expected by that provider's API. When serializing the outgoing request body, the system SHALL look up each abstract name in this table and write its value under the mapped key, omitting the abstract name from the payload.

If `compat.param_mapping` is absent or does not contain a mapping for a given abstract name, the system SHALL apply per-`provider_kind` defaults:

| `provider_kind`  | `max_output_tokens` →     |
| ---------------- | ------------------------- |
| `llama.cpp`      | `max_tokens`              |
| `vllm`           | `max_tokens`              |
| `ollama`         | `num_predict`             |
| `openai-generic` | `max_completion_tokens`   |

The mapping table SHALL apply only to top-level non-sampling fields; resolved `sampling` keys SHALL pass through unchanged (the existing "validation off — pass-through" contract).

The `max_output_tokens` value SHALL be drawn from the resolved `max_output_tokens` field (provider/model/mode/CLI stack) if present; if absent, from the resolved `sampling.max_tokens` key as a pass-through. If both are present, `max_output_tokens` SHALL win and `sampling.max_tokens` SHALL NOT also appear in the outgoing body.

#### Scenario: openai-generic default maps max_output_tokens to max_completion_tokens

- **WHEN** the provider has `provider_kind = "openai-generic"`, no `compat.param_mapping`, and resolved `max_output_tokens = 4096`
- **THEN** the outgoing body contains `max_completion_tokens: 4096` and no `max_tokens` or `max_output_tokens` field

#### Scenario: ollama default maps max_output_tokens to num_predict

- **WHEN** the provider has `provider_kind = "ollama"` and resolved `max_output_tokens = 1024`
- **THEN** the outgoing body contains `num_predict: 1024`

#### Scenario: Explicit mapping overrides the per-kind default

- **WHEN** the provider has `provider_kind = "openai-generic"`, `compat.param_mapping = {"max_output_tokens": "max_tokens"}`, and resolved `max_output_tokens = 2048`
- **THEN** the outgoing body contains `max_tokens: 2048` and no `max_completion_tokens` field

#### Scenario: max_output_tokens beats sampling.max_tokens

- **WHEN** the resolved `max_output_tokens = 1024` and the resolved `sampling.max_tokens = 2048`
- **THEN** the outgoing body contains the mapped field set to `1024` and no other max-tokens-related key

#### Scenario: Falls back to sampling.max_tokens when max_output_tokens absent

- **WHEN** the resolved `max_output_tokens` is not set and the resolved `sampling.max_tokens = 2048`
- **THEN** the outgoing body contains the mapped field set to `2048`

## ADDED Requirements

### Requirement: Outgoing message shape

The `messages` array in the outgoing chat completions request SHALL be assembled in this order:

1. If the resolved mode declares a non-empty `system_prompt`, prepend `{"role": "system", "content": "<system_prompt>"}` as a single text-string content (NOT a typed-array content — the system message uses the simple string form for maximum provider compatibility).
2. Append exactly one prompt message with:
   - `role` set to `"user"` or `"developer"` per the resolved mode's `role` field (see the `modes` capability).
   - `content` set to an ARRAY of typed content blocks, ordered as: file inputs in the order given on the command line, then the literal prompt string (if any) as a trailing `{"type": "text", "text": "<prompt>"}` block.

Each content block in the array SHALL be one of:
- `{"type": "text", "text": "<string>"}` — for text-file inlining (with the `=== <basename> ===\n<content>` header) or for the literal prompt.
- `{"type": "image_url", "image_url": {"url": "<url>"}}` — for image inputs and rasterized PDF pages. The `<url>` is either a `data:<mime>;base64,...` URL (inline mode) or a `file:///<absolute-path>` URL (path mode) per the provider's `file_passing` setting.

When there are no file inputs and no prompt string, the system SHALL exit with code 1 (a chat completion with an empty content array is rejected before assembly).

#### Scenario: Single-image + text request shape

- **WHEN** the user runs `llm-cli --mode image @screenshot.png "describe this"` against a vision model
- **THEN** the outgoing `messages` array contains the system message (if the mode has one) followed by a single message whose `content` array is `[{"type": "image_url", ...}, {"type": "text", "text": "describe this"}]` in that order

#### Scenario: Multi-image comparison shape

- **WHEN** the user runs `llm-cli --mode image @before.png @after.png "compare these screenshots"` against a vision model
- **THEN** the outgoing prompt message's `content` is the array `[{"type": "image_url", "image_url": {"url": "<before>"}}, {"type": "image_url", "image_url": {"url": "<after>"}}, {"type": "text", "text": "compare these screenshots"}]`

#### Scenario: Developer role used for prompt message

- **WHEN** the resolved mode declares `role = "developer"` and the model declares `supports_developer_role = true`
- **THEN** the outgoing prompt message has `role = "developer"`; the system message (if present) keeps `role = "system"`

#### Scenario: Empty input rejected before send

- **WHEN** the user runs `llm-cli --mode general` with no positional arguments at all
- **THEN** the system writes an error explaining that a prompt or at least one file input is required, makes no HTTP call, and exits with code 1
