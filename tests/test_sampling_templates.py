"""Tests for sampling templates."""

from __future__ import annotations

import pytest

from llm_cli.config.models_schema import ProvidersFile
from llm_cli.sampling.templates import (
    load_builtin_templates,
    resolve_templates,
)


def _make_providers_file(
    sampling_templates: dict | None = None,
) -> ProvidersFile:
    return ProvidersFile(
        providers={
            "test": {
                "baseUrl": "http://localhost/v1",
                "models": [{"id": "test", "input": ["text"]}],
            }
        },
        samplingTemplates=sampling_templates,
    )


class TestBuiltinTemplates:
    def test_load_builtin(self):
        templates = load_builtin_templates()
        assert "qwen3.6-thinking-general" in templates
        assert "qwen3.6-thinking-code" in templates
        assert "qwen3.6-instruct-general" in templates
        assert "qwen3.6-instruct-reasoning" in templates

    def test_builtin_values(self):
        templates = load_builtin_templates()
        t = templates["qwen3.6-thinking-general"]
        assert t["temperature"] == 1.0
        assert t["top_p"] == 0.95
        assert t["presence_penalty"] == 1.5


class TestResolveTemplates:
    def test_merge_builtin_and_user(self):
        pf = _make_providers_file(
            sampling_templates={"custom": {"temperature": 0.5}}
        )
        templates = resolve_templates(pf)
        assert "qwen3.6-thinking-general" in templates
        assert "custom" in templates
        assert templates["custom"]["temperature"] == 0.5

    def test_user_override_on_collision(self):
        pf = _make_providers_file(
            sampling_templates={
                "qwen3.6-thinking-general": {"temperature": 0.0}
            }
        )
        templates = resolve_templates(pf)
        assert templates["qwen3.6-thinking-general"]["temperature"] == 0.0

    def test_reject_non_sampling_keys(self):
        pf = _make_providers_file(
            sampling_templates={
                "bad": {"system_prompt": "hello", "temperature": 0.5}
            }
        )
        with pytest.raises(ValueError, match="non-sampling"):
            resolve_templates(pf)
