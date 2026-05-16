## Context

`llm-cli` is a fresh greenfield project. The primary consumer is *other LLM agents* — Claude Code skills, Codex skills, and similar — that need to delegate bounded tasks (describe-image, ocr, summarize, write-code, extract-structured) to **local** OpenAI-compatible LLM servers. The reference setup is the user's pi-agent configuration at `~/.pi/agent/models.json`, which already enumerates providers like `vllm-mlx`, `nuc`, models like `Qwen3.6-27B-vision`, default sampling, vision capability flags, and a reasoning-level encoding (`thinkingFormat` + `thinkingLevelMap`).

Constraints:
- Tool is invoked from a subprocess by a skill — stdout must be parseable; stderr must not leak into result; exit codes must distinguish failure modes.
- "Local" means the LLM endpoint is user-controlled (LAN or localhost). The CLI itself runs on the user's machine and reads local files (`@path` args).
- All providers in scope (llama.cpp `/v1`, vLLM `/v1`, Ollama `/v1`, LM Studio `/v1`) expose an OpenAI-compatible Chat Completions API. The CLI does not need a per-provider HTTP layer.
- The user is the sole operator and skill-author at v1; no multi-tenancy, no auth on the CLI itself (provider keys are per-provider in `models.json`).

## Goals / Non-Goals

**Goals:**

- One uniform CLI surface for many local OAI-compatible providers.
- Expose **advanced sampling** (DRY, XTC, min_p, mirostat, dynatemp, reasoning level, …) without losing them to a lowest-common-denominator schema.
- Make **task = mode** a first-class concept so the same model can be reused for `code`, `general`, `design`, `image`, `ocr`, etc. with task-appropriate sampling.
- Make **structured output** a default-grade feature: pass `--schema` or use a mode with bound schema → validated JSON on stdout.
- Be **skill-friendly**: deterministic stdout/stderr split, meaningful exit codes, full run log to JSONL for debugging.
- Be **predictable**: explicit `--mode` requirement, no implicit defaults, no silent param dropping (validation off, provider is source of truth).
- Install cleanly via `uv tool install` from a local git clone.

**Non-Goals:**

- Chat / conversation history / memory.
- Tool calling / function calling / agentic loops invoked *by* this CLI.
- Streaming UX (token-by-token stdout flushing). Single-shot only.
- Audio / speech-to-text / TTS.
- Cloud provider integrations beyond the generic OpenAI-compatible surface (no Anthropic, Google, Bedrock adapters).
- Auto-importing `~/.pi/agent/models.json` at runtime. The shape is mirrored but the file is independent.
- Schema generation / inference — schemas are user-supplied.
- Per-project config layering (`./llm-cli.json`). Deferred past v1.
- A library API for embedding in Python. CLI-only at v1; nothing prevents future library exposure.

## Decisions

### D1. OpenAI-compatible HTTP only (no per-provider adapters)

**Decision:** A single HTTP client (`httpx`) speaks OpenAI Chat Completions to every provider. Provider quirks ride along in `extra_body`.

**Why:** All four primary targets (llama.cpp, vLLM, Ollama, LM Studio) expose `/v1/chat/completions`. Eliminating per-provider client code removes a large class of duplication and reduces maintenance to a single request-builder + a single response-parser.

**Alternatives considered:**
- *Per-provider HTTP clients with provider-native param vocabularies* — rejected: more code, more drift, no real upside since OAI-compat is universal.
- *Use `openai-python` SDK* — rejected for v1: extra dependency, opinionated about response shapes, harder to control `extra_body` and timeouts cleanly. `httpx` is simpler.

### D2. Sampling validation **off** at the client

**Decision:** Whatever sampling keys appear in `provider.sampling`, `model.sampling`, `mode.sampling`, or CLI flags are passed through to the provider. Unknown/unsupported params yield a provider-side error that surfaces on stderr.

**Why:** Sampling vocabularies evolve quickly (llama.cpp added XTC, DRY, dynatemp within recent months). A client-side schema would be stale within weeks. The provider is the ground truth and its error message is authoritative.

**Alternatives considered:**
- *Full per-`provider_kind` sampling schemas* — rejected: high maintenance burden, blocks legitimate new params until the schema is updated.
- *Common-subset validation with warnings* — rejected: middle-ground that still adds maintenance and confuses users when warnings appear for valid params.

**Trade-off:** Typos like `temperture` reach the provider and produce HTTP errors instead of friendly client-side messages. Mitigated by the `--dry-run` flag printing the fully resolved request.

### D3. Two-file config, JSONC, pi-shaped

**Decision:**
- `~/.config/llm-cli/models.json` — providers + models, **mirrors `~/.pi/agent/models.json`'s shape verbatim** (separate file, not imported at runtime).
- `~/.config/llm-cli/modes.json` — modes (sampling + system_prompt + optional schema + optional `requires_input`).
- Both parsed as JSONC (comments tolerated). Built-in modes shipped inside the package can be overridden by user-provided modes of the same name.

