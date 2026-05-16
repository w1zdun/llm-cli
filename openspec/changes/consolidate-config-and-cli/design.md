## Context

The v0.1 implementation split user-facing configuration across `models.json` (providers, models) and `modes.json` (modes). Both files merge into a four-layer sampling stack (`provider → model → mode → CLI`). Three pain points motivated this change:

1. **Two-file config**. Per-model tuning (e.g., "for Qwen3.6 in code mode, use `temperature=0.1`") requires editing both files and keeping them mentally linked. There is no place to say "this mode means *this* for *this* model".
2. **`thinkingLevelMap` is a wrong abstraction**. It pretends reasoning is a quantitative scale (`off/low/medium/high/xhigh`) that maps to per-model values, but Qwen3.6 (the only locally-hosted model in use) exposes thinking as plain booleans: `enable_thinking: true|false` and `preserve_thinking: true|false`. The map indirection adds friction with no payoff.
3. **`run` is a verbose default**. The CLI has four verbs (`run`, `list`, `ping`, `show`), but `run` is what every actual invocation does. `llm-cli run --mode code "…"` could just be `llm-cli --mode code "…"`.

A fourth need surfaced from the Unsloth Qwen3.6 docs: there are 4+ canonical sampling-parameter bundles (thinking-general, thinking-code, instruct-general, instruct-reasoning) that any Qwen3.6 user wants to reach for. Copying those numbers into every mode definition is exactly the kind of duplication that drifts.

## Goals / Non-Goals

**Goals:**
- One file (`models.json`) defines providers, models, modes, and sampling templates.
- Modes can be declared per provider AND per model. Model-level wins per key when both define the same mode.
- Thinking control is direct: `enable_thinking` and `preserve_thinking` are plain sampling keys. The model declares `thinkingFormat: qwen-chat-template` once; the resolver routes those two keys into `extra_body.chat_template_kwargs` at request-build time. No more `thinkingLevelMap`.
- Sampling templates are a new layer in the resolution stack — referenced by name, defined once, reused across modes/models.
- Default CLI action runs a request. `llm-cli --mode code "…"` works. The other verbs (`list`, `ping`, `show`) stay as named subcommands.

**Non-Goals:**
- Backwards compatibility with the existing `modes.json` shape. The repo has one user (the author); migration is a one-time manual edit.
- A general-purpose templating system. Templates contain only sampling params, not system prompts or schemas (those are mode-level).
- Auto-detecting Qwen vs. other models. The user keeps declaring `thinkingFormat` per model; the difference is that the value-encoding map is gone.
- Validating template names at config load against the built-in set. References are resolved lazily; a missing name fails at request time with a clear error.

## Decisions

### D1. Merge modes into `models.json` with four-level scoping

**Decision:** Move modes inside `models.json` at four layers. From most general to most specific:

1. **Built-in** — shipped as package data under `llm_cli/modes/builtin/*.json` (e.g. `code`, `general`, `ocr`, …). Defines the "stock" definition of each mode.
2. **Global** — top-level `modes` object in `models.json`. Applies regardless of which provider/model is selected. Common case: declare a mode's `system_prompt` once here, never repeat per provider.
3. **Per-provider** — `providers.<name>.modes` object. Inherits from global, overrides keys for that provider.
4. **Per-model** — `providers.<name>.models[].modes` object. Most specific; inherits from provider, overrides keys for that model.

Resolution for mode `M`:
```
result = builtin.M ⊕ global.M ⊕ provider.modes.M ⊕ model.modes.M
```
where `⊕` is the same per-key deep-merge used for sampling. Later layers win per key; absent fields inherit; new fields extend. So a model-level mode can override one sampling key while inheriting `system_prompt` from global and `extra_body` from provider.

**Alternatives considered:**
- *Three layers without "global"* — rejected: forces declaring `code.system_prompt` once per provider, which is the same duplication problem `modes.json` used to solve.
- *Per-model only* — rejected: forces duplicating the same mode across every model under a provider when 90% of the time the provider-level definition is what you want.
- *Per-provider only* — rejected: defeats the whole point, since you still can't say "for THIS model in THIS mode, override temperature".

**Why:** Matches how users think in three dimensions: "what the mode IS" (global), "what this server family wants" (provider), "what this specific model wants" (model). Each layer is optional; users can declare zero, one, or all four.

### D2. Drop `thinkingLevelMap`; thinking control is two plain sampling keys

**Decision:** Remove the `reasoning: off/low/medium/.../xhigh` abstraction and the `thinkingLevelMap` indirection. Introduce two plain sampling keys:

- `enable_thinking: bool` — turns the model's `<think>` block on or off.
- `preserve_thinking: bool` — keeps prior `<think>` traces in chat history across turns.

