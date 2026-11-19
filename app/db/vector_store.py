from typing import List, Optional
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from langchain_core.documents import Document
from langchain_postgres import PGVector

from app.core.config import settings
from app.db.session import engine
from app.services.embedding_factory import get_embeddings, sanitize_collection_name


def get_vector_store(
    embedding_model: Optional[str] = None,
    embedding_dim: Optional[int] = None,
    collection_name: Optional[str] = None,
) -> PGVector:
    """Retorna o Vector Store PostgreSQL + pgvector isolado por modelo/dimensão."""
    resolved_collection = collection_name or sanitize_collection_name(
        model_name=embedding_model,
        embedding_dim=embedding_dim,
    )
    embeddings = get_embeddings(
        model_name=embedding_model,
        embedding_dim=embedding_dim,
    )

    return PGVector(
        embeddings=embeddings,
        collection_name=resolved_collection,
        connection=settings.DATABASE_URL,
        use_jsonb=True,
    )


def get_all_indexed_documents(
    doc_type_filter: Optional[str] = None,
    collection_name: Optional[str] = None,
) -> List[Document]:
    """Lê todos os chunks persistidos no pgvector para indexação lexical (BM25)."""
    resolved_collection = collection_name or sanitize_collection_name()

    sql = """
        SELECT e.document, e.cmetadata
        FROM langchain_pg_embedding e
        INNER JOIN langchain_pg_collection c ON c.uuid = e.collection_id
        WHERE c.name = :collection_name
    """
    params = {"collection_name": resolved_collection}

    if doc_type_filter:
        sql += " AND e.cmetadata ->> 'doc_type' = :doc_type"
        params["doc_type"] = doc_type_filter

    try:
        with engine.connect() as conn:
            rows = conn.execute(text(sql), params).fetchall()
    except SQLAlchemyError:
        return []

    return [
        Document(
            page_content=row[0] or "",
            metadata=dict(row[1] or {}),
        )
        for row in rows
        if row[0]
    ]
