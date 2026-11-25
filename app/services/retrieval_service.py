import re
from functools import lru_cache
from typing import Dict, List, Optional, Tuple

from flashrank import Ranker, RerankRequest
from langchain_core.documents import Document
from rank_bm25 import BM25Okapi

from app.core.config import settings
from app.db.vector_store import get_all_indexed_documents, get_vector_store
from app.services.embedding_factory import sanitize_collection_name

# Cache em memória do índice lexical por (collection_name, doc_type_filter)
_bm25_cache: Dict[Tuple[str, Optional[str]], Tuple[BM25Okapi, List[Document]]] = {}


def invalidate_bm25_cache() -> None:
    """Invalida o cache BM25 após inserção/remoção de documentos."""
    _bm25_cache.clear()


def _tokenize_legislative(text: str) -> List[str]:
    """Tokeniza preservando identificadores legislativos como 67/2025 e 1.252/2016."""
    return re.findall(r"[a-zA-ZÀ-ÿ0-9]+(?:[./-][a-zA-ZÀ-ÿ0-9]+)*", text.lower())


@lru_cache(maxsize=2)
def _get_reranker(model_name: str) -> Ranker:
    return Ranker(model_name=model_name)


def _get_bm25_index(
    collection_name: str,
    doc_type_filter: Optional[str] = None,
    corpus_override: Optional[List[Document]] = None,
) -> Optional[Tuple[BM25Okapi, List[Document]]]:
    if corpus_override is not None:
        docs = [
            d for d in corpus_override
            if not doc_type_filter or d.metadata.get("doc_type") == doc_type_filter
        ]
        if not docs:
            return None
        tokenized = [_tokenize_legislative(d.page_content) for d in docs]
        return BM25Okapi(tokenized), docs

    cache_key = (collection_name, doc_type_filter)
    if cache_key in _bm25_cache:
        return _bm25_cache[cache_key]

    docs = get_all_indexed_documents(
        doc_type_filter=doc_type_filter,
        collection_name=collection_name,
    )
    if not docs:
        return None

    tokenized = [_tokenize_legislative(d.page_content) for d in docs]
    bm25 = BM25Okapi(tokenized)
    _bm25_cache[cache_key] = (bm25, docs)
    return bm25, docs


def _bm25_search(
    query: str,
    k: int,
    collection_name: str,
    doc_type_filter: Optional[str] = None,
    corpus_override: Optional[List[Document]] = None,
) -> List[Document]:
    index_data = _get_bm25_index(
        collection_name=collection_name,
        doc_type_filter=doc_type_filter,
        corpus_override=corpus_override,
    )
    if index_data is None:
        return []

    bm25, docs = index_data
    query_tokens = _tokenize_legislative(query)
    if not query_tokens:
        return []

    scores = bm25.get_scores(query_tokens)
    ranked_indices = sorted(
        range(len(docs)),
        key=lambda i: scores[i],
        reverse=True,
    )
    return [docs[i] for i in ranked_indices[:k] if scores[i] > 0]


def reciprocal_rank_fusion(
    ranked_lists: List[List[Document]],
    rrf_k: int = 60,
) -> List[Document]:
    """Funde múltiplas listas ranqueadas usando Reciprocal Rank Fusion (RRF)."""
    scores: Dict[str, float] = {}
    doc_map: Dict[str, Document] = {}

    for doc_list in ranked_lists:
        for rank, doc in enumerate(doc_list, start=1):
            doc_key = f"{doc.metadata.get('source_file', '')}::{doc.page_content}"
            doc_map[doc_key] = doc
            scores[doc_key] = scores.get(doc_key, 0.0) + 1.0 / (rrf_k + rank)

    sorted_keys = sorted(scores.keys(), key=lambda key: scores[key], reverse=True)
    fused_docs = []
    for key in sorted_keys:
        doc = doc_map[key]
        metadata = dict(doc.metadata)
        metadata["rrf_score"] = round(scores[key], 6)
        fused_docs.append(Document(page_content=doc.page_content, metadata=metadata))
    return fused_docs


def rerank_documents(
    query: str,
    documents: List[Document],
    top_n: int,
) -> List[Document]:
    """Reordena candidatos com Cross-Encoder (FlashRank)."""
    if not documents or not settings.ENABLE_RERANKER:
        return documents[:top_n]

    passages = [
        {
            "id": idx,
            "text": doc.page_content,
            "meta": dict(doc.metadata),
        }
        for idx, doc in enumerate(documents)
    ]
    try:
        ranker = _get_reranker(settings.RERANKER_MODEL)
        rerank_req = RerankRequest(query=query, passages=passages)
        results = ranker.rerank(rerank_req)

        reranked: List[Document] = []
        for item in results[:top_n]:
            meta = dict(item.get("meta") or {})
            meta["rerank_score"] = round(float(item.get("score", 0.0)), 6)
            reranked.append(Document(page_content=item["text"], metadata=meta))
        return reranked
    except Exception as exc:
        # Fallback defensivo caso modelo ou ambiente FlashRank apresente falha
        return documents[:top_n]


def hybrid_retrieve_and_rerank(
    query: str,
    doc_type_filter: Optional[str] = None,
    doc_types: Optional[List[str]] = None,
    top_k: Optional[int] = None,
    top_n: Optional[int] = None,
    use_hybrid: bool = True,
    use_reranker: bool = True,
    embedding_model: Optional[str] = None,
    embedding_dim: Optional[int] = None,
    collection_name: Optional[str] = None,
    corpus_override: Optional[List[Document]] = None,
) -> List[Document]:
    """Executa busca vetorial (pgvector) + BM25 com RRF e reranking FlashRank."""
    k = top_k or settings.RETRIEVAL_TOP_K
    n = top_n or settings.RERANK_TOP_N
    resolved_collection = collection_name or sanitize_collection_name(
        model_name=embedding_model,
        embedding_dim=embedding_dim,
    )

    vector_store = get_vector_store(
        embedding_model=embedding_model,
        embedding_dim=embedding_dim,
        collection_name=resolved_collection,
    )

    pg_filter = None
    if doc_type_filter:
        pg_filter = {"doc_type": doc_type_filter}
    elif doc_types:
        pg_filter = {"doc_type": {"$in": doc_types}}

    vector_docs = vector_store.similarity_search(query, k=k, filter=pg_filter)

    if not use_hybrid:
        candidates = vector_docs
    else:
        if doc_types and not doc_type_filter:
            # Filtra BM25 para múltiplos doc_types
            all_docs = corpus_override or get_all_indexed_documents(collection_name=resolved_collection)
            filtered_corpus = [d for d in all_docs if d.metadata.get("doc_type") in doc_types]
            bm25_docs = _bm25_search(
                query=query,
                k=k,
                collection_name=resolved_collection,
                corpus_override=filtered_corpus,
            )
        else:
            bm25_docs = _bm25_search(
                query=query,
                k=k,
                collection_name=resolved_collection,
                doc_type_filter=doc_type_filter,
                corpus_override=corpus_override,
            )

        candidates = reciprocal_rank_fusion([vector_docs, bm25_docs])[:k]

    if use_reranker and settings.ENABLE_RERANKER:
        return rerank_documents(query=query, documents=candidates, top_n=n)
    return candidates[:n]
