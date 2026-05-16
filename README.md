# llm-cli

Single-shot LLM worker CLI for local OpenAI-compatible servers. Install via `uv tool`, invoke from scripts or agent skills. One request, one response.

## Install

```bash
# From GitHub
uv tool install git+https://github.com/w1zdun/llm-cli.git

# From local path
uv tool install /path/to/llm-cli

# From local git clone
uv tool install git+file:///path/to/llm-cli
```

## Quick Start

```bash
# General chat
llm-cli --mode general --provider nuc --model Qwen3.6-27B-vision "What is 2+2?"

# Code generation
llm-cli --mode code --model Qwen3.6-27B-vision "Write a Python quicksort"

# OCR (structured output)
llm-cli --mode ocr --model Qwen3.6-27B-vision @scan.png

# Summarize a PDF
llm-cli --mode summarize --model Qwen3.6-27B-vision @report.pdf

# With sampling template
llm-cli --mode code --sampling-template qwen3.6-thinking-code "Write a quicksort"

# Enable thinking mode
llm-cli --mode general --enable-thinking "Think step by step about..."

# Dry run (inspect resolved request)
llm-cli --mode code --dry-run "write hello world"
```

## Config

Single JSONC file: `~/.config/llm-cli/models.json`

### `models.json` — Providers, Models, Modes, Templates

```jsonc
{
  "default_provider": "nuc",

  // Named sampling parameter bundles (reusable across modes/models)
  "samplingTemplates": {
    "my-custom": {
      "temperature": 0.5,
      "top_p": 0.95,
    },
  },

  // Global modes (apply to all providers/models)
  "modes": {
    "research": {
      "sampling": {
        "temperature": 0.7,
        "top_p": 0.95,
      },
      "system_prompt": "You are a research assistant. Cite sources.",
      "max_context_tokens": 32000,
    },
  },

  "providers": {
    "nuc": {
      "baseUrl": "http://localhost:8080/v1",
      "providerKind": "llama.cpp",
      "filePassing": "path", // file:// URLs (default for llama.cpp)
      "maxContextTokens": 32768,
      "maxOutputTokens": 8192,

      // Provider-level modes (inherit from global, override keys)
      "modes": {
        "code": {
          "sampling": {
            "temperature": 0.1,
          },
        },
      },

      "models": [
        {
          "id": "./Qwen3.6-27B-vision",
          "name": "Qwen3.6-27B-vision",
          "input": ["text", "image"],
          "contextWindow": 32768,
          "reasoning": true,
          "thinkingFormat": "qwen-chat-template",
          "supportsDeveloperRole": true,
          "maxContextTokens": 32768,
          "maxOutputTokens": 8192,

          // Model-level modes (most specific layer)
          "modes": {
            "code": {
              "maxOutputTokens": 4096,
            },
          },

          "sampling": {
            "temperature": 0.6,
          },
        },
      ],
    },
    "vllm-mlx": {
      "base_url": "http://localhost:8000/v1",
      "provider_kind": "vllm",
      "models": [
        {
          "id": "./Qwen3.6-35B-A3B-MLX-8bit",
          "name": "Qwen3.6-35B-A3B-MLX-8bit",
          "input": ["text"],
          "context_window": 16384,
        },
      ],
    },
  },
}
```

### Mode Resolution (four layers)

Modes merge across four layers (later wins per key):

1. **Built-in** — shipped with the CLI (`code`, `general`, `design`, `ocr`, …)
2. **Global** — top-level `modes` in `models.json`
3. **Provider** — `providers.<name>.modes`
4. **Model** — `providers.<name>.models[].modes`

Example: if global defines `code.system_prompt` and provider defines `code.sampling.temperature`, the resolved mode has both.

### Sampling Templates

