"""Query embedding, behind an interface so the backend can change later."""
from abc import ABC, abstractmethod
from functools import lru_cache

from app.config import settings


class Embedder(ABC):
    @abstractmethod
    def embed(self, text: str) -> list[float]:
        ...


class SentenceTransformerEmbedder(Embedder):
    """Runs locally on CPU or CUDA via sentence-transformers."""

    def __init__(self, model_name: str, device: str = "cpu"):
        from sentence_transformers import SentenceTransformer

        self._model = SentenceTransformer(model_name, device=device)

    def embed(self, text: str) -> list[float]:
        return self._model.encode(text, normalize_embeddings=False).tolist()


class ApiEmbedder(Embedder):
    """Embeds via an OpenAI-compatible /embeddings endpoint, for when the
    embedding model is served remotely instead of run in-process."""

    def __init__(self, api_base: str, api_key: str, model: str, timeout: int = 30):
        import httpx

        self._client = httpx.Client(
            base_url=api_base,
            headers={"Authorization": f"Bearer {api_key}"} if api_key else {},
            timeout=timeout,
        )
        self._model = model

    def embed(self, text: str) -> list[float]:
        resp = self._client.post(
            "/embeddings", json={"model": self._model, "input": text}
        )
        resp.raise_for_status()
        return resp.json()["data"][0]["embedding"]


@lru_cache(maxsize=1)
def get_embedder() -> Embedder:
    return SentenceTransformerEmbedder(
        model_name=settings.embedding_model, device=settings.embedding_device
    )
