import os
from functools import lru_cache
from typing import Any, List, Optional

from app.core.config import settings

try:
    from langfuse import Langfuse
    from langfuse.langchain import CallbackHandler
except ImportError:  # pragma: no cover - fallback caso pacote opcional nao esteja instalado
    Langfuse = None  # type: ignore[assignment]
    CallbackHandler = None  # type: ignore[assignment]

_langfuse_client: Optional[Any] = None


@lru_cache(maxsize=1)
def _init_langfuse_client() -> bool:
    global _langfuse_client
    if Langfuse is None or CallbackHandler is None:
        return False

    if not settings.LANGFUSE_PUBLIC_KEY.strip() or not settings.LANGFUSE_SECRET_KEY.strip():
        return False

    os.environ["LANGFUSE_PUBLIC_KEY"] = settings.LANGFUSE_PUBLIC_KEY.strip()
    os.environ["LANGFUSE_SECRET_KEY"] = settings.LANGFUSE_SECRET_KEY.strip()
    host = settings.LANGFUSE_HOST.strip() or "https://cloud.langfuse.com"
    os.environ["LANGFUSE_HOST"] = host
    os.environ["LANGFUSE_BASE_URL"] = host

    _langfuse_client = Langfuse(
        public_key=os.environ["LANGFUSE_PUBLIC_KEY"],
        secret_key=os.environ["LANGFUSE_SECRET_KEY"],
        host=host,
    )
    return True


def is_langfuse_enabled() -> bool:
    """Indica se o cliente Langfuse está configurado e pronto para receber traces."""
    return _init_langfuse_client()


def get_langfuse_callbacks() -> List[Any]:
    """Retorna CallbackHandler do Langfuse se as chaves estiverem configuradas no .env."""
    if not _init_langfuse_client() or CallbackHandler is None:
        return []
    return [CallbackHandler()]


def flush_langfuse() -> None:
    """Garante o envio assíncrono dos eventos pendentes para o painel Langfuse."""
    if _langfuse_client is not None:
        try:
            _langfuse_client.flush()
        except Exception:
            pass
