import os
from langchain_community.vectorstores import Chroma
from langchain_openai import OpenAIEmbeddings
from app.core.config import settings

def get_vector_store() -> Chroma:
    os.makedirs(settings.CHROMA_PERSIST_DIR, exist_ok=True)
    embeddings = OpenAIEmbeddings(openai_api_key=settings.OPENAI_API_KEY)
    
    return Chroma(
        collection_name="publicgov_documents",
        embedding_function=embeddings,
        persist_directory=settings.CHROMA_PERSIST_DIR
    )