## 1. Project scaffolding

- [x] 1.1 Create `pyproject.toml` with `[project]` metadata, Python `>=3.11`, pinned dependencies (`httpx`, `typer`, `pydantic`, `jsonschema`, `pymupdf`, `pillow`, `pyjson5`, `jinja2`), and `[project.scripts] llm-cli = "llm_cli.__main__:app"`
- [x] 1.2 Create `llm_cli/` package directory with empty `__init__.py` and `__main__.py` containing a `typer.Typer()` instance named `app`
- [x] 1.3 Add `ruff` config (line width 80) to `pyproject.toml`
- [x] 1.4 Verify `uv tool install ~/gity/llm-cli` installs and `llm-cli --help` runs

## 2. Config loading

- [x] 2.1 Implement `llm_cli/config/paths.py`: resolve XDG config and data paths (`~/.config/llm-cli`, `~/.local/share/llm-cli`); create data dir with mode `0700` on first use
- [x] 2.2 Implement `llm_cli/config/jsonc.py`: read-and-parse helper wrapping `pyjson5.decode`, returning typed errors with file path and line number
- [x] 2.3 Implement `llm_cli/config/models_schema.py`: Pydantic models for `ProvidersFile`, `Provider`, `Model`, including key aliasing (`baseUrl`↔`base_url`, `contextWindow`↔`context_window`, `thinkingFormat`/`thinkingLevelMap` kept camelCase)
- [x] 2.4 Implement `llm_cli/config/modes_schema.py`: Pydantic models for `Mode` and `ModesFile`
- [x] 2.5 Implement `llm_cli/config/loader.py`: `load_models()` and `load_modes()` returning typed objects; missing `models.json` is a hard error, missing `modes.json` falls back to built-ins only
- [x] 2.6 Write unit tests for config loading covering pi-shaped fixtures, malformed JSONC, missing required fields, and camelCase/snake_case aliases

## 3. Built-in modes catalog

- [x] 3.1 Create `llm_cli/modes/builtin/` directory with JSONC files for `code`, `general`, `design`, `image`, `ocr`, `summarize`, `classify`, `extract`
- [x] 3.2 Implement `llm_cli/modes/registry.py`: load built-in modes from package data, merge with user-defined modes (user wins on name collision)
- [x] 3.3 Define sampling values and system prompts per mode (per design.md mode catalog: `code` temp 0.2, `general` temp 0.6, `design` temp 0.9, `image` temp 0.3, `ocr` temp 0.0 with bound `{text: str}` schema, etc.)
- [ ] 3.4 Write a snapshot test that `llm-cli list modes` prints all built-in mode names

## 4. Resolution stack

- [x] 4.1 Implement `llm_cli/resolve/deep_merge.py`: per-key deep-merge for nested dicts (last writer wins per key)
- [x] 4.2 Implement `llm_cli/resolve/sampling.py`: merge `provider.sampling` → `model.sampling` → `mode.sampling` → CLI `--temperature/--top-p/--top-k/--set` flags
- [x] 4.3 Implement `llm_cli/resolve/extra_body.py`: same four-layer merge for `extra_body`
- [x] 4.4 Implement `llm_cli/resolve/cli_overrides.py`: parse `--set key=value` flags, JSON-decode value with string fallback, expand dotted keys into nested objects
- [x] 4.5 Implement `llm_cli/resolve/reasoning.py`: look up `reasoning` level in `model.thinkingLevelMap`; encode per `thinkingFormat` (`qwen-chat-template` → `extra_body.chat_template_kwargs.enable_thinking`; `openai-reasoning-effort` → top-level `reasoning_effort`; `none` → drop); hard error on missing/null mapping
- [ ] 4.6 Write unit tests for resolution stack (each layer, deep merge, reasoning mapping, error on unsupported level)

## 5. Input handling

- [x] 5.1 Implement `llm_cli/inputs/parser.py`: parse positional args into file-input list and literal prompt; handle `\@` escape
- [x] 5.2 Implement `llm_cli/inputs/text.py`: read text files with extension whitelist, format as `=== <basename> ===\n<content>`; reject non-UTF-8 with clear error
- [x] 5.3 Implement `llm_cli/inputs/image.py`: read image file, detect MIME type, base64-encode into `{type: image_url, image_url: {url: "data:<mime>;base64,..."}}` content entry
- [x] 5.4 Implement `llm_cli/inputs/pdf.py`: use PyMuPDF to either rasterize per-page to PNG bytes (`images` strategy) or extract text per page (`text` strategy); honor `--max-pages` as a hard error
- [x] 5.5 Implement `llm_cli/inputs/strategy.py`: `auto` strategy picks images if model has `"image"` in `input`, else text
- [x] 5.6 Implement capability check: refuse image input or `--pdf-strategy=images` against text-only models with exit 1
- [x] 5.7 Implement `llm_cli/inputs/builder.py`: assemble final user message `content` array preserving input order, prompt last
- [ ] 5.8 Write unit tests with fixture files for text/markdown/png/jpg/pdf inputs

## 6. Schema handling

