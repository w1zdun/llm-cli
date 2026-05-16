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
llm-cli run --mode general --provider nuc --model Qwen3.6-27B-vision "What is 2+2?"

# Code generation
llm-cli run --mode code --model Qwen3.6-27B-vision "Write a Python quicksort"

# OCR (structured output)
llm-cli run --mode ocr --model Qwen3.6-27B-vision @scan.png

# Summarize a PDF
llm-cli run --mode summarize --model Qwen3.6-27B-vision @report.pdf

# Dry run (inspect resolved request)
llm-cli run --mode code --dry-run "write hello world"
```

## Config

Two JSONC files in `~/.config/llm-cli/`:

### `models.json` — Providers and Models

Mirrors the shape of `~/.pi/agent/models.json`:

```jsonc
{
  "default_provider": "nuc",
  "providers": {
    "nuc": {
      "baseUrl": "http://localhost:8080/v1",
      "providerKind": "llama.cpp",
      "models": [
        {
          "id": "./Qwen3.6-27B-vision",
          "name": "Qwen3.6-27B-vision",
          "input": ["text", "image"],
          "contextWindow": 32768,
          "reasoning": true,
          "thinkingFormat": "qwen-chat-template",
          "thinkingLevelMap": {
            "off": "false",
            "low": "1024",
            "medium": "2048",
            "high": "4096",
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

### `modes.json` — User-Defined Modes

```jsonc
{
  "research": {
    "sampling": {
      "temperature": 0.7,
      "top_p": 0.95,
    },
    "system_prompt": "You are a research assistant. Cite sources when possible.",
    "requires_input": "text",
  },
}
```

User modes completely replace built-in modes of the same name.

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

- **`@path`** — File input (text inlined, images base64'd, PDFs handled per strategy)
- **`\@`** — Escaped at-sign (literal prompt starting with `@`)
- **`--pdf-strategy`** — `auto` (default), `images`, or `text`
- **`--max-pages`** — Hard cap on PDF pages (default: 25)

## Subcommands

```
llm-cli run       Run a single LLM request
llm-cli list      List providers, models, or modes
llm-cli ping      Ping one or all providers
llm-cli show      Show full definition of a provider, model, or mode
```

### `run` Flags

| Flag                | Description                              |
| ------------------- | ---------------------------------------- |
| `--mode` (required) | Mode name                                |
| `--provider`        | Provider name (falls back to default)    |
| `--model`           | Model id or name (falls back to default) |
| `--schema`          | Path to JSON Schema file                 |
| `--pdf-strategy`    | `auto`, `images`, or `text`              |
| `--max-pages`       | Max PDF pages (default: 25)              |
| `--temperature`     | Override temperature                     |
| `--top-p`           | Override top_p                           |
| `--top-k`           | Override top_k                           |
| `--set key=value`   | Arbitrary override (repeatable)          |
| `--quiet`           | Suppress diagnostic stderr               |
| `--compact`         | Compact JSON output                      |
| `--dry-run`         | Print resolved request, no HTTP call     |
| `--connect-timeout` | Connect timeout in seconds (default: 10) |
| `--read-timeout`    | Read timeout in seconds (default: 600)   |

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

Every `run` appends a JSONL record to `~/.local/share/llm-cli/runs.jsonl`:

```jsonl
{"ts": "2025-01-15T10:30:00.123Z", "run_id": "abc-123", "provider": "nuc", "model": "./Qwen...", "mode": "general", "resolved_request": {...}, "resolved_headers": {"Authorization": "Bearer ***"}, "response_status": 200, "response": {...}, "latency_ms": 1234, "exit_code": 0}
```

`Authorization` header values are always redacted.

## Environment

| Variable          | Default          | Description             |
| ----------------- | ---------------- | ----------------------- |
| `XDG_CONFIG_HOME` | `~/.config`      | Config directory parent |
| `XDG_DATA_HOME`   | `~/.local/share` | Data directory parent   |

Config files: `${XDG_CONFIG_HOME}/llm-cli/models.json` and `modes.json`
Run log: `${XDG_DATA_HOME}/llm-cli/runs.jsonl`
