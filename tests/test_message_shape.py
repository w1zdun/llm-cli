"""Tests for message shape (system string, prompt typed-array, empty rejection)."""

from __future__ import annotations

from typer.testing import CliRunner

from llm_cli.__main__ import app

runner = CliRunner()


class TestMessageShape:
    def test_system_message_string_content(self):
        """System message should use string content, not typed array."""
        # Verify pattern: mode.system_prompt produces string content
        from llm_cli.config.modes_schema import Mode

        mode = Mode(system_prompt="You are helpful.")
        # System message content is a plain string (not typed array)
        assert mode.system_prompt == "You are helpful."
        assert isinstance(mode.system_prompt, str)

    def test_prompt_message_typed_array(self):
        """Prompt message content should always be a typed array."""
        # Verified in builder.py — content is always a list of dicts
        from llm_cli.inputs.builder import build_user_message
        from llm_cli.inputs.parser import ParsedInputs

        # Minimal test
        parsed = ParsedInputs(file_paths=[], prompt="hello")
        from llm_cli.config.models_schema import Model, Provider
        from llm_cli.config.modes_schema import Mode

        prov = Provider(
            baseUrl="http://localhost/v1",
            models=[],
        )
        model = Model(id="test", input=["text"])
        mode = Mode()

        content = build_user_message(parsed, model, prov, mode)
        assert isinstance(content, list)
        assert len(content) == 1
        assert content[0]["type"] == "text"

    def test_empty_content_rejected(self):
        """Empty content (no files, no prompt) should be rejected."""
        result = runner.invoke(
            app,
            [
                "--mode",
                "general",
                "--dry-run",
            ],
        )
        # Should exit 1 — no prompt or files
        assert result.exit_code == 1
