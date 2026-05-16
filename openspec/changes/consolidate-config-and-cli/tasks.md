## 1. Config schema changes

- [x] 1.1 In `llm_cli/config/models_schema.py`: add `file_passing: Literal["path", "inline"] | None` to `Provider`, with a `model_validator` filling the per-kind default at load time. Replace `Compat.max_tokens_field` with `Compat.param_mapping: dict[str, str] | None`. Implement `compat_param_mapping_resolved(provider)` returning the merged per-kind-default + user-override mapping.
- [x] 1.2 In `Provider`: add `max_context_tokens: int | None` and `max_output_tokens: int | None`
- [x] 1.3 In `Provider`: add `modes: dict[str, Mode] | None` (re-using `Mode` from `modes_schema`)
- [x] 1.4 In `Model`: add `max_context_tokens: int | None`, `max_output_tokens: int | None`, `modes: dict[str, Mode] | None`
- [x] 1.5 In `Model`: remove `thinking_level_map` and the `_VALID_INPUTS`-style enforcement of the legacy field; add an explicit `model_validator` that rejects `thinkingLevelMap` with a clear error
- [x] 1.6 In `ProvidersFile`: add `sampling_templates: dict[str, dict[str, Any]] | None = Field(alias="samplingTemplates")` and `modes: dict[str, Mode] | None` (the global mode layer)
- [x] 1.7 In `Model`: add `supports_developer_role: bool = False`
- [x] 1.8 In `Mode` (`config/modes_schema.py`): add `max_context_tokens`, `max_output_tokens`, `role: Literal["user", "developer"] = "user"`
- [x] 1.9 Reject non-sampling fields in `samplingTemplates` entries (use a separate `SamplingTemplate` pydantic type, distinct from `Mode`)
- [x] 1.10 Delete `llm_cli/config/loader.py` `load_modes()` function and its callers; `modes.json` is no longer read

## 2. Modes registry

- [x] 2.1
- [x] 2.2
- [x] 2.3

## 3. Sampling templates

- [x] 3.1
- [x] 3.2
- [x] 3.3
- [x] 3.4
- [x] 3.5

## 4. Sampling resolution

- [x] 4.1
- [x] 4.2
- [x] 4.3
- [x] 4.4

## 5. Inputs: file-by-path

- [x] 5.1
- [x] 5.2
- [x] 5.3
- [x] 5.4 Update relevant existing tests to expect `file://` URLs by default (after the fixture is updated to the new shape)

## 6. Inputs: token budget

- [x] 6.1
- [x] 6.2 In `__main__.py` (the request flow), after `build_user_message` and before `client.post`: if resolved `max_context_tokens` is set, compute the estimate, abort with code 1 if exceeded
- [x] 6.3 In `--dry-run`: include `_estimated_input_tokens` in the printed JSON when `max_context_tokens` is set (otherwise omit)

## 7. Transport: max_output_tokens

- [x] 7.1
- [x] 7.2
- [x] 7.3
- [x] 7.4

## 8. CLI surface

- [x] 8.1 In `llm_cli/__main__.py`: convert `@app.command() def run(...)` to the root callback via `@app.callback(invoke_without_command=True)`. Move all `run` parameters onto the callback signature.
- [x] 8.2 Remove the `run` command registration. Keep `list`, `ping`, `show` as named subcommands.
- [x] 8.3 Add new flags: `--enable-thinking / --no-enable-thinking`, `--preserve-thinking / --no-preserve-thinking`, `--sampling-template <name>`, `--max-context-tokens <int>`, `--max-output-tokens <int>`
- [x] 8.4 Update `--version` callback to still work on the new root layout
- [x] 8.5 Update `[project.scripts]` in `pyproject.toml` to point at the new entry (`llm-cli = "llm_cli.__main__:main"` stays — only the internal Typer wiring changes)
- [x] 8.6 Add `list templates` subcommand in `list_command` that prints `<name>  (<source>)` per row

## 8b. Request shape and role

- [x] 8b.1 In `__main__.py` (or a dedicated `llm_cli/transport/messages.py`): build the prompt message with `role` taken from the resolved mode's `role` field (default `"user"`)
- [x] 8b.2 Before building, if mode `role = "developer"` and the model has `supports_developer_role = false`, exit code 1 with a clear error naming both
- [x] 8b.3 Ensure the system message (when `mode.system_prompt` is set) uses the simple `content: "<string>"` form (NOT a typed array) for maximum compatibility
- [x] 8b.4 Ensure the prompt message's `content` is ALWAYS a typed array (never a bare string), regardless of whether it contains images
- [x] 8b.5 Reject empty content (no file inputs AND no prompt string) before sending: exit code 1 with a clear error

## 9. Resolution wiring in **main**

