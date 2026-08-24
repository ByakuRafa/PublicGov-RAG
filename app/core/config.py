from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "PublicGov-RAG API"
    VERSION: str = "1.0.0"
    
    DATABASE_URL: str = "sqlite:///./storage/publicgov.db"
    CHROMA_PERSIST_DIR: str = "./storage/chroma_db"
    UPLOAD_DIR: str = "./storage/uploads"
    
    GOOGLE_API_KEY: str = ""
    
    class Config:
        env_file = ".env"

settings = Settings()