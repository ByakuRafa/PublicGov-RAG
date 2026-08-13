from fastapi import FastAPI
from app.core.config import settings
from app.db.session import engine
from app.db.models import Base
from app.api.v1.router import api_router

# create database tables automatically
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="API para gestão e consulta de legislação pública e ouvidoria utilizando RAG."
)

app.include_router(api_router, prefix="/api/v1")

@app.get("/health", tags=["Health Check"])
def health_check():
    return {"status": "healthy", "version": settings.VERSION}