Routing rule: when the resolved model declares `thinkingFormat: qwen-chat-template`, the resolver moves these two keys (if present) out of `sampling` and into `extra_body.chat_template_kwargs.{enable_thinking, preserve_thinking}` before request build. For any other `thinkingFormat`, the keys are passed through unchanged (provider-side handling).

The `openai-reasoning-effort` format is preserved as a separate concern: a model with that format SHOULD use the standard sampling key `reasoning_effort` directly (a string like `"low" | "medium" | "high"`), which the resolver passes through to the top-level request body. No mapping table is needed.

**Alternatives considered:**
- *Keep `reasoning` as an abstract key but drop the map (auto-encode based on `thinkingFormat`)* — rejected: still hides the actual control surface from the user. If they want `enable_thinking=false`, they should write `enable_thinking: false`, not `reasoning: "off"` and trust a map.
- *Pure pass-through with no resolver routing* — rejected: forces every user/mode to type `extra_body.chat_template_kwargs.enable_thinking` explicitly, which is what Unsloth's CLI uses but is ugly inline.

**Why:** Matches Unsloth's documented Qwen3.6 control surface exactly. One concept per key. The routing is a thin one-way transform; no bidirectional mapping table to maintain.

### D3. Sampling templates as a new resolution layer

**Decision:** Add a top-level `samplingTemplates: { <name>: { …params… } }` block in `models.json`. Ship built-in templates as package data under `llm_cli/sampling/builtin/*.json` covering the Unsloth Qwen3.6 recommendations:

- `qwen3.6-thinking-general` — `temperature=1.0, top_p=0.95, top_k=20, min_p=0.0, presence_penalty=1.5`
- `qwen3.6-thinking-code` — `temperature=0.6, top_p=0.95, top_k=20, min_p=0.0, presence_penalty=0.0`
- `qwen3.6-instruct-general` — `temperature=0.7, top_p=0.8, top_k=20, min_p=0.0, presence_penalty=1.5`
- `qwen3.6-instruct-reasoning` — `temperature=1.0, top_p=0.95, top_k=20, min_p=0.0, presence_penalty=1.5`

User-declared templates in `models.json` merge with built-ins (user wins on name collision, full replacement, same rule as modes).

A `sampling_template: <name>` key may appear in `provider.sampling`, `model.sampling`, `mode.sampling`, or as a CLI flag `--sampling-template <name>`. At resolution time, every `sampling_template` reference is expanded into its constituent params and merged into the stack at a layer JUST BELOW the layer where the reference appears. Example:

```
model.sampling = { sampling_template: "qwen3.6-thinking-code", temperature: 0.55 }
```
resolves to:
```
{ temperature: 0.55, top_p: 0.95, top_k: 20, min_p: 0.0, presence_penalty: 0.0 }
```
(model's explicit `temperature: 0.55` beats the template's `0.6`).

**Alternatives considered:**
- *Templates as a sibling top-level concept invocable only by CLI flag* — rejected: half the value is being able to say "this model always uses this template by default".
- *Built-ins only, no user templates* — rejected: users will inevitably want their own bundles.
- *No built-ins, library of community templates discovered remotely* — rejected: out of scope for a single-shot local CLI.

**Why:** Eliminates the "copy these five numbers into every mode" problem. The Unsloth recommendations become a first-class citizen, not a comment in a README.

### D4. Default CLI action runs a request; `run` subcommand removed

**Decision:** Move the entire `run` parameter surface up to the Typer callback. `llm-cli` with positional args + `--mode` flag runs a request. `list`, `ping`, `show` remain explicit subcommands. `llm-cli` with no arguments still prints usage and exits 1.

The implementation: convert the existing `@app.command() run(...)` into the root callback. Typer supports this via `@app.callback(invoke_without_command=True)` combined with sub-command registration. The `--version` callback stays as `--version` / `-V` on the root.

**Alternatives considered:**
- *Add an alias so `llm-cli "…"` is a shortcut for `llm-cli run "…"`* — rejected: two ways to do the same thing.
- *Replace Typer with argparse* — rejected: Typer's callback + subcommand support handles this cleanly; switching frameworks is unrelated churn.

**Why:** Every actual invocation in shell scripts and skills is `llm-cli run …`. Saving the user three characters per call adds up; more importantly, it stops `run` from looking like a meaningful distinction from `list`/`ping`/`show`. It also makes the tool more pipeline-friendly: `cat foo | llm-cli --mode summarize` reads naturally.

### D5. Image inputs by path (file:// URLs) on local providers

**Decision:** For every provider, declare a `file_passing` field with values `"path"` or `"inline"`. Default is `"path"` for `provider_kind ∈ {llama.cpp, vllm, ollama}` and `"inline"` for `openai-generic`. When `"path"`, image content entries become:

