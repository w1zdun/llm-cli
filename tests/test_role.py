"""Tests for mode role resolution."""

from __future__ import annotations

from llm_cli.config.modes_schema import Mode


class TestModeRole:
    def test_default_role_user(self):
        mode = Mode()
        assert mode.role == "user"

    def test_developer_role(self):
        mode = Mode(role="developer")
        assert mode.role == "developer"

    def test_invalid_role_rejected(self):
        import pytest

        with pytest.raises(Exception, match="invalid role"):
            Mode(role="invalid")

    def test_role_from_dict(self):
        mode = Mode(**{"role": "developer"})
        assert mode.role == "developer"
