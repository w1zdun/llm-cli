"""llm-cli main entry point."""

from __future__ import annotations

import json
import sys
import time
import uuid

import click
import httpx
import typer
from typer.core import TyperGroup

_SUBCOMMANDS = frozenset({"list", "ping", "show"})

# Long options on the root callback that consume the next token as their value.
_LONG_OPTIONS_TAKING_VALUE = frozenset(
    {
        "--mode",
        "--provider",
        "--model",
        "--schema",
        "--pdf-strategy",
        "--max-pages",
        "--temperature",
        "--top-p",
        "--top-k",
        "--max-context-tokens",
        "--max-output-tokens",
        "--sampling-template",
        "--set",
        "--connect-timeout",
        "--read-timeout",
    }
)
# Short options on the root callback that consume the next token as their value.
_SHORT_OPTIONS_TAKING_VALUE = frozenset({"-m", "-p"})


def _last_not_none(values: list) -> object:
    """Return last non-None value from a list (CLI-side precedence)."""
    for val in reversed(values):
        if val is not None:
            return val
    return None


class _DefaultActionGroup(TyperGroup):
    """Group that lets positional args fall through to the default callback.

    Click's default behavior is to treat the first non-option arg as a
    subcommand name and raise UsageError if it doesn't match. We want
    `llm-cli @file "prompt" --mode X` to work, so when no known subcommand
    is present we strip the positional args before subcommand dispatch
    and stash them on the context for the callback to read.
    """

    def parse_args(self, ctx: click.Context, args: list[str]) -> list[str]:
        # Walk args. Skip option-value pairs; at the first non-option, non-
        # subcommand token, treat the rest as positional args for the default
        # action and hand the prefix to click for normal parsing.
        kept: list[str] = []
        positional: list[str] = []
        i = 0
        while i < len(args):
            a = args[i]
            if a.startswith("-"):
                kept.append(a)
                # Long --opt=value: self-contained.
                if "=" in a and a.startswith("--"):
                    i += 1
                    continue
                # -ovalue (short with attached value): self-contained.
                if a.startswith("-") and not a.startswith("--") and len(a) > 2:
                    i += 1
                    continue
                # Bare option that consumes the next token.
                if (
                    a in _LONG_OPTIONS_TAKING_VALUE
                    or a in _SHORT_OPTIONS_TAKING_VALUE
                ):
                    if i + 1 < len(args):
                        kept.append(args[i + 1])
                        i += 2
                        continue
                i += 1
                continue
            if a in _SUBCOMMANDS:
                kept.extend(args[i:])
                break
            positional.extend(args[i:])
            break
        ctx.ensure_object(dict)
        ctx.obj["positional_args"] = positional
        return super().parse_args(ctx, kept)


app = typer.Typer(
    add_completion=False,
    cls=_DefaultActionGroup,
    help="Single-shot LLM worker CLI for local OpenAI-compatible servers.",
)


def _version_callback(value: bool) -> None:
    if value:
        try:
            import importlib.metadata

            version = importlib.metadata.version("llm-cli")
        except importlib.metadata.PackageNotFoundError:
            version = "dev"
        typer.echo(f"llm-cli {version}")
        raise typer.Exit()


# ─── root callback (was `run` command) ─────────────────────────────────


