"""Regression tests for bugs found in code review of consolidate-config-and-cli."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

import pytest
from typer.testing import CliRunner

from llm_cli.__main__ import _last_not_none, app
from llm_cli.config.models_schema import Model, Provider, ProvidersFile
from llm_cli.config.modes_schema import Mode
from llm_cli.modes.registry import resolve_modes
from llm_cli.resolve.cli_overrides import parse_set_flags
from llm_cli.resolve.extra_body import resolve_extra_body
from llm_cli.resolve.sampling import resolve_sampling
from llm_cli.resolve.thinking import route_thinking


def _make_cfg() -> dict:
    return {
        "default_provider": "p",
        "default_model": "m",
        "providers": {
            "p": {
                "baseUrl": "http://localhost/v1",
                "providerKind": "llama.cpp",
                "models": [{"id": "m", "input": ["text"]}],
            }
        },
    }


def _runner_with_cfg(cfg: dict):
    tmp = tempfile.mkdtemp()
    os.environ["XDG_CONFIG_HOME"] = tmp
    cfg_dir = Path(tmp) / "llm-cli"
    cfg_dir.mkdir(parents=True, exist_ok=True)
    (cfg_dir / "models.json").write_text(json.dumps(cfg))
    return CliRunner(), cfg_dir


class TestPositionalArgs:
    def test_option_value_not_treated_as_positional(self):
        runner, _ = _runner_with_cfg(_make_cfg())
        # `general` is the value of `--mode`, not a positional.
        # `50` is the value of `--max-pages`, not a positional.
        res = runner.invoke(
            app,
            [
                "--mode",
                "general",
                "--max-pages",
                "50",
                "--dry-run",
                "the prompt",
            ],
        )
        assert res.exit_code == 0, res.output
        body = json.loads(res.output[: res.output.rfind("}") + 1])
        text_parts = [
            p["text"]
            for p in body["messages"][-1]["content"]
            if p.get("type") == "text"
        ]
        assert text_parts == ["the prompt"]


class TestLastNotNone:
    def test_cli_wins_over_provider(self):
        # [provider, model, mode, cli]
        assert _last_not_none([200, None, 50, 100]) == 100

    def test_falls_back_to_provider_when_all_others_none(self):
        assert _last_not_none([200, None, None, None]) == 200

    def test_all_none(self):
        assert _last_not_none([None, None, None, None]) is None


class TestRouteThinkingNoMutation:
    def test_does_not_mutate_provider_extra_body(self):
        prov = Provider(
            baseUrl="http://x/v1",
            extra_body={"chat_template_kwargs": {"a": 1}},
            models=[],
        )
        model = Model(
            id="m", input=["text"], thinkingFormat="qwen-chat-template"
        )
        mode = Mode()
        extra_body = resolve_extra_body(prov, model, mode)
        sampling = {"enable_thinking": True}
        sampling, extra_body = route_thinking(model, sampling, extra_body)
        assert prov.extra_body == {"chat_template_kwargs": {"a": 1}}
        assert extra_body["chat_template_kwargs"]["enable_thinking"] is True

    def test_strips_thinking_for_non_qwen(self):
        model = Model(id="m", input=["text"])
        sampling = {"enable_thinking": True, "temperature": 0.7}
        sampling, extra_body = route_thinking(model, sampling, {})
        assert "enable_thinking" not in sampling
        assert sampling == {"temperature": 0.7}
        assert extra_body == {}


class TestRoleInheritance:
    def test_lower_layer_role_inherited(self):
        """A provider override that omits 'role' must not clobber global's
        'developer' value back to 'user'."""
        pf = ProvidersFile(
            providers={
                "p": {
                    "baseUrl": "http://x/v1",
                    "modes": {
                        "code": {"system_prompt": "Provider prompt."},
                    },
                    "models": [
                        {
                            "id": "m",
                            "input": ["text"],
                            "supportsDeveloperRole": True,
                        }
                    ],
                }
            },
            modes={"code": {"role": "developer"}},
        )
        model = pf.providers["p"].models[0]
        modes = resolve_modes(pf, "p", model)
        assert modes["code"].effective_role == "developer"


class TestSetFlags:
    def test_dotted_key_to_extra_body_only(self):
        sampling, extra_body = parse_set_flags(
            ["chat_template_kwargs.enable_thinking=true"]
        )
        assert sampling == {}
        assert extra_body == {"chat_template_kwargs": {"enable_thinking": True}}

    def test_flat_key_to_sampling_only(self):
        sampling, extra_body = parse_set_flags(["temperature=0.5"])
        assert sampling == {"temperature": 0.5}
        assert extra_body == {}


class TestSamplingTemplatePrecedence:
    def test_provider_value_survives_template_in_mode(self):
        """A template referenced by a higher-priority layer must NOT override
        an explicit value from a lower-priority layer."""
        prov = Provider(
            baseUrl="http://x/v1",
            sampling={"temperature": 0.1},
            models=[],
        )
        model = Model(id="m", input=["text"])
        mode = Mode(sampling={"sampling_template": "T"})
        templates = {"T": {"temperature": 1.0, "top_p": 0.95}}

        resolved = resolve_sampling(prov, model, mode, None, templates)
        # Provider's explicit 0.1 wins; template fills top_p only.
        assert resolved["temperature"] == 0.1
        assert resolved["top_p"] == 0.95

    def test_layer_keys_override_its_template(self):
        prov = Provider(baseUrl="http://x/v1", models=[])
        model = Model(id="m", input=["text"])
        mode = Mode(sampling={"sampling_template": "T", "temperature": 0.2})
        templates = {"T": {"temperature": 1.0, "top_p": 0.95}}

        resolved = resolve_sampling(prov, model, mode, None, templates)
        assert resolved["temperature"] == 0.2
        assert resolved["top_p"] == 0.95


class TestNestedTemplate:
    def test_recursive_template_expansion(self):
        prov = Provider(baseUrl="http://x/v1", models=[])
        model = Model(id="m", input=["text"])
        mode = Mode(sampling={"sampling_template": "A"})
        templates = {
            "A": {"sampling_template": "B", "temperature": 0.5},
            "B": {"top_p": 0.9, "top_k": 20},
        }
        resolved = resolve_sampling(prov, model, mode, None, templates)
        assert resolved["temperature"] == 0.5
        assert resolved["top_p"] == 0.9
        assert resolved["top_k"] == 20
        assert "sampling_template" not in resolved

    def test_cycle_detection(self):
        prov = Provider(baseUrl="http://x/v1", models=[])
        model = Model(id="m", input=["text"])
        mode = Mode(sampling={"sampling_template": "A"})
        templates = {
            "A": {"sampling_template": "B"},
            "B": {"sampling_template": "A"},
        }
        with pytest.raises(Exception):
            resolve_sampling(prov, model, mode, None, templates)


class TestModelMaxTokensRejected:
    def test_legacy_max_tokens_rejected(self):
        with pytest.raises(
            Exception, match="max_tokens is no longer supported"
        ):
            Model(id="m", input=["text"], max_tokens=512)


class TestListModesHonorsProvider:
    def test_list_modes_uses_provider_filter(self):
        cfg = {
            "default_provider": "p1",
            "providers": {
                "p1": {
                    "baseUrl": "http://x/v1",
                    "modes": {"only_p1": {"system_prompt": "x"}},
                    "models": [{"id": "m1", "input": ["text"]}],
                },
                "p2": {
                    "baseUrl": "http://y/v1",
                    "modes": {"only_p2": {"system_prompt": "y"}},
                    "models": [{"id": "m2", "input": ["text"]}],
                },
            },
        }
        runner, _ = _runner_with_cfg(cfg)
        res = runner.invoke(app, ["list", "modes", "--provider", "p2"])
        assert res.exit_code == 0, res.output
        assert "only_p2" in res.output
        assert "only_p1" not in res.output
