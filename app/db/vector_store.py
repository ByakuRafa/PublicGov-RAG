import os
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from app.core.config import settings

def get_vector_store() -> Chroma:
    os.makedirs(settings.CHROMA_PERSIST_DIR, exist_ok=True)

    embeddings = HuggingFaceEmbeddings(
        model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    )

    return Chroma(
        collection_name="publicgov_documents",
        embedding_function=embeddings,
        persist_directory=settings.CHROMA_PERSIST_DIR
    )