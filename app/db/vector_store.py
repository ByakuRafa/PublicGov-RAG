import os
from langchain_chroma import Chroma
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from app.core.config import settings

def get_vector_store() -> Chroma:
    os.makedirs(settings.CHROMA_PERSIST_DIR, exist_ok=True)
    
    embeddings = GoogleGenerativeAIEmbeddings(
        model="models/text-embedding-004",
        google_api_key=settings.GOOGLE_API_KEY
    )
    
    return Chroma(
        collection_name="publicgov_documents",
        embedding_function=embeddings,
        persist_directory=settings.CHROMA_PERSIST_DIR
    )