@app.callback(invoke_without_command=True)
def _main(
    mode: str = typer.Option(
        None,
        "--mode",
        "-m",
        help="Mode name (required).",
    ),
    provider: str | None = typer.Option(
        None,
        "--provider",
        "-p",
        help="Provider name.",
    ),
    model: str | None = typer.Option(
        None,
        "--model",
        help="Model id or name.",
    ),
    schema: str | None = typer.Option(
        None,
        "--schema",
        help="Path to JSON Schema file.",
    ),
    pdf_strategy: str = typer.Option(
        "auto",
        "--pdf-strategy",
        help="PDF handling: auto, images, or text.",
    ),
    max_pages: int = typer.Option(
        25,
        "--max-pages",
        help="Max PDF pages (hard error if exceeded).",
    ),
    temperature: float | None = typer.Option(
        None,
        "--temperature",
        help="Override temperature.",
    ),
    top_p: float | None = typer.Option(
        None,
        "--top-p",
        help="Override top_p.",
    ),
    top_k: int | None = typer.Option(
        None,
        "--top-k",
        help="Override top_k.",
    ),
    enable_thinking: bool | None = typer.Option(
        None,
        "--enable-thinking/--no-enable-thinking",
        help="Enable/disable thinking mode.",
    ),
    preserve_thinking: bool | None = typer.Option(
        None,
        "--preserve-thinking/--no-preserve-thinking",
        help="Preserve thinking traces in history.",
    ),
    sampling_template: str | None = typer.Option(
        None,
        "--sampling-template",
        help="Named sampling template to apply.",
    ),
    max_context_tokens: int | None = typer.Option(
        None,
        "--max-context-tokens",
        help="Client-side input token budget.",
    ),
    max_output_tokens: int | None = typer.Option(
        None,
        "--max-output-tokens",
        help="Output token budget.",
    ),
    set_flags: list[str] | None = typer.Option(
        None,
        "--set",
        help="Arbitrary key=value override (repeatable).",
    ),
    quiet: bool = typer.Option(
        False,
        "--quiet",
        "-q",
        help="Suppress diagnostic stderr output.",
    ),
    compact: bool = typer.Option(
        False,
        "--compact",
        help="Compact JSON output (no whitespace).",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Print resolved request as JSON, do not call provider.",
    ),
    connect_timeout: float = typer.Option(
        10.0,
        "--connect-timeout",
        help="Connect timeout in seconds.",
    ),
    read_timeout: float = typer.Option(
        600.0,
        "--read-timeout",
        help="Read timeout in seconds.",
    ),
    version: bool = typer.Option(
        False,
        "--version",
        "-V",
        help="Print version and exit.",
        callback=_version_callback,
        is_eager=True,
    ),
) -> None:
    """Run a single LLM request (default action)."""
    ctx = click.get_current_context(silent=True)
    if ctx is not None and ctx.invoked_subcommand is not None:
        return

    positional_args: list[str] = []
    if ctx is not None and isinstance(ctx.obj, dict):
        positional_args = list(ctx.obj.get("positional_args", []))

    # No args at all → show help (no_args_is_help behavior).
    if mode is None and not positional_args and len(sys.argv) <= 1:
        typer.echo(ctx.get_help() if ctx is not None else "", err=True)
        raise typer.Exit(1)

    from llm_cli.config.loader import load_models
    from llm_cli.inputs.budget import estimate_tokens
    from llm_cli.inputs.builder import build_user_message
    from llm_cli.inputs.parser import parse_inputs
    from llm_cli.logging.diagnostics import format_diagnostics
    from llm_cli.logging.run_log import write_run_log
    from llm_cli.modes.registry import resolve_modes
    from llm_cli.output.emit import emit_result
    from llm_cli.resolve.cli_overrides import parse_set_flags
    from llm_cli.resolve.extra_body import resolve_extra_body
    from llm_cli.resolve.model import select_model
    from llm_cli.resolve.provider import select_provider
    from llm_cli.resolve.sampling import resolve_sampling
    from llm_cli.resolve.thinking import route_thinking
    from llm_cli.schemas.source import resolve_schema
    from llm_cli.schemas.validate import validate_output
    from llm_cli.sampling.templates import resolve_templates
    from llm_cli.transport.client import create_client
    from llm_cli.transport.errors import classify_error
    from llm_cli.transport.parse import parse_response
    from llm_cli.transport.request import build_request

    providers_file = load_models()

    provider_name, prov = select_provider(providers_file, provider)
    selected_model = select_model(providers_file, prov, model)

    # Resolve modes (four-layer merge)
    all_modes = resolve_modes(providers_file, provider_name, selected_model)

    if mode is None or mode not in all_modes:
        available = ", ".join(sorted(all_modes.keys()))
        which = "required" if mode is None else f"unknown mode '{mode}'"
        typer.echo(
            f"error: --mode is {which}\navailable: {available}", err=True
        )
        raise typer.Exit(1)

    mode_obj = all_modes[mode]

    # Resolve sampling templates
    templates_map = resolve_templates(providers_file)

    # Build CLI sampling overrides
    cli_sampling: dict = {}
    if temperature is not None:
        cli_sampling["temperature"] = temperature
    if top_p is not None:
        cli_sampling["top_p"] = top_p
    if top_k is not None:
        cli_sampling["top_k"] = top_k
    if enable_thinking is not None:
        cli_sampling["enable_thinking"] = enable_thinking
    if preserve_thinking is not None:
        cli_sampling["preserve_thinking"] = preserve_thinking
    if sampling_template is not None:
        cli_sampling["sampling_template"] = sampling_template

    set_sampling, set_extra_body = parse_set_flags(set_flags or [])
    cli_sampling.update(set_sampling)

    # Resolve sampling (with template expansion)
    sampling = resolve_sampling(
        prov, selected_model, mode_obj, cli_sampling, templates_map
    )

    # Resolve extra_body
    extra_body = resolve_extra_body(
        prov, selected_model, mode_obj, set_extra_body
    )

    # Route thinking keys
    sampling, extra_body = route_thinking(selected_model, sampling, extra_body)

    # Reasoning capability check
    if (
        "reasoning" in sampling or "reasoning_effort" in sampling
    ) and not selected_model.reasoning:
        typer.echo(
            f"error: model '{selected_model.id}' does not support reasoning "
            f"(model.reasoning=false); remove reasoning/reasoning_effort from "
            f"the sampling layer",
            err=True,
        )
        raise typer.Exit(1)

    # Resolve token budgets (CLI > mode > model > provider, last non-None wins).
    resolved_max_context = _last_not_none(
        [
            prov.max_context_tokens,
            selected_model.max_context_tokens,
            mode_obj.max_context_tokens,
            max_context_tokens,
        ]
    )
    resolved_max_output = _last_not_none(
        [
            prov.max_output_tokens,
            selected_model.max_output_tokens,
            mode_obj.max_output_tokens,
            max_output_tokens,
        ]
    )

    parsed = parse_inputs(positional_args)
    schema_obj = resolve_schema(schema, mode_obj)

    # Check developer role
    effective_role = mode_obj.effective_role
    if (
        effective_role == "developer"
        and not selected_model.supports_developer_role
    ):
        typer.echo(
            f"error: mode '{mode}' uses role='developer' but model "
            f"'{selected_model.id}' does not support the developer role",
            err=True,
        )
        raise typer.Exit(1)

    # Build messages
    messages: list[dict] = []
    if mode_obj.system_prompt:
        messages.append({"role": "system", "content": mode_obj.system_prompt})

    user_content = build_user_message(
        parsed, selected_model, prov, pdf_strategy, max_pages
    )

    # Reject empty content
    if not user_content and not parsed.prompt:
        typer.echo("error: empty content (no files and no prompt)", err=True)
        raise typer.Exit(1)

    messages.append({"role": effective_role, "content": user_content})

    # Token budget check
    if resolved_max_context is not None:
        estimated = estimate_tokens(messages)
        if estimated > resolved_max_context:
            typer.echo(
                f"error: estimated input tokens ({estimated}) exceed "
                f"max_context_tokens ({resolved_max_context})",
                err=True,
            )
            raise typer.Exit(1)

    # Build request
    request_body = build_request(
        prov,
        selected_model,
        messages,
        sampling,
        extra_body,
        schema_obj,
        resolved_max_output,
    )

    # Add estimated tokens to dry-run output
    if dry_run and resolved_max_context is not None:
        request_body["_estimated_input_tokens"] = estimate_tokens(messages)

    if dry_run:
        json.dump(request_body, sys.stdout, indent=2, ensure_ascii=False)
        sys.stdout.write("\n")
        raise typer.Exit(0)

    run_id = str(uuid.uuid4())
    start = time.monotonic()

    client = create_client(
        prov,
        connect_timeout=connect_timeout,
        read_timeout=read_timeout,
    )

    exit_code = 0
    error_msg: str | None = None
    response_status: int | None = None
    response_data = None
    result_content: str | None = None
    usage = None
    try:
        url = prov.base_url.rstrip("/") + "/chat/completions"
        resp = client.post(url, json=request_body)
        response_status = resp.status_code

        if resp.status_code != 200:
            body = resp.text
            typer.echo(
                f"error: HTTP {resp.status_code} from {provider_name}: {body}",
                err=True,
            )
            exit_code = classify_error(
                httpx.HTTPStatusError(
                    f"HTTP {resp.status_code}",
                    request=resp.request,
                    response=resp,
                )
            )
            error_msg = f"HTTP {resp.status_code}: {body}"
            response_data = body
            raise typer.Exit(exit_code)

        response_data = resp.json()
        result_content, usage = parse_response(response_data)

    except typer.Exit:
        raise
    except (
        httpx.TimeoutException,
        httpx.ConnectError,
        httpx.NetworkError,
    ) as exc:
        error_msg = f"network error: {exc}"
        exit_code = 3
        typer.echo(f"error: {error_msg}", err=True)
    except ValueError as exc:
        error_msg = f"response parse error: {exc}"
        exit_code = 3
        typer.echo(f"error: {error_msg}", err=True)

    latency_ms = int((time.monotonic() - start) * 1000)

    headers = dict(client.headers)
    write_run_log(
        run_id=run_id,
        provider_name=provider_name,
        model_id=selected_model.id,
        mode_name=mode,
        resolved_request=request_body,
        resolved_headers=headers,
        response_status=response_status,
        response=response_data,
        latency_ms=latency_ms,
        exit_code=exit_code,
        error=error_msg,
    )

    if exit_code != 0:
        if not quiet:
            diag = format_diagnostics(
                provider_name,
                selected_model.id,
                mode,
                latency_ms,
                run_id=run_id,
            )
            typer.echo(diag, err=True)
        raise typer.Exit(exit_code)

    if schema_obj is not None and result_content is not None:
        try:
            validated = validate_output(result_content, schema_obj)
            emit_result(validated, is_json=True, compact=compact)
        except Exception as exc:
            typer.echo(
                f"error: schema validation failed: {exc}\n"
                f"raw response: {result_content}",
                err=True,
            )
            raise typer.Exit(2)
    elif result_content is not None:
        emit_result(result_content, is_json=False)

    if not quiet:
        prompt_tokens = usage.get("prompt_tokens") if usage else None
        completion_tokens = usage.get("completion_tokens") if usage else None
        diag = format_diagnostics(
            provider_name,
            selected_model.id,
            mode,
            latency_ms,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            run_id=run_id,
        )
        typer.echo(diag, err=True)


