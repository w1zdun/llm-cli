## ADDED Requirements

### Requirement: `@path` argument convention

Positional arguments to `run` that begin with `@` SHALL be interpreted as file paths. The remaining positional argument (if any) SHALL be treated as the literal user prompt string. A user wishing to include a literal `@` at the start of the prompt SHALL escape it as `\@`.

#### Scenario: File input recognized

- **WHEN** the user runs `llm-cli run --mode summarize @notes.md`
- **THEN** the system reads `notes.md` and includes its content in the user message

#### Scenario: Literal at-sign escaped

- **WHEN** the user runs `llm-cli run --mode general "\@example email"`
- **THEN** the system treats the argument as the literal prompt string starting with `@`

#### Scenario: Multiple file inputs accepted

- **WHEN** the user runs `llm-cli run --mode classify @file1.txt @file2.txt "compare these"`
- **THEN** the system includes both files plus the literal prompt in the user message

#### Scenario: Missing file is a hard error

- **WHEN** an `@path` argument points to a file that does not exist
- **THEN** the system writes "input not found: <path>" to stderr and exits with code 1

### Requirement: Text file inlining

Files with text MIME types or extensions in `{.txt, .md, .json, .yaml, .yml, .py, .js, .ts, .go, .rs, .java, .c, .cpp, .h, .sh, .toml, .ini, .csv, .tsv, .xml, .html, .css, .sql}` SHALL be read as UTF-8 and inlined into the user message as text content. The file name SHALL precede the file content in the format:

```
=== <basename> ===
<content>
```

#### Scenario: Markdown file inlined with header

- **WHEN** the user passes `@notes.md` containing `# Hello\nWorld`
- **THEN** the user message includes a text block starting with `=== notes.md ===` followed by the file content

#### Scenario: Non-UTF-8 file produces a clear error

- **WHEN** the user passes a binary file with a text extension and it cannot be decoded as UTF-8
- **THEN** the system writes "could not decode <path> as UTF-8" to stderr and exits with code 1

### Requirement: Image file handling

Files with extensions in `{.png, .jpg, .jpeg, .webp, .gif, .bmp}` SHALL be read as binary, base64-encoded, and attached to the user message as an OpenAI-compatible vision content entry of the form `{"type": "image_url", "image_url": {"url": "data:<mime>;base64,<...>"}}`. The system SHALL refuse the input (exit code 1) if the resolved model's `input` array does not include `"image"`.

#### Scenario: PNG image attached as data URL

- **WHEN** the user runs `llm-cli run --mode image @photo.png` against a vision-capable model
- **THEN** the user message contains an `image_url` entry with a `data:image/png;base64,...` URL

#### Scenario: Image against text-only model rejected

- **WHEN** the user passes `@photo.png` and the resolved model has `input = ["text"]`
- **THEN** the system writes "model <name> does not accept image inputs" to stderr and exits with code 1

### Requirement: PDF strategies

The system SHALL accept `--pdf-strategy {auto|images|text}` (default `auto`) for handling `.pdf` inputs:
- `auto` — if the resolved model's `input` includes `"image"`, behave as `images`; otherwise behave as `text`.
- `images` — rasterize each page to a PNG via PyMuPDF and attach each as a separate `image_url` content entry.
- `text` — extract the text layer of each page via PyMuPDF and inline it as text, prefixed per page with `=== <basename> page <N> ===`.

#### Scenario: Auto chooses images for vision model

- **WHEN** the resolved model has `input = ["text", "image"]` and the user passes `@doc.pdf` without specifying `--pdf-strategy`
- **THEN** the system rasterizes each PDF page and attaches them as image entries

#### Scenario: Auto chooses text for text-only model

- **WHEN** the resolved model has `input = ["text"]` and the user passes `@doc.pdf` without specifying `--pdf-strategy`
- **THEN** the system extracts each page's text layer and inlines it

#### Scenario: Explicit images on text-only model rejected

- **WHEN** the user passes `--pdf-strategy=images` against a model with `input = ["text"]`
- **THEN** the system writes an error explaining the incompatibility and exits with code 1

### Requirement: `--max-pages` cap

The system SHALL accept `--max-pages <N>` (default `25`) limiting the number of PDF pages processed. If a PDF exceeds this limit, the system SHALL exit with code 1 and a message naming the page count and limit. The system SHALL NOT silently truncate.

#### Scenario: Page limit exceeded is a hard error

- **WHEN** the user passes a 50-page PDF with `--max-pages 25`
- **THEN** the system writes "PDF has 50 pages, exceeds --max-pages 25" to stderr and exits with code 1

#### Scenario: Within limit processes all pages

- **WHEN** the user passes a 10-page PDF with `--max-pages 25`
- **THEN** the system processes all 10 pages

### Requirement: Input ordering preserved

The system SHALL preserve the order of file inputs as given on the command line when constructing the user message. The literal prompt string (if any) SHALL appear after all file inputs.

#### Scenario: Order preserved in message

- **WHEN** the user runs `llm-cli run --mode general @a.md @b.md "now answer"`
- **THEN** the user message content list contains a's text first, then b's text, then "now answer", in that order
