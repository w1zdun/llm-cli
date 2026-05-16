"""Unit tests for config loading."""

import tempfile
from pathlib import Path

import pytest

from llm_cli.config.jsonc import JsoncError, read_jsonc
from llm_cli.config.models_schema import (
    Model,
    Provider,
    ProvidersFile,
    compat_param_mapping_resolved,
)
from llm_cli.config.modes_schema import (
    Mode,
    SamplingTemplate,
    parse_modes_file,
)
from llm_cli.config.paths import config_dir, data_dir, ensure_data_dir
from llm_cli.modes.registry import resolve_modes

FIXTURES = Path(__file__).parent / "fixtures"


class TestReadJsonc:
    def test_valid_jsonc(self):
        path = FIXTURES / "pi_models.json"
        result = read_jsonc(path)
        assert isinstance(result, dict)
        assert "providers" in result

    def test_missing_file(self):
        path = Path("/tmp/does-not-exist.json")
        with pytest.raises(JsoncError) as exc_info:
            read_jsonc(path)
        assert "file not found" in str(exc_info.value)

    def test_malformed_jsonc(self):
        path = FIXTURES / "malformed.json"
        with pytest.raises(JsoncError):
            read_jsonc(path)


class TestPaths:
    def test_config_dir(self):
        d = config_dir()
        assert d.name == "llm-cli"

    def test_data_dir(self):
        d = data_dir()
        assert d.name == "llm-cli"
        assert "share" in str(d).split("/")[-2]

    def test_ensure_data_dir(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            import os

            old = os.environ.get("XDG_DATA_HOME")
            os.environ["XDG_DATA_HOME"] = tmpdir
            try:
                d = ensure_data_dir()
                assert d.exists()
                mode = d.stat().st_mode & 0o777
                assert mode == 0o700
            finally:
                if old is not None:
                    os.environ["XDG_DATA_HOME"] = old
                else:
                    os.environ.pop("XDG_DATA_HOME", None)


class TestModelsSchema:
    def test_pi_shaped_loads(self):
        raw = read_jsonc(FIXTURES / "pi_models.json")
        pf = ProvidersFile(**raw)
        assert "nuc" in pf.providers
        assert pf.default_provider == "nuc"

    def test_camel_case_aliases(self):
        model = Model(
            id="./test",
            input=["text"],
            contextWindow=4096,
            thinkingFormat="none",
        )
        assert model.context_window == 4096
        assert model.thinking_format == "none"

    def test_snake_case_aliases(self):
        model = Model(
            id="./test",
            input=["text"],
            context_window=4096,
            thinking_format="none",
        )
        assert model.context_window == 4096
        assert model.thinking_format == "none"

    def test_missing_base_url(self):
        with pytest.raises(Exception):
            Provider(
                models=[],
            )

    def test_invalid_input_modality(self):
        with pytest.raises(Exception):
            Model(
                id="./test",
                input=["audio"],
            )

    def test_provider_kind_validation(self):
        p = Provider(baseUrl="http://localhost/v1", models=[])
        assert p.provider_kind == "openai-generic"

    def test_thinking_level_map_rejected(self):
        with pytest.raises(Exception, match="thinkingLevelMap"):
            Model(
                id="./test",
                input=["text"],
                thinkingLevelMap={"low": "1024"},
            )

    def test_file_passing_default(self):
        p = Provider(
            baseUrl="http://localhost/v1",
            providerKind="llama.cpp",
            models=[],
        )
        assert p.file_passing == "path"

        p2 = Provider(
            baseUrl="http://localhost/v1",
            providerKind="openai-generic",
            models=[],
        )
        assert p2.file_passing == "inline"

    def test_param_mapping_resolved(self):
        p = Provider(
            baseUrl="http://localhost/v1",
            providerKind="ollama",
            models=[],
        )
        mapping = compat_param_mapping_resolved(p)
        assert mapping["max_output_tokens"] == "num_predict"

        p2 = Provider(
            baseUrl="http://localhost/v1",
            providerKind="llama.cpp",
            models=[],
        )
        mapping2 = compat_param_mapping_resolved(p2)
        assert mapping2["max_output_tokens"] == "max_tokens"

    def test_modes_four_layer_resolution(self):
        """Test that modes merge across builtin/global/provider/model."""
        raw = read_jsonc(FIXTURES / "pi_models.json")
        pf = ProvidersFile(**raw)
        prov = pf.providers["nuc"]
        model = prov.models[0]

        modes = resolve_modes(pf, "nuc", model)
        assert "code" in modes

        # Code mode should have provider-level temperature override
        code_mode = modes["code"]
        assert code_mode.sampling["temperature"] == 0.1

        # Should inherit max_output_tokens from model-level mode
        assert code_mode.max_output_tokens == 4096


class TestModesSchema:
    def test_parse_modes_file(self):
        raw = {
            "custom": {
                "sampling": {"temperature": 0.1},
                "system_prompt": "You are helpful.",
            }
        }
        modes = parse_modes_file(raw)
        assert "custom" in modes
        assert modes["custom"].sampling["temperature"] == 0.1

    def test_mode_with_schema(self):
        raw = {
            "ocr": {
                "sampling": {"temperature": 0.0},
                "schema": {
                    "type": "object",
                    "properties": {"text": {"type": "string"}},
                },
            }
        }
        modes = parse_modes_file(raw)
        mode = modes["ocr"]
        assert mode.output_schema is not None
        assert mode.output_schema["type"] == "object"

    def test_camel_case_requires_input(self):
        raw = {
            "test": {
                "requiresInput": "image",
            }
        }
        modes = parse_modes_file(raw)
        assert modes["test"].requires_input == "image"

    def test_mode_role_validation(self):
        mode = Mode(role="developer")
        assert mode.role == "developer"

        with pytest.raises(Exception, match="invalid role"):
            Mode(role="invalid")

    def test_sampling_template_rejects_non_sampling_keys(self):
        with pytest.raises(Exception, match="non-sampling"):
            SamplingTemplate(root={"system_prompt": "hello"})

    def test_sampling_template_accepts_sampling_keys(self):
        template = SamplingTemplate(root={"temperature": 0.7, "top_p": 0.9})
        assert template.root["temperature"] == 0.7