**Why:** The user already has a working mental model from pi-agent. Reusing the exact shape eliminates a translation step. Splitting providers from modes mirrors the conceptual split between *where to talk* and *what task to do* — each varies independently and changes at a different cadence (providers rarely; modes often).

**Alternatives considered:**
- *Single combined `config.json`* — rejected: providers and modes have very different lifecycles; merging them couples reviews and edits.
- *TOML* — rejected for v1 because it diverges from the pi convention the user explicitly cited.
- *Auto-read `~/.pi/agent/models.json`* — rejected this round per user preference (option `a`: mirror, don't import).

### D4. `--mode` is required; no env var fallback

**Decision:** `llm-cli run` errors out with exit code `1` if `--mode` is not passed. There is no `LLM_CLI_MODE` env var and no implicit `default` mode.

**Why:** This CLI is a worker invoked by other agents. Implicit defaults are a debugging nightmare across skill boundaries — a change to a default in this tool's config would silently change behavior of every skill that omits `--mode`. Forcing explicitness pushes the choice to the skill author, who can pass `--mode general` if they truly mean it.

**Alternatives considered:**
- *Default to `general`* — rejected: silently hides "I forgot to think about which mode" bugs.
- *`LLM_CLI_MODE` env var* — rejected: env-var-as-default has the same hidden-behavior problem at one layer of indirection.

### D5. Reasoning lives inside sampling, encoded per model

**Decision:** A mode's `sampling.reasoning` is one of `off|minimal|low|medium|high|xhigh` (matching pi's vocabulary). Each model in `models.json` declares `thinkingFormat` (one of `qwen-chat-template`, `openai-reasoning-effort`, `none`, etc.) and `thinkingLevelMap` mapping each abstract level to the model-specific encoding value (or `null` for "unsupported").

At resolve time: if `thinkingLevelMap[level]` is `null` or missing, error out with a clear message listing supported levels.

**Why:** Reasoning is conceptually another sampling knob (it shapes generation behavior), so it deserves the same resolution stack as `temperature`. But its on-the-wire encoding varies wildly across models. Abstracting the level and pushing encoding to the model entry keeps modes portable across models.

**Alternatives considered:**
- *Per-model boolean reasoning* — rejected: loses gradations.
- *Mode emits raw provider-specific keys* — rejected: makes modes non-portable across models.

### D6. Inputs as `@path` positional args; normalization driven by model capability

**Decision:**
- Args starting with `@` are file inputs; everything else is the literal prompt string.
- Text files → inlined into the user message.
- Images → base64 data URLs in OpenAI-compatible vision `content` entries. Refused if the chosen model's `input` array does not include `"image"` (hard error, exit `1`).
- PDFs → `--pdf-strategy=auto|images|text`:
  - `auto` (default): if model supports images, rasterize per page (via PyMuPDF) and attach as multiple image_url entries; else extract text.
  - `images`: always rasterize.
  - `text`: always extract text (via PyMuPDF text layer).
- `--max-pages=N` caps PDF size; exceeding it is a hard error (exit `1`) — never silently truncate.

**Why:** `@path` is a familiar convention (used by `simonw/llm`, `curl @file`, others). Routing image handling through `model.input` capabilities lets the CLI refuse impossible combinations early instead of producing a confusing provider error. PyMuPDF is the most robust open PDF library on macOS and handles both rasterization and text extraction.

**Alternatives considered:**
- *Auto-detect file type from content rather than extension* — deferred; extension-based detection is simpler and sufficient for v1.
- *OCR text-only PDFs through an OCR engine like tesseract* — rejected for v1: adds a heavy native dep. If the user's PDF lacks a text layer, they can pick `--pdf-strategy=images` and use a VLM to OCR.

### D7. Schema source = `--schema` OR mode-bound; encoding per `provider_kind`

**Decision:**
- Schema accepted from `--schema <file>` (JSON Schema file) or from `mode.schema`. `--schema` takes precedence.
- On the wire, schema is encoded per `provider_kind`:
  - `llama.cpp` → `response_format = {type: "json_schema", json_schema: {schema: ...}}`.
  - `vllm` → `extra_body = {guided_json: <schema>}`.
  - `ollama` → `format = <schema>`.
  - `openai-generic` / unknown → `response_format = {type: "json_schema", ...}` with stderr warning that fallback was used.
- Output validated against the schema (using `jsonschema`); validation failure → exit `2`, raw response on stderr for debugging.

**Why:** Each provider exposes structured output differently but the user-facing surface should be uniform. Picking the right wire encoding from `provider_kind` keeps the CLI authoritative and prevents the skill author from needing provider-specific knowledge.

**Alternatives considered:**
- *Pydantic models as schema source* — deferred; JSON Schema is the lowest-common-denominator and easy to author by hand or generate.
- *Lenient JSON parsing of partial responses* — rejected: explicit failure is better than smudging over malformed structured output, and the run log preserves the raw response.

### D8. Output discipline: stdout = result only; stderr = diagnostics; exit codes by category

**Decision:**

