"""Embedding provider abstraction."""

import time
import os
import numpy as np
from src.config import OPENAI_API_KEY, EMBEDDING_MODEL, EMBEDDING_DIMENSION, LOCAL_EMBEDDING_DIMENSION


class EmbeddingProvider:
    """Abstraction over embedding models. Uses OpenAI if key is set, else local."""

    def __init__(self):
        if OPENAI_API_KEY:
            self._provider = "openai"
            self._dimension = EMBEDDING_DIMENSION
            self._model = EMBEDDING_MODEL
            import openai
            self._client = openai.OpenAI(api_key=OPENAI_API_KEY)
        else:
            self._provider = "local"
            self._dimension = LOCAL_EMBEDDING_DIMENSION
            self._model = "all-MiniLM-L6-v2"
            self._load_local_model()

    def _load_local_model(self):
        """Load model directly with transformers (lighter than sentence-transformers)."""
        import torch
        from transformers import AutoTokenizer, AutoModel

        local_path = os.path.expanduser("~/.cache/st-model")
        if os.path.exists(os.path.join(local_path, "model.safetensors")):
            model_path = local_path
        else:
            model_path = "sentence-transformers/all-MiniLM-L6-v2"

        self._tokenizer = AutoTokenizer.from_pretrained(model_path)
        self._torch_model = AutoModel.from_pretrained(model_path)
        self._torch_model.eval()

    @property
    def dimension(self) -> int:
        return self._dimension

    @property
    def model_name(self) -> str:
        return self._model

    @property
    def provider_name(self) -> str:
        return self._provider

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Embed a batch of texts."""
        start = time.time()
        if self._provider == "openai":
            result = self._embed_openai(texts)
        else:
            result = self._embed_local(texts)
        elapsed = time.time() - start
        print(f"  Embedded {len(texts)} texts in {elapsed:.1f}s ({self._provider}/{self._model})")
        return result

    def embed_query(self, text: str) -> list[float]:
        """Embed a single query."""
        if self._provider == "openai":
            return self._embed_openai([text])[0]
        return self._embed_local([text])[0]

    def _embed_openai(self, texts: list[str]) -> list[list[float]]:
        batch_size = 100
        all_embeddings = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            response = self._client.embeddings.create(model=self._model, input=batch)
            all_embeddings.extend([d.embedding for d in response.data])
        return all_embeddings

    def _embed_local(self, texts: list[str]) -> list[list[float]]:
        """Embed using transformers directly with mean pooling."""
        import torch

        all_embeddings = []
        batch_size = 16
        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            encoded = self._tokenizer(
                batch, padding=True, truncation=True, max_length=512, return_tensors="pt"
            )
            with torch.no_grad():
                outputs = self._torch_model(**encoded)

            # Mean pooling
            attention_mask = encoded["attention_mask"]
            token_embeddings = outputs.last_hidden_state
            input_mask_expanded = attention_mask.unsqueeze(-1).expand(token_embeddings.size()).float()
            embeddings = torch.sum(token_embeddings * input_mask_expanded, 1) / torch.clamp(
                input_mask_expanded.sum(1), min=1e-9
            )
            # Normalize
            embeddings = torch.nn.functional.normalize(embeddings, p=2, dim=1)
            all_embeddings.extend(embeddings.cpu().numpy().tolist())

        return all_embeddings
