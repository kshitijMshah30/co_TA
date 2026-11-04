"""Step 9: generate the reply. Backends are swappable so Inference can plug in their server.

LLM_BACKEND:
  mock               - no model; echoes the retrieved context (default, free, for wiring tests)
  anthropic          - Claude API (needs ANTHROPIC_API_KEY; LLM_MODEL defaults below)
  openai_compatible  - any OpenAI-style /v1/chat/completions server: OpenAI, or a
                       self-hosted vLLM / Ollama / LM Studio from the Inference team
                       (needs LLM_MODEL, optional LLM_BASE_URL and OPENAI_API_KEY)
"""

from typing import Protocol

from .config import Settings

DEFAULT_ANTHROPIC_MODEL = "claude-haiku-5-5"
MAX_TOKENS = 600


class LLM(Protocol):
    name: str

    def generate(self, system: str, messages: list[dict]) -> str: ...


class MockLLM:
    name = "mock"

    def generate(self, system: str, messages: list[dict]) -> str:
        return "[MOCK LLM RESPONSE]\n" + messages[-1]["content"][:1500]


class AnthropicLLM:
    name = "anthropic"

    def __init__(self, model: str | None):
        import anthropic

        self.client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY
        self.model = model or DEFAULT_ANTHROPIC_MODEL

    def generate(self, system: str, messages: list[dict]) -> str:
        resp = self.client.messages.create(
            model=self.model, max_tokens=MAX_TOKENS, system=system, messages=messages
        )
        return "".join(block.text for block in resp.content if block.type == "text")


class OpenAICompatibleLLM:
    name = "openai_compatible"

    def __init__(self, model: str | None, base_url: str | None):
        if not model:
            raise RuntimeError("LLM_MODEL is required for LLM_BACKEND=openai_compatible")
        from openai import OpenAI

        # Local servers usually accept any key; OpenAI itself reads OPENAI_API_KEY.
        self.client = OpenAI(base_url=base_url) if base_url else OpenAI()
        self.model = model

    def generate(self, system: str, messages: list[dict]) -> str:
        resp = self.client.chat.completions.create(
            model=self.model,
            max_tokens=MAX_TOKENS,
            messages=[{"role": "system", "content": system}, *messages],
        )
        return resp.choices[0].message.content or ""


def make_llm(settings: Settings) -> LLM:
    if settings.llm_backend == "mock":
        return MockLLM()
    if settings.llm_backend == "anthropic":
        return AnthropicLLM(settings.llm_model)
    if settings.llm_backend == "openai_compatible":
        return OpenAICompatibleLLM(settings.llm_model, settings.llm_base_url)
    raise RuntimeError(f"Unknown LLM_BACKEND {settings.llm_backend!r}")