```
stdout:
  no schema       → raw text (the assistant's content)
  schema present  → JSON (validated, pretty-printed unless --compact)

stderr:
  always          → one line of diagnostics (model, latency, tokens, run-id, log path)
  --quiet         → silence diagnostics; errors still printed

exit:
  0  success
  1  user error (bad args, missing config, unsupported input, max-pages exceeded)
  2  schema validation failed (response was returned but didn't match schema)
  3  provider/transport error (HTTP non-2xx, network failure, auth)
```

**Why:** A subprocess-invoking skill needs to (a) read stdout and parse it, (b) read exit code to classify failures, (c) optionally show stderr to the user for debugging. Splitting categories of error into distinct exit codes lets the skill react differently to "I gave bad input" vs "the model couldn't produce valid JSON" vs "the server is down".

### D9. Run log = JSONL at XDG path

**Decision:** Every `run` invocation appends a single JSON object to `~/.local/share/llm-cli/runs.jsonl`. Fields: `ts` (ISO 8601, UTC), `run_id` (uuid4), `provider`, `model`, `mode`, `resolved_request` (the full POST body), `resolved_headers` (without auth secrets), `response_status`, `response` (full JSON from provider), `latency_ms`, `exit_code`, `error?`. No size limit at v1; the user owns rotation.

**Why:** Skill-invoked subprocesses are notoriously hard to debug because the orchestrator's logs only see stdout/stderr/exit. Having a complete record per call — *especially the resolved request* — lets the user reconstruct what the skill actually asked for and replay it. JSONL is grep-able and `jq`-able.

**Alternatives considered:**
- *SQLite* — rejected for v1: JSONL is enough, simpler to inspect, no migrations.
- *Opt-in logging* — rejected: skill debugging is the primary use case; logs must be on by default. Add `--no-log` later if anyone hits a privacy concern.

### D10. Distribution via `uv tool install` from local git

**Decision:** Single wheel, all dependencies pinned in `pyproject.toml`, no extras at v1 (PDF and image deps included by default). Install command:

```bash
uv tool install ~/gity/llm-cli
# or
uv tool install git+file://~/gity/llm-cli
```

`[project.scripts]` exposes `llm-cli = "llm_cli.__main__:app"`.

**Why:** The user explicitly chose "all functionalities" — no lean variant — and "install from local git". Keeping it a single wheel removes the complexity of optional dependency groups and makes the install one command. PyPI publication is a future decision.

## Risks / Trade-offs

- **[R1] Validation-off lets typos through silently.** A misspelled sampling key reaches the provider and produces an HTTP 400 with an opaque message. → **Mitigation:** `--dry-run` prints the resolved request before sending; the run log captures every request and response. Worst-case impact is one wasted call.
- **[R2] `--mode` required friction.** Every skill invocation must pass `--mode`, including trivial ones. → **Mitigation:** the `general` mode is the explicit no-opinion choice; skills document their chosen mode in their prompt.
- **[R3] PyMuPDF native dependency.** PyMuPDF ships its own bindings to MuPDF (C library) and adds ~30 MB to the install. → **Mitigation:** acceptable given "all functionalities" goal; alternative (pypdf + Pillow for rasterization) is markedly worse on PDF fidelity.
- **[R4] `extra_body` deep-merge ambiguity.** Two layers each setting `extra_body.guided_decoding_backend` need a clear winner. → **Mitigation:** deep-merge with last-writer-wins per key (mode beats model beats provider), documented in the `sampling` spec.
- **[R5] Schema validation false negatives.** A provider may return JSON that's *almost* valid (e.g., trailing whitespace, an extra field) and we exit `2`. → **Mitigation:** schema authors can use `additionalProperties: true`; we document the trade-off and keep the raw response in the run log.
- **[R6] Run log grows unbounded.** Daily skill use could accumulate megabytes of JSONL. → **Mitigation:** documented; user can `rotate` / `truncate` / move to gzip manually. Built-in rotation is a future enhancement.
- **[R7] Reasoning encoding drift.** Provider sides change how they accept reasoning effort (e.g., chat-template flag vs top-level field). → **Mitigation:** the `thinkingFormat` field on each model is an explicit knob; users update `models.json` when providers change.
- **[R8] OAI-generic schema fallback may not actually be supported by every server.** Some OAI-compatible servers reject `response_format` outright. → **Mitigation:** stderr warning when fallback is used; provider error surfaces on exit `3`; user can override by setting `provider_kind` explicitly.

## Migration Plan

Not applicable — greenfield project, no existing users or state to migrate.

## Open Questions

- **JSONC parser choice**: `json5` vs `pyjson5` vs hand-rolled comment-stripping pre-pass. Decision deferred to tasks; functionally equivalent.
- **Image format normalization**: do we re-encode all images to PNG before base64-ing them? Some providers reject WebP. Default: pass-through with content-type detection; re-encode only on a known incompatibility list. To be settled during implementation.
- **Mode `requires_input` granularity**: today proposed as `"image"`, `"text"`, or `"pdf"`. Should it support arrays (`["image", "pdf"]`)? Deferred to first user friction.
- **Built-in mode catalog content**: the eight mode names are locked; their exact system prompts and sampling values will be tuned during implementation. Initial values are starting points, not contracts.
