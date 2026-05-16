## Why

The current shape has several friction points that surface every time someone touches the config or runs the tool: modes live in a separate `modes.json` file (so per-model tuning means editing two files and keeping them in sync), thinking control goes through an abstract `thinkingLevelMap` indirection that doesn't match how Qwen3.6 (the primary local model) actually exposes thinking (it's just `enable_thinking: true|false` plus an optional `preserve_thinking`), every invocation forces the user to type `llm-cli run …` when `run` is the only verb that takes arguments anyway, images are base64-inlined into the request (bloating payloads enormously for local same-host servers that could just read a file path), and there is no per-mode budget on input or output token counts (so a small "summarize a tweet" mode and a "summarize a book" mode share the same untyped sampling stack). Now is the right time because the project just shipped v0.1 and has zero external users — breaking the config shape and CLI surface is free.

## What Changes

- **BREAKING**: Merge `modes.json` into `models.json`. Modes may be declared at four layers — built-in (shipped), global (top-level `modes:` in `models.json`), per-provider (`providers.<name>.modes`), per-model (`providers.<name>.models[].modes`). The four merge per-key with later layers winning (built-in → global → provider → model). A field absent at a more specific layer is inherited from the next-higher; a field present overrides; new fields extend the resolved set. This lets a user declare `code.system_prompt` once globally and only tweak `code.sampling.temperature` per model.
- **BREAKING**: Drop the `thinkingLevelMap` + `thinkingFormat: qwen-chat-template` indirection. Replace with two direct boolean knobs that map straight onto Qwen's chat-template kwargs: `enable_thinking` (turns the `<think>` block on/off) and `preserve_thinking` (keeps prior thinking traces in chat history). Both surface as plain sampling keys; they get routed into `chat_template_kwargs` at request-build time without any per-model mapping table.
- **BREAKING**: Drop the `run` subcommand. The default action becomes "run a request", so `llm-cli --mode code "…"` works directly. `list`, `ping`, and `show` stay as named subcommands.
- Add sampling templates — named bundles of recommended sampling params (e.g., `qwen3.6-thinking-general`, `qwen3.6-thinking-code`, `qwen3.6-instruct-general`, `qwen3.6-instruct-reasoning`) sourced from the Unsloth Qwen3.6 recommendations. A model, mode, or CLI flag (`--sampling-template <name>`) can reference one by name; the template merges into the sampling stack BELOW the model layer (so explicit per-key overrides still win).
- Ship built-in templates under `llm_cli/sampling/builtin/`. Users can declare custom templates inline under a top-level `samplingTemplates` key in `models.json`.
- **BREAKING**: Image inputs are passed BY PATH (`file:///abs/path`) by default instead of base64-inlined as data URLs. Each provider declares `file_passing: "path" | "inline"`; default is `"path"` for `llama.cpp`/`vllm`/`ollama` (same-host local servers) and `"inline"` for `openai-generic`. Rasterized PDF pages (`--pdf-strategy=images`) are written to a per-run temp directory and referenced by path under the same rule. Text and PDF-text content remain inlined (no `file://` convention exists for inline text in OpenAI chat schemas).
- Confirm and spec the existing multi-file behavior: any number of `@<path>` positional args are accepted, content array preserves their order, prompt appears last. This was already implemented but not previously specified.
- Add per-mode token budgets: `max_context_tokens` (refuses the request if the estimated input would exceed this budget) and `max_output_tokens` (becomes the resolved `max_tokens` / `compat.maxTokensField` sent to the provider). Both fields are optional and may live at provider, model, or mode level using the same per-key deep-merge stack.
- Add a per-mode `role` field (default `"user"`) that selects the OpenAI-style role for the message containing the assembled prompt + file inputs. A mode MAY declare `role: "developer"` for coding/instruction modes when the chosen model supports it. The model declares capability via `supports_developer_role: bool` (default `false`); a mode requesting `developer` against a model that does not support it fails fast with a clear error.

## Capabilities

### New Capabilities

- `sampling-templates`: Named, reusable bundles of sampling parameters. Built-ins ship with the package; users can declare custom ones in their config. Templates plug into the existing resolution stack as a new layer below model-level overrides.

### Modified Capabilities

- `config`: `models.json` schema gains a top-level `modes` block (global modes), nested `modes` per provider and per model, top-level `samplingTemplates` block, per-provider `file_passing` field, and `max_context_tokens` / `max_output_tokens` fields at every layer. `modes.json` is removed.
- `modes`: Modes are no longer loaded from a separate file. Built-in modes still exist (shipped as package data) and are merged with global, per-provider, and per-model modes from `models.json`. New precedence: builtin → global (top-level `modes`) → provider.modes → model.modes → CLI (later wins). Modes may declare `max_context_tokens` and `max_output_tokens`.
- `sampling`: `thinkingLevelMap` removed. Reasoning is controlled by `enable_thinking` and `preserve_thinking` plain sampling keys; routing into `chat_template_kwargs` happens automatically for models with `thinkingFormat: qwen-chat-template`. Sampling resolution gains a `sampling_template` lookup layer.
- `cli`: Default command (no subcommand) runs a request. `run` subcommand removed. `--sampling-template` flag added.
- `inputs`: Image inputs default to `file://` URLs (per-provider switch). Multi-file behavior formally specified. New `max_context_tokens` check before request build.
- `transport`: `max_output_tokens` (resolved) maps to the request body via `compat.maxTokensField`, replacing the previous `max_tokens` sampling key for budget intent (the plain `max_tokens` sampling key still works as a pass-through but the mode-level field is `max_output_tokens`).

## Impact

- **Config files** — every user's `~/.config/llm-cli/models.json` must be edited; `~/.config/llm-cli/modes.json` becomes dead and can be deleted. Migration is a manual one-time edit (no auto-migrator since there's only one known user).
- **Code** — `llm_cli/config/loader.py` (drop `load_modes`), `llm_cli/config/models_schema.py` (nest modes, drop `thinkingLevelMap`/`thinkingFormat`, add `samplingTemplates`), `llm_cli/config/modes_schema.py` (still used but loaded from nested data), `llm_cli/modes/registry.py` (consume merged modes from `ProvidersFile`), `llm_cli/resolve/reasoning.py` (delete; replaced by a thinner `llm_cli/resolve/thinking.py` that just routes the two plain keys), `llm_cli/resolve/sampling.py` (insert template-resolution layer), `llm_cli/__main__.py` (drop `run` subcommand, make it the default callback).
- **New module** — `llm_cli/sampling/templates.py` + `llm_cli/sampling/builtin/*.json` for shipped templates.
- **Built-in modes** — files under `llm_cli/modes/builtin/` keep their current shape (they're the "builtin" tier of mode merging).
- **Tests** — `tests/test_config.py` fixture (`pi_models.json`) regenerated with new shape; new test cases for template resolution and mode precedence.
- **Docs** — `README.md` config-example section rewritten; `openspec/changes/init-llm-cli/specs/` deltas applied via this change.
- **No remote/API impact** — request body sent to the LLM server is unchanged in shape; only the config and CLI surface change.
