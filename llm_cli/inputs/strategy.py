"""PDF strategy resolution and capability checks."""

from __future__ import annotations

import typer

from llm_cli.config.models_schema import Model

_PDF_STRATEGIES = {"auto", "images", "text"}


def resolve_pdf_strategy(
    strategy: str,
    model: Model,
) -> str:
    """Resolve the effective PDF strategy.

    Args:
        strategy: Strategy from CLI (auto/images/text).
        model: Resolved model.

    Returns:
        Effective strategy ('images' or 'text').

    Raises:
        SystemExit: On invalid strategy or capability mismatch (exit code 1).
    """
    if strategy not in _PDF_STRATEGIES:
        typer.echo(
            f"error: invalid --pdf-strategy '{strategy}'; "
            f"valid: {', '.join(sorted(_PDF_STRATEGIES))}",
            err=True,
        )
        raise typer.Exit(1)

    if strategy == "auto":
        return "images" if "image" in model.input else "text"

    # Check capability for explicit strategies
    if strategy == "images" and "image" not in model.input:
        typer.echo(
            f"error: model '{model.id}' does not accept image inputs, "
            f"cannot use --pdf-strategy=images",
            err=True,
        )
        raise typer.Exit(1)

    return strategy


def check_image_capability(model: Model) -> None:
    """Check if the model supports image inputs.

    Args:
        model: Resolved model.

    Raises:
        SystemExit: If model doesn't support images (exit code 1).
    """
    if "image" not in model.input:
        typer.echo(
            f"error: model '{model.id}' does not accept image inputs",
            err=True,
        )
        raise typer.Exit(1)