# ─── list ──────────────────────────────────────────────────────────────


@app.command(name="list")
def list_command(
    what: str = typer.Argument(
        ..., help="providers, models, modes, or templates."
    ),
    provider_filter: str | None = typer.Option(
        None,
        "--provider",
        "-p",
        help="Filter models by provider.",
    ),
) -> None:
    """List providers, models, modes, or templates."""
    from llm_cli.config.loader import load_models
    from llm_cli.modes.registry import get_mode_source, resolve_modes
    from llm_cli.sampling.templates import resolve_templates

    providers_file = load_models()

    if what == "providers":
        for name, prov in providers_file.providers.items():
            kind = prov.provider_kind
            url = prov.base_url
            default = (
                " (default)" if name == providers_file.default_provider else ""
            )
            typer.echo(f"{name}{default}  {url}  [{kind}]")

    elif what == "models":
        if provider_filter:
            if provider_filter not in providers_file.providers:
                typer.echo(
                    f"error: unknown provider '{provider_filter}'", err=True
                )
                raise typer.Exit(1)
            prov = providers_file.providers[provider_filter]
            for m in prov.models:
                inputs = ", ".join(m.input)
                typer.echo(f"  {m.name or m.id}  id={m.id}  input=[{inputs}]")
        else:
            for name, prov in providers_file.providers.items():
                for m in prov.models:
                    inputs = ", ".join(m.input)
                    typer.echo(
                        f"{name}/{(m.name or m.id)}  id={m.id}  input=[{inputs}]"
                    )

    elif what == "modes":
        # Honor --provider filter; otherwise enumerate every (provider, model)
        # pair so per-model mode overrides remain visible.
        if provider_filter:
            if provider_filter not in providers_file.providers:
                typer.echo(
                    f"error: unknown provider '{provider_filter}'", err=True
                )
                raise typer.Exit(1)
            scopes = [
                (provider_filter, providers_file.providers[provider_filter])
            ]
        else:
            scopes = list(providers_file.providers.items())

        seen: dict[str, str] = {}
        for prov_name, prov in scopes:
            models_iter = prov.models if prov.models else [None]
            for sel_model in models_iter:
                if sel_model is None:
                    continue
                all_modes = resolve_modes(providers_file, prov_name, sel_model)
                for name in all_modes:
                    source = get_mode_source(
                        name, providers_file, prov_name, sel_model
                    )
                    key = f"{prov_name}/{sel_model.id}:{name}"
                    seen[key] = source

        if not seen:
            typer.echo("error: no models configured", err=True)
            raise typer.Exit(1)

        for key in sorted(seen):
            typer.echo(f"  {key}  ({seen[key]})")

    elif what == "templates":
        templates = resolve_templates(providers_file)
        # Determine which are user-defined
        user_template_names = set(
            (providers_file.sampling_templates or {}).keys()
        )
        for name in sorted(templates.keys()):
            source = "user" if name in user_template_names else "builtin"
            typer.echo(f"  {name}  ({source})")

    else:
        typer.echo(
            f"error: unknown list target '{what}'; "
            f"use: providers, models, modes, templates",
            err=True,
        )
        raise typer.Exit(1)


