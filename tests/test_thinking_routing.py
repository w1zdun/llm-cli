"""Tests for thinking key routing (resolve/thinking.py)."""

from __future__ import annotations

from llm_cli.config.models_schema import Model
from llm_cli.resolve.thinking import route_thinking


class TestQwenChatTemplate:
    def test_enable_thinking_routed(self):
        model = Model(
            id="test",
            input=["text"],
            thinkingFormat="qwen-chat-template",
        )
        sampling = {"enable_thinking": True, "temperature": 0.7}
        extra_body: dict = {}

        sampling, extra_body = route_thinking(model, sampling, extra_body)

        assert "enable_thinking" not in sampling
        assert sampling["temperature"] == 0.7
        assert extra_body["chat_template_kwargs"]["enable_thinking"] is True

    def test_preserve_thinking_routed(self):
        model = Model(
            id="test",
            input=["text"],
            thinkingFormat="qwen-chat-template",
        )
        sampling = {
            "enable_thinking": True,
            "preserve_thinking": False,
        }
        extra_body: dict = {}

        sampling, extra_body = route_thinking(model, sampling, extra_body)

        assert "enable_thinking" not in sampling
        assert "preserve_thinking" not in sampling
        ct = extra_body["chat_template_kwargs"]
        assert ct["enable_thinking"] is True
        assert ct["preserve_thinking"] is False

    def test_both_keys_together(self):
        model = Model(
            id="test",
            input=["text"],
            thinkingFormat="qwen-chat-template",
        )
        sampling = {
            "enable_thinking": True,
            "preserve_thinking": True,
            "top_p": 0.9,
        }
        extra_body: dict = {}

        sampling, extra_body = route_thinking(model, sampling, extra_body)

        assert set(sampling.keys()) == {"top_p"}
        ct = extra_body["chat_template_kwargs"]
        assert ct["enable_thinking"] is True
        assert ct["preserve_thinking"] is True


class TestOtherFormats:
    def test_unknown_format_stripped(self):
        """Non-qwen formats have no wire destination — strip the keys."""
        model = Model(
            id="test",
            input=["text"],
            thinkingFormat="openai-reasoning-effort",
        )
        sampling = {"enable_thinking": True, "temperature": 0.7}
        extra_body: dict = {}

        sampling, extra_body = route_thinking(model, sampling, extra_body)

        assert "enable_thinking" not in sampling
        assert sampling == {"temperature": 0.7}
        assert extra_body == {}

    def test_no_thinking_format_stripped(self):
        model = Model(
            id="test",
            input=["text"],
        )
        sampling = {"enable_thinking": True}
        extra_body: dict = {}

        sampling, extra_body = route_thinking(model, sampling, extra_body)

        assert "enable_thinking" not in sampling
        assert extra_body == {}

    def test_no_thinking_keys(self):
        model = Model(
            id="test",
            input=["text"],
            thinkingFormat="qwen-chat-template",
        )
        sampling = {"temperature": 0.7}
        extra_body: dict = {}

        sampling, extra_body = route_thinking(model, sampling, extra_body)

        assert sampling == {"temperature": 0.7}
        assert extra_body == {}
