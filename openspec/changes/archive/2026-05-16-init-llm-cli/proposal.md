## Why

Other LLM agents (Claude Code skills, Codex, etc.) need a reliable, scriptable way to delegate bounded text/vision tasks to **local** OpenAI-compatible LLM servers (llama.cpp, vLLM, Ollama, LM Studio, …) with the **advanced sampling knobs** these stacks expose and with **reproducible, structured outputs**. Existing CLIs (`simonw/llm`, `ollama run`, `aichat`) either expose only basic sampling, lock you into one provider, or treat structured output as an afterthought. This change introduces `llm-cli`: a single-shot worker CLI, installable via `uv tool`, that other agents can invoke as a skill — they bring the task, the file/image/PDF inputs, and optionally a schema; it returns text or validated JSON on stdout.

## What Changes

- New Python CLI package `llm-cli` (entry point `llm-cli`), installable via `uv tool install` from local git.
- Single primary command `llm-cli run` — one request, one response. Plus introspection commands: `list providers|models|modes`, `ping`, `show`, `--dry-run`.
- **Single transport**: OpenAI-compatible HTTP only. Provider-specific knobs ride along in `extra_body`. Sampling validation **off** at the client (provider is the source of truth — unknown params surface as provider errors).
- **Config in two JSONC files**:
  - `~/.config/llm-cli/models.json` — providers + models registry, **shape mirrored from `~/.pi/agent/models.json`** (separate file, no auto-import).
  - `~/.config/llm-cli/modes.json` — named sampling/prompt/schema presets per task.
- **Modes** — first-class task presets shipped with the package: `code`, `general`, `design`, `image`, `ocr`, `summarize`, `classify`, `extract`. User can override or add. `--mode` is **required** on every `run` (no implicit default, no env var fallback) — skill author either knows the task or passes `general` explicitly.
- **Sampling resolution stack**: `provider.sampling` → `model.sampling` → `mode.sampling` → CLI flag overrides. Deep-merged per key for both `sampling` and `extra_body`.
- **Reasoning lives in sampling**: modes specify abstract level (`off|minimal|low|medium|high|xhigh`); models declare `thinkingFormat` + `thinkingLevelMap` (pi-shaped) to encode the level. Unsupported level → hard error.
- **Inputs as positional `@path` args**: text files inlined; images base64'd into OpenAI-compatible vision content; PDFs handled via `--pdf-strategy=auto|images|text` (auto: VLM → per-page images, else text extraction). `--max-pages` caps PDF size.
- **Structured output**:
  - Schema source = `--schema <file>` flag or mode-bound `schema`.
  - Schema present → **JSON on stdout**, validated; exit `2` on validation failure.
  - No schema → **raw text on stdout**.
- **stdout/stderr discipline**: stdout = result only; stderr = diagnostics (model, latency, tokens, run-id, log path); `--quiet` silences diagnostics. Exit codes: `0` ok, `1` user error, `2` schema validation fail, `3` provider/transport error.
- **Run log**: every call appended to `~/.local/share/llm-cli/runs.jsonl` (XDG-compliant) with timestamp, resolved request, response, latency, exit code — for skill debugging and replay.
- Out of scope (non-goals): chat/history, tool-calling, agentic loops, streaming UX, audio/transcription, cloud provider quirks beyond generic OpenAI-compatible.

## Capabilities

### New Capabilities

- `cli`: Command surface — `run`, `list`, `ping`, `show`, `--dry-run`; argument parsing; stdout/stderr/exit-code contract.
- `config`: Loading and layering of `models.json` + `modes.json` (JSONC), XDG paths, validation, error messages.
- `providers`: Provider/model registry semantics (pi-shaped schema), capability flags (`input`, `reasoning`, `context_window`), `provider_kind` tag.
- `modes`: Mode definition (sampling, system prompt, optional schema, `requires_input`), built-in catalog, user overrides, `--mode` required behavior.
- `sampling`: Resolution stack (provider → model → mode → CLI), deep-merge semantics, reasoning-level mapping via `thinkingLevelMap`, validation-off pass-through.
- `inputs`: `@path` argument parsing, text inlining, image base64 + capability check against `model.input`, PDF strategies (`auto|images|text`), `--max-pages`.
- `schemas`: Schema sources (`--schema` file, mode-bound), encoding per `provider_kind` (response_format vs guided_json vs format), output validation, exit code 2.
- `transport`: OpenAI-compatible HTTP client (httpx), request construction, error classification, timeouts.
- `logging`: Diagnostics-to-stderr formatting, JSONL run log at `~/.local/share/llm-cli/runs.jsonl`, `--quiet` flag.

### Modified Capabilities

None — greenfield project.

## Impact

- **New repository / package**: Python package `llm_cli` under `~/gity/llm-cli`, with `pyproject.toml` exposing `llm-cli` entry point. Distributed via `uv tool install` from local git path (no PyPI publication required for v1).
- **Dependencies** (pinned in `pyproject.toml`):
  - `httpx` (HTTP client),
  - `typer` (CLI framework),
  - `pydantic` (config + schema validation),
  - `jsonschema` (output validation against JSON Schema),
  - `pymupdf` (PDF rasterization and text extraction),
  - `pillow` (image normalization),
  - `json5` or `pyjson5` (JSONC parsing),
  - `jinja2` (prompt templating in modes).
- **External systems consumed**: local HTTP endpoints (llama.cpp `/v1`, vLLM `/v1`, Ollama `/v1`, LM Studio `/v1`, generic OAI-compatible). No outbound calls beyond user-configured endpoints.
- **Filesystem**: reads under `~/.config/llm-cli/`, appends under `~/.local/share/llm-cli/`, reads user-supplied `@path` inputs. No writes to project paths.
- **Other consumers**: skills (in `~/.claude/skills/`, `~/.codex/skills/`, etc.) will be authored separately to invoke this CLI; their design is out of scope for this change.