- [x] 9.1 Replace `from llm_cli.config.loader import load_models, load_modes` with `load_models` only
- [x] 9.2 After `select_provider` + `select_model`, call the new `resolve_modes(providers_file, provider_name, selected_model)` (which internally merges builtin → global → provider → model layers) to get the mode map
- [x] 9.3 Resolve sampling templates via `resolve_templates(providers_file)` and pass to `resolve_sampling`
- [x] 9.4 Compute resolved `max_context_tokens` and `max_output_tokens` via the same deep-merge stack (provider → model → mode → CLI flags); pass both to the appropriate downstream call (budget check, transport build)
- [x] 9.5 Wire `--enable-thinking`/`--preserve-thinking` / `--sampling-template` CLI flags into the CLI layer of `resolve_sampling`
- [x] 9.6 Replace the `encode_reasoning(...)` call with `route_thinking(model, sampling, extra_body)` from the new `resolve/thinking.py`

## 10. Built-in modes

- [x] 10.1 Review each file under `llm_cli/modes/builtin/` for references to `reasoning: ...` keys; rewrite to `enable_thinking` (and optionally `preserve_thinking`) per design D2
- [x] 10.2 Where appropriate, add `max_output_tokens` defaults to small modes (e.g., `classify`, `ocr`) and a generous `max_context_tokens` to all (e.g., `32000`) so they remain useful out of the box
- [x] 10.3 No file rename, no schema change to the built-in files beyond field replacements

## 11. Tests

- [x] 11.1 Update `tests/fixtures/pi_models.json` to the new shape: nested `modes` under provider, no `modes.json` referenced, no `thinkingLevelMap`, `samplingTemplates` block included, `file_passing` declared explicitly on at least one provider
- [x] 11.2 Update existing `tests/test_config.py` cases that read the old fixture; add cases for mode resolution across `builtin/provider/model` layers
- [x] 11.3 New `tests/test_sampling_templates.py`: built-in load, user override on name collision, reference expansion (model-layer, provider-layer), unknown-template error
- [x] 11.4 New `tests/test_thinking_routing.py`: keys routed to `chat_template_kwargs` for `qwen-chat-template`, untouched for other formats, both keys present together
- [x] 11.5 New `tests/test_inputs_path.py`: image returns `file://` URL on path-mode provider, returns `data:` URL on inline-mode provider, missing file rejected before send
- [x] 11.6 New `tests/test_budget.py`: estimate counts text correctly, counts images at 1024, over-budget aborts with exit 1
- [x] 11.7 New `tests/test_cli_default.py`: `llm-cli --mode general "hi"` works without `run`; `llm-cli list templates` exits 0; `llm-cli` with no args exits 1
- [x] 11.8 New `tests/test_modes_resolution.py`: four-layer merge (builtin/global/provider/model); fields from each layer survive when not overridden; specific layer wins on conflict
- [x] 11.9 New `tests/test_role.py`: mode `role: "developer"` produces `role = "developer"` on the prompt message when model supports it; rejected with exit 1 when the model doesn't support it
- [x] 11.10 New `tests/test_message_shape.py`: system message uses string content, prompt message uses typed-array content even for text-only; empty content rejected before send

## 12. Documentation

- [x] 12.1 Rewrite the `models.json` example in `README.md` to show the new shape (nested modes, `samplingTemplates`, `file_passing`, `max_context_tokens`/`max_output_tokens`)
- [x] 12.2 Replace every `llm-cli run …` example with `llm-cli …` (drop the `run` subcommand)
- [x] 12.3 Add a "Migration from v0.1" section to README covering: split into `models.json` only, `thinkingLevelMap` → `enable_thinking`/`preserve_thinking`, `run` removal
- [x] 12.4 Document built-in sampling templates with their values and the Unsloth source URL

## 13. Manual acceptance

- [ ] 13.1 Edit personal `~/.config/llm-cli/models.json` to the new shape; delete `modes.json`
- [ ] 13.2 Run `llm-cli --mode code "write a python fizzbuzz"` (no `run`) and confirm a normal text response
- [ ] 13.3 Run `llm-cli --mode ocr @some.png` against a Qwen3.6 model with `file_passing = "path"` and confirm the request body in `--dry-run` shows a `file://` URL, not base64
- [ ] 13.4 Run `llm-cli --mode summarize --sampling-template qwen3.6-instruct-general @long-doc.md` and confirm template params show in `--dry-run`
- [ ] 13.5 Run `llm-cli --mode ocr --max-context-tokens 100 @huge.pdf` and confirm a budget-exceeded error with exit code 1
- [ ] 13.6 Run `llm-cli list templates` and confirm the 4 built-ins plus any user-declared appear
- [ ] 13.7 Run `llm-cli --mode general --enable-thinking "think about this"` against Qwen3.6 and confirm `chat_template_kwargs.enable_thinking = true` in the dry-run output
