import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")


@dataclass(frozen=True)
class LLMSettings:
    api_key: str
    base_url: str
    model: str
    timeout_seconds: float
    max_input_chars: int
    provider: str = "openai-responses"
    api_style: str = "responses"

    @property
    def configured(self) -> bool:
        return bool(self.api_key)

    @property
    def mode(self) -> str:
        return f"{self.provider}:{self.model}"


def get_llm_settings() -> LLMSettings:
    return LLMSettings(
        api_key=os.getenv("STORYFORGE_LLM_API_KEY", os.getenv("OPENAI_API_KEY", "")).strip(),
        base_url=os.getenv("STORYFORGE_LLM_BASE_URL", "https://api.openai.com/v1").rstrip("/"),
        model=os.getenv("STORYFORGE_LLM_MODEL", "gpt-5-mini").strip(),
        timeout_seconds=float(os.getenv("STORYFORGE_LLM_TIMEOUT_SECONDS", "60")),
        max_input_chars=int(os.getenv("STORYFORGE_LLM_MAX_INPUT_CHARS", "60000")),
        provider=os.getenv("STORYFORGE_LLM_PROVIDER", "openai-responses").strip(),
        api_style=os.getenv("STORYFORGE_LLM_API_STYLE", "responses").strip(),
    )


def get_cors_origins() -> list[str]:
    return [
        origin.strip()
        for origin in os.getenv("STORYFORGE_CORS_ORIGINS", "").split(",")
        if origin.strip()
    ]


def get_api_token() -> str:
    return os.getenv("STORYFORGE_API_TOKEN", "").strip()