```json
{"type": "image_url", "image_url": {"url": "file:///abs/path/to/image.png"}}
```

instead of the current data-URL form. The CLI resolves the path to an absolute path before sending. For PDF rasterization under `--pdf-strategy=images`, the resolver writes each rasterized page to a per-run temp directory (`tempfile.TemporaryDirectory()` lifetime-scoped to the request) and references the temp paths via `file://`. Text content and PDF-text are unchanged (always inlined as `{"type": "text", "text": "..."}`).

**Alternatives considered:**
- *Always inline (status quo)* — rejected: a 3MB PNG becomes 4MB+ base64 + JSON overhead, multiplied per request, multiplied per page of a PDF. Local llama.cpp servers can `read()` directly.
- *Always path* — rejected: breaks remote `openai-generic` targets which can't reach the user's filesystem.
- *Auto-detect per-provider* — rejected: too magical. Explicit field makes the intent visible.

**Why:** For a tool whose primary use case is `localhost:8080` / LAN llama.cpp, base64-bloating is pure waste. The per-provider knob lets remote endpoints opt out.

### D6. Per-mode `max_context_tokens` and `max_output_tokens` with generic provider param mapping

**Decision:** Add two optional budget fields to provider/model/mode definitions, resolvable through the standard deep-merge stack:

- `max_context_tokens: int` — upper bound on the estimated input size. Before sending the request, the system estimates the token count of the final `messages` array (rough heuristic: `len(serialized_text) / 4` for text content, `1024` per image entry — both numbers configurable later if needed). If the estimate exceeds `max_context_tokens`, the system exits with code 1 and a message naming the budget and the estimate. This field is **client-side only** — it never reaches the provider.
- `max_output_tokens: int` — the budget for the model's response. The system writes this value into the request body under the field name resolved via the provider's parameter-mapping table (see below). It replaces any plain `max_tokens` sampling key for the same effect, but the plain sampling key is still respected as a pass-through (later-layer wins as usual).

