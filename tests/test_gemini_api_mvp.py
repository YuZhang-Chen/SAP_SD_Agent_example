from types import SimpleNamespace

import pytest

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