- [x] 6.1 Implement `llm_cli/schemas/source.py`: resolve schema from `--schema` flag (file load) or `mode.schema`; `--schema` precedence
- [x] 6.2 Implement `llm_cli/schemas/encode.py`: encode schema into request body per `provider_kind` (llama.cpp: `response_format`, vllm: `extra_body.guided_json`, ollama: top-level `format`, openai-generic: `response_format` with stderr warning)
- [x] 6.3 Implement `llm_cli/schemas/validate.py`: parse assistant content as JSON, validate against schema (Draft 2020-12), return validated obj or error with path
- [ ] 6.4 Write unit tests covering all four `provider_kind` encodings and validation success/parse-failure/validation-failure paths

## 7. Transport

- [x] 7.1 Implement `llm_cli/transport/client.py`: `httpx.Client` with connect_timeout=10s, read_timeout=600s (overridable by CLI flags); add `Authorization: Bearer <api_key>` when api_key present
- [x] 7.2 Implement `llm_cli/transport/request.py`: assemble final POST body (model, messages, merged sampling flattened, `extra_body` flattened, `response_format`/`format` from schema encoding, `max_tokens` via `compat.maxTokensField`); ensure `stream=False`
- [x] 7.3 Implement `llm_cli/transport/errors.py`: classify HTTP responses into exit codes per spec (4xx≠401/403→1; 401/403/5xx/timeout/network→3)
- [x] 7.4 Implement `llm_cli/transport/parse.py`: extract `response.choices[0].message.content`; missing → exit 3
- [ ] 7.5 Write transport tests against a local mock httpx server (`pytest-httpx`)

## 8. Logging and diagnostics

- [x] 8.1 Implement `llm_cli/logging/run_log.py`: write JSONL record per spec field list; redact `Authorization` header value to `"Bearer ***"`
- [x] 8.2 Implement `llm_cli/logging/diagnostics.py`: format one-line stderr diagnostic `provider=... model=... mode=... latency=...ms tokens=p/c run=<uuid> log=<path>`; suppress under `--quiet`
- [x] 8.3 Generate one UUIDv4 per `run` invocation; thread it through both stderr line and log record
- [ ] 8.4 Write tests verifying redaction, file mode `0700`, transport-failure logging path

## 9. CLI commands

- [x] 9.1 Wire `llm-cli run` in `__main__.py` with all flags (`--mode` required, `--provider`, `--model`, `--schema`, `--pdf-strategy`, `--max-pages`, `--temperature`, `--top-p`, `--top-k`, `--set` repeating, `--quiet`, `--compact`, `--dry-run`, `--connect-timeout`, `--read-timeout`)
- [x] 9.2 Implement `--dry-run`: build resolved request and print as pretty JSON; no HTTP call
- [x] 9.3 Implement `llm-cli list providers|models|modes` with `--provider` filter
- [x] 9.4 Implement `llm-cli ping [--provider <name>]`: hit `/v1/models` on each provider, report status and latency
- [x] 9.5 Implement `llm-cli show provider|model|mode <name>` printing full resolved JSON
- [x] 9.6 Ensure no-args invocation prints usage to stderr and exits 1
- [x] 9.7 Ensure unknown subcommand exits 1 with usage hint
- [ ] 9.8 End-to-end CLI snapshot tests for each subcommand against a mock provider

## 10. Provider and model selection

- [x] 10.1 Implement `llm_cli/resolve/provider.py`: select provider by `--provider` flag, else `default_provider` field, else hard error listing providers
- [x] 10.2 Implement `llm_cli/resolve/model.py`: select model by `--model` flag (matching `id` or `name`), else `default_model` field scoped to provider, else hard error listing models
- [x] 10.3 Detect ambiguous model `name` across providers when `--provider` omitted; hard error
- [ ] 10.4 Tests for selection: explicit, default, ambiguous, missing

## 11. Output discipline

- [x] 11.1 Implement `llm_cli/output/emit.py`: if schema active → JSON to stdout (pretty by default, compact with `--compact`); else raw text to stdout
- [x] 11.2 Ensure errors only ever go to stderr; stdout is reserved for the result
- [ ] 11.3 Tests: assert stdout is parseable JSON when schema present, plain text otherwise

## 12. Documentation

- [x] 12.1 Write `README.md` covering install (`uv tool install`), example invocations per built-in mode, config file layout, environment paths
- [x] 12.2 Include a `models.json` example mirroring the pi shape (with placeholder URLs) and a `modes.json` example showing one user-defined mode
- [x] 12.3 Document each exit code and the stdout/stderr contract for skill authors

## 13. Manual acceptance

- [ ] 13.1 Run `llm-cli ping` against the user's `nuc` provider and confirm OK
- [ ] 13.2 Run `llm-cli run --mode general --model Qwen3.6-27B-vision "say hi"` and confirm text on stdout, diagnostic on stderr, log entry written
- [ ] 13.3 Run `llm-cli run --mode ocr @<some-image.png>` and confirm validated JSON on stdout
- [ ] 13.4 Run `llm-cli run --mode summarize @<some.pdf>` and confirm text-strategy auto-pick for text-only model OR images-strategy for VLM
- [ ] 13.5 Run `llm-cli run --mode code --schema <some-schema.json> "write a function"` and confirm JSON on stdout, exit 0
- [ ] 13.6 Force a schema mismatch and confirm exit code 2 with raw response on stderr
- [ ] 13.7 Stop the provider and run a request to confirm exit code 3 with clear error