Both fields participate in the four-layer sampling-style stack (`provider → model → mode → CLI`), but they live OUTSIDE `sampling` (because they're budgets, not generation params). CLI flags: `--max-context-tokens <int>` and `--max-output-tokens <int>`.

**Provider parameter mapping.** Replace the previous `compat.maxTokensField` with a generic `compat.param_mapping: dict[str, str]` that maps abstract CLI/config parameter names to the provider's wire-format field names. This lets a single concept (`max_output_tokens`) map to whatever each provider expects without sprinkling per-parameter flags through `compat`. Built-in defaults applied per `provider_kind` if `param_mapping` is absent:

| provider_kind     | `max_output_tokens` maps to | rationale                                       |
| ----------------- | --------------------------- | ----------------------------------------------- |
| `llama.cpp`       | `max_tokens`                | standard OpenAI shape                           |
| `vllm`            | `max_tokens`                | standard OpenAI shape                           |
| `ollama`          | `num_predict`               | ollama-specific (matches their API)             |
| `openai-generic`  | `max_completion_tokens`     | required for o-series and GPT-4.1+; older models accept it as alias |

User overrides apply per-provider:

```jsonc
{
  "providers": {
    "legacy-openai": {
      "provider_kind": "openai-generic",
      "compat": { "param_mapping": { "max_output_tokens": "max_tokens" } }
    }
  }
}
```

When `max_output_tokens` is resolved, the system looks up `compat.param_mapping["max_output_tokens"]` (falling back to the per-kind default) and writes the resolved value to the request body under THAT key, omitting the abstract name from the wire payload. The mapping table is consulted only for non-sampling top-level fields; sampling keys pass through unchanged.

**Alternatives considered:**
- *Real tokenizer per model* — rejected for v0.2: requires loading the model's tokenizer (download, hash check). The character-count heuristic is good enough to catch egregious oversizes; precise counting can come later behind a `--tokenizer` flag.
- *Soft budgets that auto-truncate* — rejected: truncation hides intent. A hard error makes the user fix the input or raise the limit.
- *Keep `maxTokensField` as a single-purpose field* — rejected: the user explicitly asked for a generic mapping so future renames (e.g., a provider that uses `output_length`) don't require a code change. One mapping table covers all current and future renames.
- *Apply param_mapping to sampling keys too* — rejected: sampling is already a pass-through; remapping it would conflict with the "validation off — pass-through" contract and surprise users.

**Why:** Modes encode intent ("quick classify", "long-form summarize"); each intent has a natural budget. Surfacing those budgets as first-class fields stops them from leaking into the sampling stack and getting overridden by accident. The generic `param_mapping` keeps the abstract names stable across providers and avoids a per-rename `compat.fooField` field for every future quirk.

### D7. Migration: one breaking edit, no compat shim

**Decision:** Ship the new shape with no backwards-compatibility code path. Users (currently: the author) update their `~/.config/llm-cli/models.json` once, delete `modes.json`, and move on. The previous `init-llm-cli` change can be referenced by anyone who cloned the repo at v0.1.

**Why:** Zero external users at the time of this change. A compat layer would carry forward two of the three problems (`thinkingLevelMap` and split files) into the codebase, defeating the cleanup.

### D8. Per-mode `role` with model capability check

**Decision:** Add a `role: "user" | "developer"` field to mode definitions, default `"user"`. The system uses this value as the `role` of the message containing the assembled prompt + file inputs (i.e. the non-system message). Models declare capability with `supports_developer_role: bool` (default `false`). At request build time, if the resolved mode declares `role = "developer"` and the model has `supports_developer_role = false`, the system exits with code 1 and a message naming the mode, the model, and the missing capability.

The `system` message (when a mode declares `system_prompt`) keeps `role: "system"` unchanged. Only the second message's role is affected. The `assistant` role is irrelevant here (single-shot, no history).

**Alternatives considered:**
- *Allow any string and pass through* — rejected: typos like `role: "developler"` would only surface as a 400 from the server. An explicit capability flag catches mistakes at config time.
- *Maintain a list `supported_roles: ["user", "developer"]` on each model* — over-engineered for a single optional role. If more roles emerge (e.g. `tool`), revisit.
- *Auto-detect from model id strings* — magical and brittle. Capability is a config concern, not a code concern.

**Why:** The OpenAI-style `developer` role is the canonical way to signal "this is an instruction, not a chat turn" on newer models (GPT-4.1+, o-series). Coding/extract/classify modes benefit; image-description chat does not. Making it a per-mode field keeps the choice next to the system prompt.

### D9. Multi-file inputs: confirm and formalize

**Decision:** The existing multi-input behavior (any number of `@path` args, content array preserves order, prompt appears last) is correct and stays. No code change; the change here is purely specification — adding explicit scenarios to the `inputs` spec so the contract is testable.

**Why:** This was implemented by accident-of-design and never spec'd. With the broader rework happening, codify it so a future refactor can't silently regress.

## Risks / Trade-offs

- **[Lost flexibility from removing `thinkingLevelMap`]** — Other models in the future may expose thinking as a string scale (`low/medium/high`) rather than a boolean. → **Mitigation:** the `reasoning_effort` key already covers that case (openai-style). For genuinely new formats, the resolver gets a new branch — but that's the same shape as `qwen-chat-template` routing, just a different field.

- **[`run` default may collide with future subcommands]** — Adding a subcommand named `debug` or `eval` later would shadow positional prompts that happen to equal those words. → **Mitigation:** Typer's behavior in this case is documented: bare-word positionals are treated as the subcommand when they match; users with such prompts can prefix them (`-- debug` or quote). The set of subcommands is small (currently 3, max foreseen ~5) so collision risk is low.

- **[Mode-merge precedence is per-key — easy to misread]** — A user who declares `code` at both provider and model level may not expect that omitting `system_prompt` at model-level INHERITS the provider's prompt. → **Mitigation:** the same semantics already govern sampling, so behavior is consistent within the project. Document with an example.

- **[Sampling-template name resolution is lazy]** — A typo in `sampling_template: "qwen3.6-thiking-code"` only surfaces at request build, not at config load. → **Mitigation:** acceptable cost — config load stays simple, and the error message at build time clearly names the unknown template and lists known ones.

- **[Built-in templates may drift from upstream]** — Unsloth could update their Qwen3.6 recommendations. → **Mitigation:** built-in templates carry a comment in their JSON header citing the source and date. Users can always override with custom templates.

## Migration Plan

1. **Land the breaking changes in a single commit series** (see tasks.md). Old config files become invalid at the same moment the new code lands; there is no in-between state.
2. **Update `tests/fixtures/pi_models.json`** to the new shape. Tests must pass against the new shape only.
3. **Author's own `~/.config/llm-cli/models.json`** is edited by hand (separate from this change). Old `modes.json` deleted.
4. **README** rewritten with the new config example before the next push to origin.

Rollback: this change is a single feature branch. If something breaks before publication, revert to `main@a86d36e` (the current MIT-license commit) and the prior shape returns intact.

## Open Questions

- Should `--sampling-template` on the CLI MERGE INTO or REPLACE the model's resolved template? Current decision: merge (it adds another layer at the top of the stack). If the model has `qwen3.6-thinking-code` and the user passes `--sampling-template qwen3.6-instruct-general`, the result merges both — which is rarely useful. **Open**: should the CLI flag REPLACE any template reference further down the stack? Lean toward replace, but leaving open until first real use surfaces a preference.
- Should built-in templates be discoverable via `llm-cli list templates`? Probably yes for symmetry with `list modes`. Listed in tasks.
