"""Parse positional args into file-input list and literal prompt."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ParsedInputs:
    """Result of parsing positional arguments."""

    file_paths: list[str] = field(default_factory=list)
    prompt: str | None = None


TEXT_EXTENSIONS = {
    ".txt",
    ".md",
    ".json",
    ".yaml",
    ".yml",
    ".py",
    ".js",
    ".ts",
    ".go",
    ".rs",
    ".java",
    ".c",
    ".cpp",
    ".h",
    ".sh",
    ".toml",
    ".ini",
    ".csv",
    ".tsv",
    ".xml",
    ".html",
    ".css",
    ".sql",
}

IMAGE_EXTENSIONS = {
    ".png",
    ".jpg",
    ".jpeg",
    ".webp",
    ".gif",
    ".bmp",
}

PDF_EXTENSIONS = {".pdf"}


def parse_inputs(args: list[str]) -> ParsedInputs:
    """Parse positional arguments into file inputs and prompt.

    Args starting with @ are file paths (unless escaped as \@).
    The last non-@ arg is the prompt.

    Args:
        args: Positional arguments from the CLI.

    Returns:
        ParsedInputs with file_paths and prompt.
    """
    result = ParsedInputs()
    prompt_parts: list[str] = []

    for arg in args:
        if arg.startswith("\\@"):
            # Escaped @ — treat as literal prompt
            prompt_parts.append(arg[1:])  # remove backslash
        elif arg.startswith("@"):
            # File input
            result.file_paths.append(arg[1:])  # remove @
        else:
            prompt_parts.append(arg)

    if prompt_parts:
        result.prompt = " ".join(prompt_parts)

    return result


def classify_file(path: str) -> str:
    """Classify a file by extension.

    Returns:
        'text', 'image', 'pdf', or 'unknown'.
    """
    from pathlib import Path

    ext = Path(path).suffix.lower()
    if ext in TEXT_EXTENSIONS:
        return "text"
    if ext in IMAGE_EXTENSIONS:
        return "image"
    if ext in PDF_EXTENSIONS:
        return "pdf"
    return "unknown"
