"""Tests for four-layer mode resolution."""

from __future__ import annotations

from llm_cli.config.models_schema import ProvidersFile
from llm_cli.modes.registry import get_mode_source, resolve_modes


def _make_providers_file() -> ProvidersFile:
    return ProvidersFile(
        providers={
            "test": {
                "baseUrl": "http://localhost/v1",
                "modes": {
                    "code": {
                        "sampling": {"temperature": 0.15},
                        "system_prompt": "Provider prompt.",
                    }
                },
                "models": [
                    {
                        "id": "test-model",
                        "input": ["text"],
                        "modes": {
                            "code": {
                                "sampling": {"top_p": 0.85},
                            }
                        },
                    }
                ],
            }
        },
        modes={
            "code": {
                "sampling": {"temperature": 0.2, "top_p": 0.9},
                "system_prompt": "Global prompt.",
            }
        },
    )


class TestFourLayerMerge:
    def test_builtin_present(self):
        pf = _make_providers_file()
        model = pf.providers["test"].models[0]
        modes = resolve_modes(pf, "test", model)

        # Builtin modes should be present
        assert "general" in modes

    def test_global_layer_applies(self):
        pf = _make_providers_file()
        model = pf.providers["test"].models[0]
        modes = resolve_modes(pf, "test", model)

        code = modes["code"]
        # Global temperature=0.2, provider overrides to 0.15
        assert code.sampling["temperature"] == 0.15

    def test_provider_wins_over_global(self):
        pf = _make_providers_file()
        model = pf.providers["test"].models[0]
        modes = resolve_modes(pf, "test", model)

        code = modes["code"]
        # Provider system_prompt wins
        assert code.system_prompt == "Provider prompt."

    def test_model_layer_wins(self):
        pf = _make_providers_file()
        model = pf.providers["test"].models[0]
        modes = resolve_modes(pf, "test", model)

        code = modes["code"]
        # Model top_p=0.85 wins over global 0.9
        assert code.sampling["top_p"] == 0.85

    def test_fields_inherit_when_not_overridden(self):
        pf = _make_providers_file()
        model = pf.providers["test"].models[0]
        modes = resolve_modes(pf, "test", model)

        code = modes["code"]
        # system_prompt from provider (model didn't override)
        assert code.system_prompt == "Provider prompt."


class TestModeSource:
    def test_model_source(self):
        pf = _make_providers_file()
        model = pf.providers["test"].models[0]
        source = get_mode_source("code", pf, "test", model)
        assert source == "model"

    def test_builtin_source(self):
        pf = _make_providers_file()
        model = pf.providers["test"].models[0]
        source = get_mode_source("general", pf, "test", model)
        assert source == "builtin"

    def test_global_source(self):
        """When mode is only in global, source is 'global'."""
        pf = ProvidersFile(
            providers={
                "test": {
                    "baseUrl": "http://localhost/v1",
                    "models": [{"id": "m", "input": ["text"]}],
                }
            },
            modes={"custom": {"system_prompt": "X"}},
        )
        model = pf.providers["test"].models[0]
        source = get_mode_source("custom", pf, "test", model)
        assert source == "global"

    def test_provider_source(self):
        pf = ProvidersFile(
            providers={
                "test": {
                    "baseUrl": "http://localhost/v1",
                    "modes": {"prov-mode": {"system_prompt": "P"}},
                    "models": [{"id": "m", "input": ["text"]}],
                }
            },
        )
        model = pf.providers["test"].models[0]
        source = get_mode_source("prov-mode", pf, "test", model)
        assert source == "provider"
