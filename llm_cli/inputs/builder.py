"""Assemble final user message content array."""

from __future__ import annotations

from typing import Any

import typer

from llm_cli.config.models_schema import Model, Provider
from llm_cli.inputs.image import read_image_file
from llm_cli.inputs.parser import ParsedInputs, classify_file
from llm_cli.inputs.pdf import read_pdf_images, read_pdf_text
from llm_cli.inputs.strategy import check_image_capability, resolve_pdf_strategy
from llm_cli.inputs.text import read_text_file


def build_user_message(
    parsed: ParsedInputs,
    model: Model,
    provider: Provider,
    pdf_strategy: str = "auto",
    max_pages: int = 25,
) -> list[dict[str, Any]]:
    """Build the user message content array.

    Preserves input order. Prompt appears last.

    Args:
        parsed: Parsed inputs (file paths + prompt).
        model: Resolved model.
        provider: Resolved provider (for file_passing).
        pdf_strategy: PDF handling strategy.
        max_pages: Max PDF pages.

    Returns:
        Content array for the user message.
    """
    content: list[dict[str, Any]] = []
    file_passing = provider.file_passing or "inline"

    for file_path in parsed.file_paths:
        ftype = classify_file(file_path)

        if ftype == "text":
            text = read_text_file(file_path)
            content.append({"type": "text", "text": text})

        elif ftype == "image":
            check_image_capability(model)
            entry = read_image_file(file_path, file_passing=file_passing)
            content.append(entry)

        elif ftype == "pdf":
            effective = resolve_pdf_strategy(pdf_strategy, model)
            if effective == "images":
                check_image_capability(model)
                images = read_pdf_images(
                    file_path, max_pages, file_passing=file_passing
                )
                content.extend(images)
            else:
                text = read_pdf_text(file_path, max_pages)
                content.append({"type": "text", "text": text})

        else:
            typer.echo(
                f"error: cannot process {file_path} (unknown file type)",
                err=True,
            )
            raise typer.Exit(1)

    # Prompt last
    if parsed.prompt:
        content.append({"type": "text", "text": parsed.prompt})

    return content
