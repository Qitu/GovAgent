import re

import pytest

from generative_agents.modules.model.llm_model import (
    parse_llm_output,
    create_llm_model,
    OllamaLLMModel,
)


def test_parse_llm_output_match_last():
    # Should return last matched item by default
    text = """line1\nvalue: A\nvalue: B\nend"""
    out = parse_llm_output(text, r"value: (.+)")
    assert out == "B"


def test_parse_llm_output_match_first_and_all():
    text = """x\nfoo: 1\nbar\nfoo: 2"""
    assert parse_llm_output(text, r"foo: (\d+)", mode="match_first") == "1"
    assert parse_llm_output(text, r"foo: (\d+)", mode="match_all") == ["1", "2"]


def test_parse_llm_output_ignore_empty_true():
    # When ignore_empty True and no match, should return None
    text = "no matches here"
    out = parse_llm_output(text, r"foo: (\d+)", mode="match_last", ignore_empty=True)
    assert out is None


def test_create_llm_model_provider_selection():
    assert create_llm_model({"provider": "ollama", "api_key": "", "base_url": "http://x", "model": "m"}).__class__.__name__ == "OllamaLLMModel"
    assert create_llm_model({"provider": "openai", "api_key": "k", "base_url": "http://x", "model": "gpt"}).__class__.__name__ == "OpenAILLMModel"
    with pytest.raises(NotImplementedError):
        create_llm_model({"provider": "unknown", "api_key": "", "base_url": "", "model": ""})


def test_ollama_completion_monkeypatched(monkeypatch):
    # Monkeypatch network call to be deterministic and offline
    cfg = {"provider": "ollama", "api_key": "", "base_url": "http://localhost:11434", "model": "qwen3:latest"}
    model = create_llm_model(cfg)
    assert isinstance(model, OllamaLLMModel)

    def fake_ollama_chat(messages, temperature):
        # Simulate OpenAI-compatible shape
        return {
            "choices": [
                {
                    "message": {
                        # Include <think> ... </think> which should be stripped
                        "content": "<think>hidden reasoning</think>Final answer"
                    }
                }
            ],
            "usage": {"prompt_tokens": 5, "completion_tokens": 7, "total_tokens": 12},
        }

    monkeypatch.setattr(model, "ollama_chat", lambda messages, temperature: fake_ollama_chat(messages, temperature))

    out = model._completion("hello", temperature=0.1)
    # Output should have think tags removed
    assert out == "Final answer"

    # If prompt already contains /nothink, it should not append it again (we check by behavior)
    out2 = model._completion("hello\n/nothink", temperature=0.1)
    assert out2 == "Final answer"
