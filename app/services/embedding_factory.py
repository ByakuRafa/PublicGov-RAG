import os
import re
from functools import lru_cache
from typing import List, Optional

from langchain_core.embeddings import Embeddings
from langchain_huggingface import HuggingFaceEmbeddings
from sentence_transformers import SentenceTransformer

from app.core.config import settings


class EmbeddingGemma2Embeddings(Embeddings):
    """Wrapper LangChain para google/embeddinggemma-2 com Task-Steered Prompts e Matryoshka."""

    def __init__(
        self,
        model_name: str = "google/embeddinggemma-2",
        truncate_dim: Optional[int] = None,
        hf_token: Optional[str] = None,
    ) -> None:
        if truncate_dim is not None and truncate_dim not in (128, 256, 512, 768):
            raise ValueError(
                f"EMBEDDING_DIM={truncate_dim} inválido para EmbeddingGemma 2. "
                "Valores suportados (Matryoshka): 128, 256, 512 ou 768."
            )

        kwargs = {}
        if truncate_dim is not None:
            kwargs["truncate_dim"] = truncate_dim
        if hf_token:
            kwargs["token"] = hf_token

        self.model = SentenceTransformer(model_name, **kwargs)
        self.truncate_dim = truncate_dim

    def _encode(self, texts: List[str], prompt_name: str) -> List[List[float]]:
        encode_kwargs = {"normalize_embeddings": True}
        if self.truncate_dim is not None:
            encode_kwargs["truncate_dim"] = self.truncate_dim

        # Usa prompt_name se o modelo expuser prompts configurados; caso contrário faz fallback limpo
        available_prompts = getattr(self.model, "prompts", None) or {}
        if prompt_name in available_prompts:
            encode_kwargs["prompt_name"] = prompt_name

        vectors = self.model.encode(texts, **encode_kwargs)
        return [vec.tolist() for vec in vectors]

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        return self._encode(texts, prompt_name="Document")

    def embed_query(self, text: str) -> List[float]:
        return self._encode([text], prompt_name="SearchQuery")[0]


def sanitize_collection_name(
    model_name: Optional[str] = None,
    embedding_dim: Optional[int] = None,
) -> str:
    """Gera nome de coleção isolado por modelo e dimensão no pgvector."""
    resolved_model = (model_name or settings.EMBEDDING_MODEL).split("/")[-1].lower()
    slug = re.sub(r"[^a-z0-9]+", "_", resolved_model).strip("_")
    resolved_dim = embedding_dim if embedding_dim is not None else settings.EMBEDDING_DIM
    if resolved_dim is not None:
        return f"publicgov_{slug}_d{resolved_dim}"
    return f"publicgov_{slug}"


@lru_cache(maxsize=6)
def _cached_embeddings(model_name: str, embedding_dim: Optional[int]) -> Embeddings:
    hf_token = settings.HF_TOKEN.strip() or os.getenv("HF_TOKEN", "").strip() or None
    if hf_token:
        os.environ.setdefault("HF_TOKEN", hf_token)

    if "embeddinggemma-2" in model_name.lower():
        return EmbeddingGemma2Embeddings(
            model_name=model_name,
            truncate_dim=embedding_dim,
            hf_token=hf_token,
        )

    return HuggingFaceEmbeddings(
        model_name=model_name,
        encode_kwargs={"normalize_embeddings": True},
    )


def get_embeddings(
    model_name: Optional[str] = None,
    embedding_dim: Optional[int] = None,
) -> Embeddings:
    """Retorna instância singleton (em cache) do modelo de embeddings configurado."""
    resolved_model = model_name or settings.EMBEDDING_MODEL
    resolved_dim = embedding_dim if embedding_dim is not None else settings.EMBEDDING_DIM
    return _cached_embeddings(resolved_model, resolved_dim)