# ─── ping ──────────────────────────────────────────────────────────────


@app.command()
def ping(
    provider_filter: str | None = typer.Option(
        None,
        "--provider",
        "-p",
        help="Ping a specific provider.",
    ),
) -> None:
    """Ping one or all configured providers."""
    from llm_cli.config.loader import load_models

    providers_file = load_models()
    any_failed = False

    names = (
        [provider_filter]
        if provider_filter
        else sorted(providers_file.providers.keys())
    )

    with httpx.Client(timeout=10.0) as client:
        for name in names:
            if name not in providers_file.providers:
                typer.echo(f"{name}  ERROR: unknown provider")
                any_failed = True
                continue

            prov = providers_file.providers[name]
            url = prov.base_url.rstrip("/") + "/v1/models"
            headers = (
                {"Authorization": f"Bearer {prov.api_key}"}
                if prov.api_key
                else {}
            )

            start = time.monotonic()
            try:
                resp = client.get(url, headers=headers)
                latency = int((time.monotonic() - start) * 1000)
                if resp.status_code == 200:
                    typer.echo(f"{name}  OK  {latency}ms")
                else:
                    typer.echo(f"{name}  HTTP {resp.status_code}  {latency}ms")
                    any_failed = True
            except httpx.HTTPError as exc:
                latency = int((time.monotonic() - start) * 1000)
                typer.echo(f"{name}  ERROR: {exc}  {latency}ms")
                any_failed = True

    if any_failed:
        raise typer.Exit(3)


