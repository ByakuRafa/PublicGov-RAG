import os
from functools import lru_cache
from typing import List

from langfuse import Langfuse
from langfuse.langchain import CallbackHandler

from app.core.config import settings


@lru_cache(maxsize=1)
def _init_langfuse_client() -> bool:
    if not settings.LANGFUSE_PUBLIC_KEY.strip() or not settings.LANGFUSE_SECRET_KEY.strip():
        return False

    os.environ["LANGFUSE_PUBLIC_KEY"] = settings.LANGFUSE_PUBLIC_KEY.strip()
    os.environ["LANGFUSE_SECRET_KEY"] = settings.LANGFUSE_SECRET_KEY.strip()
    host = settings.LANGFUSE_HOST.strip() or "https://cloud.langfuse.com"
    os.environ["LANGFUSE_HOST"] = host
    os.environ["LANGFUSE_BASE_URL"] = host

    Langfuse(
        public_key=os.environ["LANGFUSE_PUBLIC_KEY"],
        secret_key=os.environ["LANGFUSE_SECRET_KEY"],
        host=host,
    )
    return True


def get_langfuse_callbacks() -> List[CallbackHandler]:
    """Retorna CallbackHandler do Langfuse se as chaves estiverem configuradas no .env."""
    if not _init_langfuse_client():
        return []
    return [CallbackHandler()]
