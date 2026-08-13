from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "PublicGov-RAG API"
    VERSION: str = "1.0.0"
    
    # Banco Relacional (padrão SQLite local para testes, expansível para Postgres)
    DATABASE_URL: str = "sqlite:///./storage/publicgov.db"
    
    # Banco Vetorial e Armazenamento
    CHROMA_PERSIST_DIR: str = "./storage/chroma_db"
    UPLOAD_DIR: str = "./storage/uploads"
    
    # Configurações de IA
    OPENAI_API_KEY: str = ""
    
    class Config:
        env_file = ".env"

settings = Settings()