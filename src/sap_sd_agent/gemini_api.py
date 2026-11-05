import os

from dotenv import load_dotenv
from google import genai
from google.genai import types


def load_gemini_config():
    """Read the Gemini API settings from .env."""
    load_dotenv()

    config = {
        "api_key": os.getenv("GEMINI_API_KEY", ""),
        "model": os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite"),
        "timeout": float(os.getenv("GEMINI_TIMEOUT_SECONDS", "30")),
    }
    if not config["api_key"]:
        raise ValueError("Missing GEMINI_API_KEY in .env")

    return config


def make_gemini_client(config):
    """Create the official Google Gen AI client."""
    return genai.Client(
        api_key=config["api_key"],
        http_options=types.HttpOptions(timeout=int(config["timeout"] * 1000)),
    )


def ask_gemini(config, prompt, client=None):
    """Send one prompt to Gemini and return plain text."""
    if not prompt.strip():
        raise ValueError("Prompt cannot be empty")

    created_here = client is None
    client = client or make_gemini_client(config)

    response = client.models.generate_content(
        model=config["model"],
        contents=prompt,
        config=types.GenerateContentConfig(temperature=0),
    )

    if created_here:
        client.close()
    if not response.text:
        raise ValueError("Gemini returned an empty response")

    return response.text.strip()


def check_gemini(config=None):
    """Small smoke test used by students to verify their API key."""
    config = config or load_gemini_config()
    return ask_gemini(config, "請只回答 GEMINI_OK")


if __name__ == "__main__":
    print(check_gemini())
