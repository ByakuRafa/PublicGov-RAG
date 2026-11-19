import argparse
import json
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from langchain_core.documents import Document
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.db.session import engine
from app.db.vector_store import get_all_indexed_documents, get_vector_store
from app.services.embedding_factory import sanitize_collection_name
from app.services.retrieval_service import hybrid_retrieve_and_rerank, invalidate_bm25_cache

EVALS_DIR = Path(__file__).resolve().parent
DATASET_PATH = EVALS_DIR / "dataset.json"
CORPUS_PATH = EVALS_DIR / "sample_corpus.json"
RESULTS_DIR = EVALS_DIR / "results"


@dataclass
class EmbeddingCandidate:
    label: str
    model_name: str
    embedding_dim: Optional[int]


DEFAULT_CANDIDATES: Dict[str, EmbeddingCandidate] = {
    "minilm": EmbeddingCandidate(
        label="MiniLM-L12-v2 (384d)",
        model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
        embedding_dim=None,
    ),
    "gemma-768": EmbeddingCandidate(
        label="EmbeddingGemma-2 (768d)",
        model_name="google/embeddinggemma-2",
        embedding_dim=768,
    ),
    "gemma-256": EmbeddingCandidate(
        label="EmbeddingGemma-2 (256d MRL)",
        model_name="google/embeddinggemma-2",
        embedding_dim=256,
    ),
}

RETRIEVAL_MODES = [
    ("vector_only", False, False),
    ("hybrid_rrf", True, False),
    ("hybrid_rrf_rerank", True, True),
]


def _load_corpus(from_db: bool) -> List[Document]:
    if from_db:
        docs = get_all_indexed_documents()
        if not docs:
            raise RuntimeError("Nenhum documento encontrado no pgvector ativo para --from-db.")
        return docs

    if not CORPUS_PATH.exists():
        raise FileNotFoundError(f"Corpus de exemplo não encontrado em {CORPUS_PATH}")

    with open(CORPUS_PATH, "r", encoding="utf-8") as f:
        raw = json.load(f)

    return [
        Document(page_content=item["page_content"], metadata=item.get("metadata", {}))
        for item in raw
    ]


def _collection_count(collection_name: str) -> int:
    sql = """
        SELECT COUNT(*)
        FROM langchain_pg_embedding e
        INNER JOIN langchain_pg_collection c ON c.uuid = e.collection_id
        WHERE c.name = :name
    """
    try:
        with engine.connect() as conn:
            return int(conn.execute(text(sql), {"name": collection_name}).scalar() or 0)
    except Exception:
        return 0


def _drop_collection(collection_name: str) -> None:
    sql = "DELETE FROM langchain_pg_collection WHERE name = :name"
    try:
        with engine.begin() as conn:
            conn.execute(text(sql), {"name": collection_name})
    except SQLAlchemyError:
        pass


def _compute_recall_and_mrr(
    retrieved_docs: List[Document],
    expected_source: str,
) -> tuple[float, float]:
    seen_sources: List[str] = []
    for doc in retrieved_docs:
        src = doc.metadata.get("source_file", "")
        if src and src not in seen_sources:
            seen_sources.append(src)

    if expected_source not in seen_sources:
        return 0.0, 0.0

    rank = seen_sources.index(expected_source) + 1
    return 1.0, 1.0 / rank


