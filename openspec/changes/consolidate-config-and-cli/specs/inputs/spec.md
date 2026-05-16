## MODIFIED Requirements

### Requirement: Image file handling

Files with extensions in `{.png, .jpg, .jpeg, .webp, .gif, .bmp}` SHALL be attached to the user message as an OpenAI-compatible vision content entry of the form `{"type": "image_url", "image_url": {"url": "<value>"}}`. The `<value>` SHALL be derived from the resolved provider's `file_passing` setting:

- `file_passing = "path"` — the file is referenced as `file:///<absolute-path>` and its bytes are NOT read by the CLI before sending. The provider is expected to resolve the path itself.
- `file_passing = "inline"` — the file is read as binary, base64-encoded, and embedded as a `data:<mime>;base64,<...>` URL.

The system SHALL refuse the input (exit code 1) if the resolved model's `input` array does not include `"image"`.

The system SHALL refuse the input (exit code 1) if the file does not exist, regardless of `file_passing` mode.

#### Scenario: PNG image attached as file:// URL on local provider

- **WHEN** the user passes `@photo.png` against a vision-capable model whose provider has `file_passing = "path"` (the default for `llama.cpp`)
- **THEN** the user message contains an `image_url` entry whose URL is `file:///<absolute-path-to-photo.png>` and the CLI does NOT read the file's bytes

#### Scenario: PNG image attached as data URL on remote provider

- **WHEN** the user passes `@photo.png` against a vision-capable model whose provider has `file_passing = "inline"`
- **THEN** the user message contains an `image_url` entry with a `data:image/png;base64,...` URL

#### Scenario: Image against text-only model rejected

- **WHEN** the user passes `@photo.png` and the resolved model has `input = ["text"]`
- **THEN** the system writes "model <name> does not accept image inputs" to stderr and exits with code 1

#### Scenario: Missing image file rejected before path is sent

- **WHEN** the user passes `@missing.png` against a provider with `file_passing = "path"`
- **THEN** the system writes "input not found: missing.png" to stderr and exits with code 1 (the path is not sent to the provider)

### Requirement: PDF strategies

The system SHALL accept `--pdf-strategy {auto|images|text}` (default `auto`) for handling `.pdf` inputs:
- `auto` — if the resolved model's `input` includes `"image"`, behave as `images`; otherwise behave as `text`.
- `images` — rasterize each page to a PNG via PyMuPDF. Under `file_passing = "path"`, write each rasterized page to a per-run temp directory and attach each as a `file://` image_url. Under `file_passing = "inline"`, base64-inline each page as a `data:image/png;base64,...` URL. Temp files SHALL be cleaned up at process exit.
- `text` — extract the text layer of each page via PyMuPDF and inline it as text, prefixed per page with `=== <basename> page <N> ===`. This strategy is unaffected by `file_passing`.

#### Scenario: Auto chooses images for vision model

- **WHEN** the resolved model has `input = ["text", "image"]` and the user passes `@doc.pdf` without specifying `--pdf-strategy`
- **THEN** the system rasterizes each PDF page and attaches them as image entries (using the provider's `file_passing` mode)

#### Scenario: Auto chooses text for text-only model

- **WHEN** the resolved model has `input = ["text"]` and the user passes `@doc.pdf` without specifying `--pdf-strategy`
- **THEN** the system extracts each page's text layer and inlines it

#### Scenario: Explicit images on text-only model rejected

- **WHEN** the user passes `--pdf-strategy=images` against a model with `input = ["text"]`
- **THEN** the system writes an error explaining the incompatibility and exits with code 1

#### Scenario: Rasterized pages written to temp under path mode

- **WHEN** the user runs `--pdf-strategy=images` against a provider with `file_passing = "path"` on a 3-page PDF
- **THEN** the system writes 3 PNG files to a per-run temp directory, the outgoing message has 3 `image_url` entries with `file://` URLs pointing into that directory, and the temp directory is removed at process exit

### Requirement: Input ordering preserved

The system SHALL preserve the order of file inputs as given on the command line when constructing the user message. The literal prompt string (if any) SHALL appear after all file inputs. Any number of file inputs SHALL be accepted.

#### Scenario: Order preserved in message

- **WHEN** the user runs `llm-cli --mode general @a.md @b.md "now answer"`
- **THEN** the user message content list contains a's text first, then b's text, then "now answer", in that order

#### Scenario: Many heterogeneous inputs preserve order

- **WHEN** the user runs `llm-cli --mode image @screen1.png @notes.md @screen2.png "compare the two screenshots using the notes"`
- **THEN** the user message content list contains screen1's image entry, then notes.md's text block, then screen2's image entry, then the literal prompt, in that order

## ADDED Requirements

### Requirement: `max_context_tokens` enforced before request build

When the resolved configuration (after merging provider/model/mode/CLI layers) declares a `max_context_tokens` value, the system SHALL estimate the input token count for the assembled `messages` array and refuse the request if the estimate exceeds `max_context_tokens`. The estimate SHALL be a deterministic heuristic visible in `--dry-run` output. Refusal SHALL exit with code 1 and an error message naming the budget and the estimate.

For v0.2, the estimate SHALL be:
- Each text content entry: `ceil(len(text) / 4)` tokens.
- Each `image_url` content entry: `1024` tokens (fixed allowance).
- Each system message: counted with the same rule as user-message text.

When no `max_context_tokens` is resolved, no check is performed.

#### Scenario: Within budget passes

- **WHEN** the resolved `max_context_tokens` is `8000` and the estimated input is `4500`
- **THEN** the system sends the request normally

#### Scenario: Over budget refused before sending

- **WHEN** the resolved `max_context_tokens` is `2000` and the estimated input is `5400`
- **THEN** the system writes "input estimated at 5400 tokens exceeds max_context_tokens=2000" to stderr, makes no HTTP call, and exits with code 1

#### Scenario: Estimate visible in dry-run

- **WHEN** the user runs `--dry-run` with a resolved `max_context_tokens`
- **THEN** the resolved-request JSON includes a top-level diagnostic field `_estimated_input_tokens` alongside the request body
