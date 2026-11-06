"""LLM generation backends, swappable so the GPU server can drop in later."""
from abc import ABC, abstractmethod
from functools import lru_cache

from app.config import settings


class LLM(ABC):
    @abstractmethod
    def generate(self, messages: list[dict]) -> str:
        ...


class MockLLM(LLM):
    """Echoes the retrieved context instead of calling a real model.
    Used for all testing while the GPU box is unreachable."""

    def generate(self, messages: list[dict]) -> str:
        user_msg = next((m["content"] for m in messages if m["role"] == "user"), "")
        return f"[MOCK LLM RESPONSE]\n{user_msg}"


class OpenAICompatibleLLM(LLM):
    """Talks to any OpenAI-compatible chat completions endpoint
    (Purdue GenAI Studio, a self-hosted GPU server, etc.)."""

    def __init__(self, api_base: str, api_key: str, model: str, timeout: int = 30):
        import httpx

        self._client = httpx.Client(
            base_url=api_base,
            headers={"Authorization": f"Bearer {api_key}"} if api_key else {},
            timeout=timeout,
        )
        self._model = model

    def generate(self, messages: list[dict]) -> str:
        resp = self._client.post(
            "/chat/completions",
            json={"model": self._model, "messages": messages},
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]


@lru_cache(maxsize=1)
def get_llm() -> LLM:
    if settings.llm_backend == "mock":
        return MockLLM()
    if settings.llm_backend == "openai_compatible":
        return OpenAICompatibleLLM(
            api_base=settings.llm_api_base,
            api_key=settings.llm_api_key,
            model=settings.llm_model,
            timeout=settings.llm_timeout_seconds,
        )
    raise ValueError(f"Unknown LLM_BACKEND: {settings.llm_backend}")