# ─── show ──────────────────────────────────────────────────────────────


@app.command()
def show(
    what: str = typer.Argument(..., help="provider, model, mode, or template."),
    name: str = typer.Argument(..., help="Name of the item to show."),
    provider_filter: str | None = typer.Option(
        None,
        "--provider",
        "-p",
        help="Provider for model/mode lookup.",
    ),
) -> None:
    """Show full definition of a provider, model, mode, or template."""
    from llm_cli.config.loader import load_models
    from llm_cli.modes.registry import resolve_modes
    from llm_cli.sampling.templates import resolve_templates

    providers_file = load_models()

    if what == "provider":
        if name not in providers_file.providers:
            typer.echo(f"error: unknown provider '{name}'", err=True)
            raise typer.Exit(1)
        prov = providers_file.providers[name]
        json.dump(prov.model_dump(), sys.stdout, indent=2, ensure_ascii=False)
        sys.stdout.write("\n")

    elif what == "model":
        prov_name = provider_filter
        if prov_name is None:
            prov_name = providers_file.default_provider
        if prov_name is None or prov_name not in providers_file.providers:
            typer.echo("error: use --provider to specify a provider", err=True)
            raise typer.Exit(1)

        prov = providers_file.providers[prov_name]
        found = None
        for m in prov.models:
            if m.id == name or m.name == name:
                found = m
                break

        if found is None:
            typer.echo(f"error: unknown model '{name}'", err=True)
            raise typer.Exit(1)

        json.dump(found.model_dump(), sys.stdout, indent=2, ensure_ascii=False)
        sys.stdout.write("\n")

    elif what == "mode":
        prov_name = provider_filter
        if prov_name is None:
            prov_name = providers_file.default_provider
        if prov_name is None or prov_name not in providers_file.providers:
            typer.echo("error: use --provider to specify a provider", err=True)
            raise typer.Exit(1)

        prov = providers_file.providers[prov_name]
        sel_model = prov.models[0] if prov.models else None
        if sel_model is None:
            typer.echo("error: no models configured", err=True)
            raise typer.Exit(1)

        all_modes = resolve_modes(providers_file, prov_name, sel_model)
        if name not in all_modes:
            typer.echo(f"error: unknown mode '{name}'", err=True)
            raise typer.Exit(1)

        mode_obj = all_modes[name]
        json.dump(
            mode_obj.model_dump(), sys.stdout, indent=2, ensure_ascii=False
        )
        sys.stdout.write("\n")

    elif what == "template":
        templates = resolve_templates(providers_file)
        if name not in templates:
            typer.echo(f"error: unknown template '{name}'", err=True)
            raise typer.Exit(1)

        json.dump(templates[name], sys.stdout, indent=2, ensure_ascii=False)
        sys.stdout.write("\n")

    else:
        typer.echo(
            f"error: unknown show target '{what}'; "
            f"use: provider, model, mode, template",
            err=True,
        )
        raise typer.Exit(1)


def main() -> None:
    try:
        app()
    except typer.Exit as exc:
        # Map typer's exit code 2 (usage error) to exit code 1
        code = exc.exit_code
        if code == 2:
            code = 1
        sys.exit(code)
    except SystemExit as exc:
        # Catch SystemExit from typer internals (e.g. --help)
        code = exc.code if isinstance(exc.code, int) else 1
        if code == 2:
            code = 1
        sys.exit(code)
    except Exception as exc:
        typer.echo(f"error: {exc}", err=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