def run_benchmark(
    selected_keys: List[str],
    from_db: bool = False,
    reindex: bool = False,
) -> Dict[str, Any]:
    with open(DATASET_PATH, "r", encoding="utf-8") as f:
        dataset_items = [item for item in json.load(f) if item.get("in_scope") and item.get("expected_source")]

    corpus = _load_corpus(from_db=from_db)
    print(f"Corpus carregado: {len(corpus)} chunks | Perguntas in-scope: {len(dataset_items)}")

    summary_rows: List[Dict[str, Any]] = []
    skipped: List[Dict[str, str]] = []

    for key in selected_keys:
        candidate = DEFAULT_CANDIDATES[key]
        collection_name = f"bench_{sanitize_collection_name(candidate.model_name, candidate.embedding_dim)}"
        print(f"\n>>> Testando {candidate.label} (coleção: {collection_name})")

        try:
            if reindex:
                _drop_collection(collection_name)

            existing_count = _collection_count(collection_name)
            index_time_s = 0.0

            vector_store = get_vector_store(
                embedding_model=candidate.model_name,
                embedding_dim=candidate.embedding_dim,
                collection_name=collection_name,
            )

            if existing_count == 0:
                t0 = time.perf_counter()
                vector_store.add_documents(corpus)
                index_time_s = round(time.perf_counter() - t0, 2)
                print(f"    Indexados {len(corpus)} chunks em {index_time_s}s.")
            else:
                print(f"    Coleção já possui {existing_count} chunks indexados (use --reindex para recriar).")

            invalidate_bm25_cache()

            for mode_name, use_hybrid, use_reranker in RETRIEVAL_MODES:
                recalls: List[float] = []
                mrrs: List[float] = []
                latencies_ms: List[float] = []

                for item in dataset_items:
                    t_q = time.perf_counter()
                    docs = hybrid_retrieve_and_rerank(
                        query=item["question"],
                        top_k=10,
                        top_n=4,
                        use_hybrid=use_hybrid,
                        use_reranker=use_reranker,
                        embedding_model=candidate.model_name,
                        embedding_dim=candidate.embedding_dim,
                        collection_name=collection_name,
                        corpus_override=corpus if use_hybrid else None,
                    )
                    latencies_ms.append((time.perf_counter() - t_q) * 1000.0)
                    rec, mrr = _compute_recall_and_mrr(docs, item["expected_source"])
                    recalls.append(rec)
                    mrrs.append(mrr)

                row = {
                    "embedding": candidate.label,
                    "model_id": candidate.model_name,
                    "dim": candidate.embedding_dim or 384,
                    "mode": mode_name,
                    "recall_at_4": round(sum(recalls) / len(recalls), 4),
                    "mrr_at_4": round(sum(mrrs) / len(mrrs), 4),
                    "avg_latency_ms": round(sum(latencies_ms) / len(latencies_ms), 1),
                    "index_time_s": index_time_s,
                }
                summary_rows.append(row)
                print(
                    f"    [{mode_name:17s}] Recall@4={row['recall_at_4']:.2%} | "
                    f"MRR@4={row['mrr_at_4']:.4f} | Latência={row['avg_latency_ms']}ms"
                )
        except Exception as exc:
            msg = str(exc)
            print(f"    [PULADO] Falha ao carregar/executar {candidate.label}: {msg}")
            skipped.append({"embedding": candidate.label, "reason": msg})

    os.makedirs(RESULTS_DIR, exist_ok=True)
    json_out = RESULTS_DIR / "benchmark_embeddings.json"
    md_out = RESULTS_DIR / "benchmark_embeddings.md"

    payload = {"results": summary_rows, "skipped": skipped}
    with open(json_out, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    md_lines = [
        "# Benchmark de Embeddings e Estratégias de Retrieval — PublicGov-RAG\n",
        "| Embedding | Modo de Busca | Recall@4 | MRR@4 | Latência Média (ms) | Indexação (s) |",
        "| :--- | :--- | :---: | :---: | :---: | :---: |",
    ]
    for r in summary_rows:
        md_lines.append(
            f"| {r['embedding']} | `{r['mode']}` | {r['recall_at_4']:.2%} | "
            f"{r['mrr_at_4']:.4f} | {r['avg_latency_ms']} | {r['index_time_s']} |"
        )
    if skipped:
        md_lines.append("\n## Modelos Pulados")
        for s in skipped:
            md_lines.append(f"- **{s['embedding']}**: `{s['reason']}`")

    with open(md_out, "w", encoding="utf-8") as f:
        f.write("\n".join(md_lines) + "\n")

    print(f"\nRelatórios salvos em:\n- {json_out}\n- {md_out}")
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Benchmark comparativo entre MiniLM e EmbeddingGemma 2 (Full e Matryoshka) no pgvector."
    )
    parser.add_argument(
        "--models",
        nargs="+",
        choices=list(DEFAULT_CANDIDATES.keys()),
        default=list(DEFAULT_CANDIDATES.keys()),
        help="Modelos a incluir no benchmark.",
    )
    parser.add_argument(
        "--from-db",
        action="store_true",
        help="Lê chunks da coleção ativa do pgvector em vez de evals/sample_corpus.json.",
    )
    parser.add_argument(
        "--reindex",
        action="store_true",
        help="Recria as coleções de benchmark no pgvector antes de testar.",
    )
    args = parser.parse_args()
    run_benchmark(selected_keys=args.models, from_db=args.from_db, reindex=args.reindex)


if __name__ == "__main__":
    main()
