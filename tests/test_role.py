"""Tests for mode role resolution."""

from __future__ import annotations

from llm_cli.config.modes_schema import Mode


class TestModeRole:
    def test_default_role_none(self):
        """role default is None (inherit); effective_role resolves to 'user'."""
        mode = Mode()
        assert mode.role is None
        assert mode.effective_role == "user"

    def test_developer_role(self):
        mode = Mode(role="developer")
        assert mode.role == "developer"
        assert mode.effective_role == "developer"

    def test_invalid_role_rejected(self):
        import pytest

        with pytest.raises(Exception, match="invalid role"):
            Mode(role="invalid")

    def test_role_from_dict(self):
        mode = Mode(**{"role": "developer"})
        assert mode.role == "developer"

    def test_role_not_emitted_when_none(self):
        """When role is unset, model_dump(exclude_none=True) omits it."""
        mode = Mode(system_prompt="hi")
        dumped = mode.model_dump(exclude_none=True)
        assert "role" not in dumped
