import argparse
import asyncio
import json
import os
import time
from pathlib import Path
from typing import Any, Dict, List

from datasets import Dataset
from langchain_google_genai import ChatGoogleGenerativeAI
from ragas import RunConfig, evaluate
from ragas.embeddings import LangchainEmbeddingsWrapper
from ragas.llms import LangchainLLMWrapper
from ragas.metrics import answer_relevancy, faithfulness

from app.core.config import settings
from app.db.session import SessionLocal
from app.services.agent_service import run_legislative_agent
from app.services.embedding_factory import get_embeddings

DATASET_PATH = Path(__file__).resolve().parent / "dataset.json"
RESULTS_DIR = Path(__file__).resolve().parent / "results"


async def _collect_predictions(samples: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    db = SessionLocal()
    records: List[Dict[str, Any]] = []
    try:
        for item in samples:
            started = time.perf_counter()
            res = await run_legislative_agent(
                question=item["question"],
                doc_type_filter=item.get("doc_type_filter"),
                db=db,
            )
            elapsed_ms = (time.perf_counter() - started) * 1000.0

            expected_source = item.get("expected_source")
            source_hit = None
            if expected_source:
                source_hit = expected_source in res["sources"]

            records.append(
                {
                    "id": item["id"],
                    "question": item["question"],
                    "answer": res["answer"],
                    "contexts": res["contexts"] or ["Nenhum contexto recuperado."],
                    "ground_truth": item["ground_truth"],
                    "expected_source": expected_source,
                    "predicted_sources": res["sources"],
                    "source_hit": source_hit,
                    "tools_used": res["tools_used"],
                    "in_scope": item.get("in_scope", True),
                    "latency_ms": round(elapsed_ms, 1),
                }
            )
            print(
                f"[{item['id']}] hit={source_hit} | tools={res['tools_used']} | "
                f"latency={elapsed_ms:.0f}ms"
            )
    finally:
        db.close()

    return records


def run_evaluation(limit: int | None = None, skip_ragas: bool = False) -> Dict[str, Any]:
    if not DATASET_PATH.exists():
        raise FileNotFoundError(f"Dataset não encontrado em {DATASET_PATH}")

    with open(DATASET_PATH, "r", encoding="utf-8") as f:
        dataset_items = json.load(f)

    if limit is not None:
        dataset_items = dataset_items[:limit]

    if not settings.GOOGLE_API_KEY:
        raise RuntimeError(
            "GOOGLE_API_KEY não configurada no .env. Configure a chave antes de rodar evals."
        )

    print(f"Executando {len(dataset_items)} perguntas contra o agente ({settings.GEMINI_MODEL})...")
    predictions = asyncio.run(_collect_predictions(dataset_items))

    in_scope_hits = [p["source_hit"] for p in predictions if p["source_hit"] is not None]
    recall_at_k = (sum(1 for h in in_scope_hits if h) / len(in_scope_hits)) if in_scope_hits else 0.0
    avg_latency_ms = sum(p["latency_ms"] for p in predictions) / len(predictions) if predictions else 0.0

    ragas_summary: Dict[str, Any] = {}
    if not skip_ragas:
        print("\nCalculando métricas RAGAS (faithfulness e answer_relevancy)...")
        ragas_dataset = Dataset.from_dict(
            {
                "question": [p["question"] for p in predictions],
                "answer": [p["answer"] for p in predictions],
                "contexts": [p["contexts"] for p in predictions],
                "ground_truth": [p["ground_truth"] for p in predictions],
            }
        )
        judge_llm = LangchainLLMWrapper(
            ChatGoogleGenerativeAI(
                model=settings.GEMINI_MODEL,
                temperature=0.0,
                google_api_key=settings.GOOGLE_API_KEY,
            )
        )
        judge_embeddings = LangchainEmbeddingsWrapper(get_embeddings())

        ragas_result = evaluate(
            dataset=ragas_dataset,
            metrics=[faithfulness, answer_relevancy],
            llm=judge_llm,
            embeddings=judge_embeddings,
            run_config=RunConfig(max_workers=1, max_retries=5),
        )
        df = ragas_result.to_pandas()
        ragas_summary = {
            "faithfulness": round(float(df["faithfulness"].mean()), 4),
            "answer_relevancy": round(float(df["answer_relevancy"].mean()), 4),
        }

    report = {
        "model": settings.GEMINI_MODEL,
        "embedding_model": settings.EMBEDDING_MODEL,
        "embedding_dim": settings.EMBEDDING_DIM,
        "total_questions": len(predictions),
        "source_recall_at_4": round(recall_at_k, 4),
        "avg_latency_ms": round(avg_latency_ms, 1),
        "ragas": ragas_summary,
        "details": predictions,
    }

    os.makedirs(RESULTS_DIR, exist_ok=True)
    out_path = RESULTS_DIR / "latest_report.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print("\n=== Resumo da Avaliação ===")
    print(f"Perguntas avaliadas : {report['total_questions']}")
    print(f"Source Recall@4     : {report['source_recall_at_4']:.2%}")
    print(f"Latência média      : {report['avg_latency_ms']} ms")
    if ragas_summary:
        print(f"Faithfulness (RAGAS): {ragas_summary['faithfulness']:.4f}")
        print(f"Answer Relevancy    : {ragas_summary['answer_relevancy']:.4f}")
    print(f"Relatório salvo em  : {out_path}")

    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Executa suíte de Evals RAGAS do PublicGov-RAG.")
    parser.add_argument("--limit", type=int, default=None, help="Limita quantidade de perguntas.")
    parser.add_argument(
        "--skip-ragas",
        action="store_true",
        help="Executa apenas o agente e métricas de recuperação/latência sem juiz RAGAS.",
    )
    args = parser.parse_args()
    run_evaluation(limit=args.limit, skip_ragas=args.skip_ragas)


if __name__ == "__main__":
    main()
