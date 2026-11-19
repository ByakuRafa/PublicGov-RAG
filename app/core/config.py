from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "PublicGov-RAG API"
    VERSION: str = "2.0.0"

    # Banco Relacional e Vetorial Unificado (PostgreSQL + pgvector)
    DATABASE_URL: str = "postgresql+psycopg://postgres:postgres@localhost:5432/publicgov"
    UPLOAD_DIR: str = "./storage/uploads"

    # LLM Google Gemini
    GOOGLE_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-2.5-flash"

    # Embeddings configuráveis (ex.: MiniLM ou google/embeddinggemma-2)
    EMBEDDING_MODEL: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    EMBEDDING_DIM: Optional[int] = None  # Matryoshka para EmbeddingGemma 2: 128, 256, 512, 768
    HF_TOKEN: str = ""

    # Busca Híbrida & Reranking
    RETRIEVAL_TOP_K: int = 10
    RERANK_TOP_N: int = 4
    ENABLE_RERANKER: bool = True
    RERANKER_MODEL: str = "ms-marco-MultiBERT-L-12"

    # Observabilidade Langfuse (via .env)
    LANGFUSE_PUBLIC_KEY: str = ""
    LANGFUSE_SECRET_KEY: str = ""
    LANGFUSE_HOST: str = "https://cloud.langfuse.com"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
