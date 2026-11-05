from types import SimpleNamespace

import pytest
from google.genai import errors

from sap_sd_agent.gemini_api import ask_gemini, check_gemini


class FakeModels:
    def __init__(self):
        self.last_call = None

    def generate_content(self, **kwargs):
        self.last_call = kwargs
        return SimpleNamespace(text=" GEMINI_OK ")


class FakeGeminiClient:
    def __init__(self):
        self.models = FakeModels()


def test_ask_gemini_sends_model_and_prompt():
    fake_client = FakeGeminiClient()
    config = {"api_key": "demo", "model": "gemini-test", "timeout": 30}

    answer = ask_gemini(config, "你好", client=fake_client)

    assert answer == "GEMINI_OK"
    assert fake_client.models.last_call["model"] == "gemini-test"
    assert fake_client.models.last_call["contents"] == "你好"


def test_empty_prompt_is_rejected():
    config = {"api_key": "demo", "model": "gemini-test", "timeout": 30}

    with pytest.raises(ValueError, match="Prompt cannot be empty"):
        ask_gemini(config, "  ", client=FakeGeminiClient())


def test_check_gemini_uses_small_test_prompt():
    fake_client = FakeGeminiClient()
    config = {"api_key": "demo", "model": "gemini-test", "timeout": 30}

    answer = ask_gemini(config, "請只回答 GEMINI_OK", client=fake_client)

    assert answer == "GEMINI_OK"

def test_503_is_retried(monkeypatch):
    fake_client = FakeGeminiClient()
    calls = 0
    waits = []

    def generate_content(**kwargs):
        nonlocal calls
        calls += 1
        if calls < 3:
            raise errors.ServerError(503, {"error": {"message": "busy"}})
        return SimpleNamespace(text="GEMINI_OK")

    fake_client.models.generate_content = generate_content
    monkeypatch.setattr("sap_sd_agent.gemini_api.time.sleep", waits.append)

    answer = ask_gemini(
        {"api_key": "demo", "model": "gemini-test", "timeout": 30},
        "hello",
        client=fake_client,
    )

    assert answer == "GEMINI_OK"
    assert calls == 3
    assert waits == [1, 2]