Built-in templates (from [Unsloth Qwen3.6 docs](https://github.com/unslothai/unsloth)):

| Template                     | Temp | top_p | top_k | min_p | presence_penalty |
| ---------------------------- | ---- | ----- | ----- | ----- | ---------------- |
| `qwen3.6-thinking-general`   | 1.0  | 0.95  | 20    | 0.0   | 1.5              |
| `qwen3.6-thinking-code`      | 0.6  | 0.95  | 20    | 0.0   | 0.0              |
| `qwen3.6-instruct-general`   | 0.7  | 0.8   | 20    | 0.0   | 1.5              |
| `qwen3.6-instruct-reasoning` | 1.0  | 0.95  | 20    | 0.0   | 1.5              |

Reference from any layer: `{"sampling_template": "qwen3.6-thinking-code"}`.
List with: `llm-cli list templates`.

### Thinking Control

For models with `thinkingFormat: "qwen-chat-template"`, use plain sampling keys:

- `enable_thinking: true/false` — enable/disable reasoning traces
- `preserve_thinking: true/false` — keep prior traces in history

These are automatically routed to `extra_body.chat_template_kwargs.*` at request time.

### File Passing

- `"path"` — sends `file:///abs/path` URLs (default for `llama.cpp`, `vllm`, `ollama`)
- `"inline"` — sends base64 data URLs (default for `openai-generic`)

### Token Budgets

- `max_context_tokens` — client-side input budget (never sent to provider). Exceeded = exit 1.
- `max_output_tokens` — written to request under the provider-mapped field name (e.g., `max_tokens` for llama.cpp, `num_predict` for ollama).

## Built-in Modes

| Mode        | Temp | Description                                 |
| ----------- | ---- | ------------------------------------------- |
| `code`      | 0.2  | Precise code generation                     |
| `general`   | 0.6  | General-purpose chat                        |
| `design`    | 0.9  | Creative exploration, multiple alternatives |
| `image`     | 0.3  | Image description (requires vision model)   |
| `ocr`       | 0.0  | Text extraction from images (JSON output)   |
| `summarize` | 0.3  | Concise summaries                           |
| `classify`  | 0.1  | Categorization and labeling                 |
| `extract`   | 0.1  | Structured information extraction           |

## Input Handling

- **`@path`** — File input (text inlined, images by path or base64 per provider, PDFs per strategy)
- **`\@`** — Escaped at-sign (literal prompt starting with `@`)
- **`--pdf-strategy`** — `auto` (default), `images`, or `text`
- **`--max-pages`** — Hard cap on PDF pages (default: 25)

## CLI

```
llm-cli [flags] [args]     Run a request (default action)
llm-cli list <what>        List providers, models, modes, or templates
llm-cli ping               Ping one or all providers
llm-cli show <what> <name> Show full definition
```

### Flags

| Flag                                           | Description                                  |
| ---------------------------------------------- | -------------------------------------------- |
| `--mode` (required)                            | Mode name                                    |
| `--provider`                                   | Provider name (falls back to default)        |
| `--model`                                      | Model id or name (falls back to default)     |
| `--schema`                                     | Path to JSON Schema file                     |
| `--pdf-strategy`                               | `auto`, `images`, or `text`                  |
| `--max-pages`                                  | Max PDF pages (default: 25)                  |
| `--temperature`                                | Override temperature                         |
| `--top-p`                                      | Override top_p                               |
| `--top-k`                                      | Override top_k                               |
| `--enable-thinking`/`--no-enable-thinking`     | Enable/disable thinking                      |
| `--preserve-thinking`/`--no-preserve-thinking` | Preserve thinking traces                     |
| `--sampling-template`                          | Named sampling template                      |
| `--max-context-tokens`                         | Client-side input token budget               |
| `--max-output-tokens`                          | Output token budget                          |
| `--set key=value`                              | Arbitrary override (repeatable, dotted keys) |
| `--quiet`                                      | Suppress diagnostic stderr                   |
| `--compact`                                    | Compact JSON output                          |
| `--dry-run`                                    | Print resolved request, no HTTP call         |
| `--connect-timeout`                            | Connect timeout in seconds (default: 10)     |
| `--read-timeout`                               | Read timeout in seconds (default: 600)       |

## Output Contract

**stdout** — Result only (raw text or JSON). Never errors or diagnostics.

**stderr** — Diagnostics (one line on success), error messages.

```
provider=nuc model=./Qwen3.6-27B-vision mode=general latency=1234ms tokens=12/45 run=abc-123 log=~/.local/share/llm-cli/runs.jsonl
```

## Exit Codes

| Code | Meaning                                          |
| ---- | ------------------------------------------------ |
| `0`  | Success                                          |
| `1`  | User error (bad args, missing config, etc.)      |
| `2`  | Schema validation failed (response didn't match) |
| `3`  | Provider/transport error (HTTP, network, auth)   |

## Run Log

Every request appends a JSONL record to `~/.local/share/llm-cli/runs.jsonl`:

```jsonl
{"ts": "2025-01-15T10:30:00.123Z", "run_id": "abc-123", "provider": "nuc", "model": "./Qwen...", "mode": "general", "resolved_request": {...}, "resolved_headers": {"Authorization": "Bearer ***"}, "response_status": 200, "response": {...}, "latency_ms": 1234, "exit_code": 0}
```

`Authorization` header values are always redacted.

## Environment

| Variable          | Default          | Description             |
| ----------------- | ---------------- | ----------------------- |
| `XDG_CONFIG_HOME` | `~/.config`      | Config directory parent |
| `XDG_DATA_HOME`   | `~/.local/share` | Data directory parent   |

Config file: `${XDG_CONFIG_HOME}/llm-cli/models.json`
Run log: `${XDG_DATA_HOME}/llm-cli/runs.jsonl`

## Migration from v0.1

### Config file split removed

v0.1 used two files: `models.json` + `modes.json`. v0.2 uses only `models.json` with modes nested at global, provider, and model levels. Move your `modes.json` entries into `models.json` at the appropriate scope.

### `thinkingLevelMap` removed

The `reasoning: off/low/medium/high/xhigh` abstraction and `thinkingLevelMap` are gone. Use:

- `enable_thinking: true/false` — plain boolean sampling key
- `preserve_thinking: true/false` — keep traces across turns

For models with `thinkingFormat: "qwen-chat-template"`, these keys are automatically routed to `chat_template_kwargs`.

### `run` subcommand removed

`llm-cli run --mode code "…"` becomes `llm-cli --mode code "…"`. The `run` verb is no longer needed — the default action is to run a request. `list`, `ping`, `show` remain as explicit subcommands.

### `compat.maxTokensField` replaced

Replaced with `compat.param_mapping: dict[str, str]` for generic field name mapping. Per-kind defaults cover `max_output_tokens` for all supported provider kinds.
