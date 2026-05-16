"""Tests for CLI default command (no `run` subcommand)."""

from __future__ import annotations

from typer.testing import CliRunner

from llm_cli.__main__ import app

runner = CliRunner()


class TestCliDefault:
    def test_no_args_exits_nonzero(self):
        """llm-cli with no args prints usage and exits non-zero."""
        result = runner.invoke(app, [])
        assert result.exit_code != 0

    def test_version_flag(self):
        result = runner.invoke(app, ["--version"])
        assert result.exit_code == 0
        assert "llm-cli" in result.stdout

    def test_list_templates_exits_ok(self):
        """llm-cli list templates works."""
        result = runner.invoke(app, ["list", "templates"])
        # May fail if no config, but command should exist
        assert result.exit_code in (0, 1)

    def test_run_command_not_exists(self):
        """`llm-cli run` should not be a valid subcommand."""
        result = runner.invoke(app, ["run", "--help"])
        # Typer may treat 'run' as a positional arg, not a subcommand
        assert result.exit_code != 0

    def test_mode_flag_on_root(self):
        """--mode flag should be on the root command."""
        # Test by invoking with --mode (will fail without config, but flag should be recognized)
        result = runner.invoke(app, ["--mode", "general", "test"])
        # Exit 1 expected (no config), but not "unknown option"
        assert "no such option" not in (result.stdout + result.stderr).lower()

    def test_new_flags_present(self):
        """New flags should be available on root command."""
        # Test --enable-thinking flag is recognized
        result = runner.invoke(
            app, ["--enable-thinking", "--mode", "general", "test"]
        )
        assert "no such option" not in (result.stdout + result.stderr).lower()

        # Test --sampling-template
        result = runner.invoke(
            app,
            [
                "--sampling-template",
                "qwen3.6-thinking-code",
                "--mode",
                "general",
                "test",
            ],
        )
        assert "no such option" not in (result.stdout + result.stderr).lower()

        # Test --max-context-tokens
        result = runner.invoke(
            app, ["--max-context-tokens", "1000", "--mode", "general", "test"]
        )
        assert "no such option" not in (result.stdout + result.stderr).lower()
