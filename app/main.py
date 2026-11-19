from contextlib import asynccontextmanager
from fastapi import FastAPI

from app.api.v1.router import api_router
from app.core.config import settings
from app.db.models import Base
from app.db.session import engine
from app.mcp_server import mcp

# Cria aplicação ASGI do servidor MCP e integra seu lifespan ao FastAPI
mcp_app = mcp.http_app(path="/")


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    async with mcp_app.lifespan(app):
        yield


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description=(
        "API e Servidor MCP para consulta e análise de legislação e matérias legislativas "
        "da Câmara de Vereadores de Santana do Livramento utilizando Busca Híbrida, Reranking e LangGraph."
    ),
    lifespan=lifespan,
)

app.include_router(api_router, prefix="/api/v1")
app.mount("/mcp", mcp_app)


@app.get("/health", tags=["Health Check"])
def health_check():
    return {
        "status": "healthy",
        "version": settings.VERSION,
        "llm_model": settings.GEMINI_MODEL,
        "embedding_model": settings.EMBEDDING_MODEL,
        "embedding_dim": settings.EMBEDDING_DIM,
        "vector_backend": "pgvector",
    }
