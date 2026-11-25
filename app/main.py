from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.observability import is_langfuse_enabled
from app.db.models import Base, ensure_query_logs_schema
from app.db.session import engine
from app.mcp_server import mcp

# Cria aplicação ASGI do servidor MCP e integra seu lifespan ao FastAPI
mcp_app = mcp.http_app(path="/")


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    ensure_query_logs_schema(engine)
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

STATIC_DIR = Path(__file__).resolve().parent / "static"
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/", include_in_schema=False)
def serve_workbench():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/health", tags=["Health Check"])
def health_check():
    return {
        "status": "healthy",
        "version": settings.VERSION,
        "llm_model": settings.GEMINI_MODEL,
        "embedding_model": settings.EMBEDDING_MODEL,
        "embedding_dim": settings.EMBEDDING_DIM,
        "vector_backend": "pgvector",
        "langfuse_enabled": is_langfuse_enabled(),
    }
