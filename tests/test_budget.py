"""Tests for token budget estimation."""

from __future__ import annotations

from llm_cli.inputs.budget import estimate_tokens


class TestEstimateTokens:
    def test_text_only(self):
        messages = [{"role": "user", "content": "Hello, world!"}]
        tokens = estimate_tokens(messages)
        # "Hello, world!" = 13 chars -> ceil(13/4) = 4 + 2 role overhead = 6
        assert tokens >= 4

    def test_long_text(self):
        text = "x" * 1000
        messages = [{"role": "user", "content": text}]
        tokens = estimate_tokens(messages)
        # ceil(1000/4) = 250 + 2 = 252
        assert tokens == 252

    def test_typed_array_text(self):
        messages = [
            {
                "role": "user",
                "content": [{"type": "text", "text": "Hello"}],
            }
        ]
        tokens = estimate_tokens(messages)
        assert tokens >= 2  # role overhead

    def test_image_entry(self):
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Describe"},
                    {
                        "type": "image_url",
                        "image_url": {"url": "data:image/png;base64,xxx"},
                    },
                ],
            }
        ]
        tokens = estimate_tokens(messages)
        assert tokens >= 1024  # image costs 1024

    def test_multiple_messages(self):
        messages = [
            {"role": "system", "content": "You are helpful."},
            {"role": "user", "content": "Hello"},
        ]
        tokens = estimate_tokens(messages)
        assert tokens >= 10  # both messages count

    def test_empty_content(self):
        messages = [{"role": "user", "content": ""}]
        tokens = estimate_tokens(messages)
        assert tokens >= 2  # at least role overhead
