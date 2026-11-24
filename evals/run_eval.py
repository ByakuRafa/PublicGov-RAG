import argparse
import asyncio
import json
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from sqlalchemy import func

from app.core.config import settings
from app.core.constants import DOC_TYPES
from app.db.models import DocumentModel
from app.db.session import SessionLocal
from app.services.agent_service import PROMPT_VERSIONS, run_legislative_agent

EVALS_DIR = Path(__file__).resolve().parent
GOLDEN_DATASET_PATH = EVALS_DIR / "golden_dataset.json"
LEGACY_DATASET_PATH = EVALS_DIR / "dataset.json"
RESULTS_DIR = EVALS_DIR / "results"

ABSTENTION_PATTERNS = (
    "não foi localizada",
    "não foram localizadas",
    "não consta",
    "não constam",
    "não localizado",
    "fora do escopo",
    "não há informações",
    "não há registro",
    "não encontrei",
    "não foi possível localizar",
    "não existem registros",
    "sem evidência",
)


def resolve_dataset_path(custom_path: Optional[str] = None) -> Path:
    if custom_path:
        return Path(custom_path)
    return GOLDEN_DATASET_PATH if GOLDEN_DATASET_PATH.exists() else LEGACY_DATASET_PATH


def is_abstention_response(answer: str) -> bool:
    """Detecta se a resposta recusou/absteve-se adequadamente por falta de evidência ou escopo."""
    normalized = (answer or "").lower()
    return any(pattern in normalized for pattern in ABSTENTION_PATTERNS)


def score_prediction(item: Dict[str, Any], pred: Dict[str, Any]) -> Dict[str, Any]:
    """Calcula métricas individuais de recuperação, citação explícita de fontes e abstenção."""
    expected_source = item.get("expected_source")
    answerable = item.get("answerable", item.get("in_scope", True) and expected_source is not None)
    predicted_sources = pred.get("predicted_sources") or []
    cited_sources = pred.get("cited_sources") or []
    answer_text = pred.get("answer") or ""

    if answerable and expected_source:
        source_hit = expected_source in predicted_sources
        retrieval_precision = (
            round(1.0 / len(predicted_sources), 4) if source_hit and predicted_sources else 0.0
        )
        if cited_sources:
            citation_precision = (
                round(1.0 / len(cited_sources), 4) if expected_source in cited_sources else 0.0
            )
            citation_hit = expected_source in cited_sources
        else:
            citation_precision = 0.0
            citation_hit = False
        abstention_hit = None
    else:
        source_hit = None
        retrieval_precision = None
        abstained = is_abstention_response(answer_text)
        no_false_citation = len(cited_sources) == 0
        abstention_hit = bool(abstained and no_false_citation)
        citation_hit = None
        # Penaliza se citou arquivo falso em pergunta sem resposta; se absteve sem citar, é preciso
        citation_precision = 1.0 if no_false_citation else 0.0

    return {
        "source_hit": source_hit,
        "retrieval_precision": retrieval_precision,
        "citation_hit": citation_hit,
        "citation_precision": citation_precision,
        "abstention_hit": abstention_hit,
    }


def inspect_corpus_coverage(db=None) -> Dict[str, Any]:
    """Consulta a tabela documents para apurar total de PDFs indexados e cobertura nas 8 categorias."""
    own_session = db is None
    session = db or SessionLocal()
    try:
        rows = (
            session.query(DocumentModel.doc_type, func.count(DocumentModel.id))
            .group_by(DocumentModel.doc_type)
            .all()
        )
        counts_by_type = {doc_type: int(cnt) for doc_type, cnt in rows}
        total_documents = sum(counts_by_type.values())
        covered = [dt for dt in DOC_TYPES if counts_by_type.get(dt, 0) > 0]
        missing = [dt for dt in DOC_TYPES if counts_by_type.get(dt, 0) == 0]
        return {
            "indexed_documents_count": total_documents,
            "counts_by_doc_type": counts_by_type,
            "covered_categories": covered,
            "missing_categories": missing,
            "categories_covered_count": len(covered),
            "categories_total_count": len(DOC_TYPES),
        }
    except Exception as exc:
        return {
            "indexed_documents_count": 0,
            "counts_by_doc_type": {},
            "covered_categories": [],
            "missing_categories": list(DOC_TYPES),
            "categories_covered_count": 0,
            "categories_total_count": len(DOC_TYPES),
            "db_warning": str(exc),
        }
    finally:
        if own_session:
            session.close()


async def _collect_predictions(
    samples: List[Dict[str, Any]],
    prompt_version: str,
) -> List[Dict[str, Any]]:
    db = SessionLocal()
    records: List[Dict[str, Any]] = []
    try:
        for item in samples:
            started = time.perf_counter()
            res = await run_legislative_agent(
                question=item["question"],
                doc_type_filter=item.get("doc_type_filter"),
                db=db,
                prompt_version=prompt_version,
            )
            elapsed_ms = res.get("latency_ms") or round((time.perf_counter() - started) * 1000.0, 2)

            base_pred = {
                "id": item["id"],
                "doc_type": item.get("doc_type"),
                "question": item["question"],
                "answer": res["answer"],
                "contexts": res["contexts"] or ["Nenhum contexto recuperado."],
                "ground_truth": item["ground_truth"],
                "expected_source": item.get("expected_source"),
                "predicted_sources": res["sources"],
                "cited_sources": res.get("cited_sources", []),
                "tools_used": res["tools_used"],
                "in_scope": item.get("in_scope", True),
                "answerable": item.get("answerable", item.get("in_scope", True)),
                "prompt_version": prompt_version,
                "latency_ms": round(float(elapsed_ms), 2),
                "prompt_tokens": int(res.get("prompt_tokens") or 0),
                "completion_tokens": int(res.get("completion_tokens") or 0),
                "estimated_cost_usd": float(res.get("estimated_cost_usd") or 0.0),
            }
            base_pred.update(score_prediction(item, base_pred))
            records.append(base_pred)
            print(
                f"[{prompt_version}][{item['id']}] recall_hit={base_pred['source_hit']} | "
                f"cite_prec={base_pred['citation_precision']} | abstention={base_pred['abstention_hit']} | "
                f"tokens={base_pred['prompt_tokens']}+{base_pred['completion_tokens']} | "
                f"latency={base_pred['latency_ms']:.0f}ms"
            )
    finally:
        db.close()

    return records


def _compute_ragas_metrics(predictions: List[Dict[str, Any]]) -> Dict[str, Any]:
    from datasets import Dataset
    from langchain_google_genai import ChatGoogleGenerativeAI
    from ragas import RunConfig, evaluate
    from ragas.embeddings import LangchainEmbeddingsWrapper
    from ragas.llms import LangchainLLMWrapper
    from ragas.metrics import answer_relevancy, faithfulness
    from app.services.embedding_factory import get_embeddings

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
    return {
        "faithfulness": round(float(df["faithfulness"].mean()), 4),
        "answer_relevancy": round(float(df["answer_relevancy"].mean()), 4),
    }


def summarize_prompt_run(
    prompt_version: str,
    predictions: List[Dict[str, Any]],
    ragas_summary: Dict[str, Any],
) -> Dict[str, Any]:
    """Agrega todas as métricas de avaliação para uma versão de prompt."""
    recall_hits = [p["source_hit"] for p in predictions if p["source_hit"] is not None]
    citation_hits = [p["citation_hit"] for p in predictions if p["citation_hit"] is not None]
    citation_precs = [p["citation_precision"] for p in predictions if p["citation_precision"] is not None]
    abstention_hits = [p["abstention_hit"] for p in predictions if p["abstention_hit"] is not None]

    total_n = len(predictions)
    return {
        "prompt_version": prompt_version,
        "total_questions": total_n,
        "answerable_questions": len(recall_hits),
        "unanswerable_questions": len(abstention_hits),
        "source_recall_at_4": round(sum(1 for h in recall_hits if h) / len(recall_hits), 4)
        if recall_hits
        else 0.0,
        "explicit_citation_recall": round(sum(1 for h in citation_hits if h) / len(citation_hits), 4)
        if citation_hits
        else 0.0,
        "source_citation_precision": round(sum(citation_precs) / len(citation_precs), 4)
        if citation_precs
        else 0.0,
        "abstention_rate": round(sum(1 for h in abstention_hits if h) / len(abstention_hits), 4)
        if abstention_hits
        else 0.0,
        "avg_latency_ms": round(sum(p["latency_ms"] for p in predictions) / total_n, 2)
        if total_n
        else 0.0,
        "total_prompt_tokens": sum(p["prompt_tokens"] for p in predictions),
        "total_completion_tokens": sum(p["completion_tokens"] for p in predictions),
        "total_estimated_cost_usd": round(sum(p["estimated_cost_usd"] for p in predictions), 6),
        "ragas": ragas_summary,
    }


def render_comparison_markdown(report: Dict[str, Any]) -> str:
    """Gera tabela comparativa em Markdown pronta para documentação e currículo."""
    coverage = report.get("corpus_coverage", {})
    lines = [
        "# Relatório Comparativo de Evals — PublicGov-RAG",
        "",
        f"- **Dataset:** `{report.get('dataset_path')}` ({report.get('total_questions')} perguntas)",
        f"- **Modelo LLM:** `{report.get('model')}` | **Embeddings:** `{report.get('embedding_model')}`",
        f"- **Documentos indexados no PostgreSQL:** **{coverage.get('indexed_documents_count', 0)}** "
        f"({coverage.get('categories_covered_count', 0)}/{coverage.get('categories_total_count', 8)} categorias `doc_type`)",
        "",
        "| Versão Prompt | Faithfulness (RAGAS) | Answer Relevancy | Source Recall@4 | Precisão Citação de Fontes | Abstenção (Sem Resposta) | Latência Média (ms) | Tokens (In/Out) | Custo Total (USD) |",
        "| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |",
    ]

    for summary in report.get("prompt_summaries", []):
        ragas = summary.get("ragas") or {}
        faith = f"{ragas['faithfulness']:.2%}" if "faithfulness" in ragas else "N/A"
        rel = f"{ragas['answer_relevancy']:.2%}" if "answer_relevancy" in ragas else "N/A"
        tokens_str = f"{summary['total_prompt_tokens']}/{summary['total_completion_tokens']}"
        lines.append(
            f"| `{summary['prompt_version']}` | {faith} | {rel} | "
            f"{summary['source_recall_at_4']:.2%} | {summary['source_citation_precision']:.2%} | "
            f"{summary['abstention_rate']:.2%} | {summary['avg_latency_ms']:.1f} | "
            f"{tokens_str} | ${summary['total_estimated_cost_usd']:.6f} |"
        )

    missing = coverage.get("missing_categories") or []
    if missing:
        lines.extend(
            [
                "",
                f"> **Categorias `doc_type` ainda sem PDFs indexados no banco:** {', '.join(f'`{c}`' for c in missing)}",
            ]
        )

    return "\n".join(lines) + "\n"


def run_evaluation(
    prompt_versions: Sequence[str] = ("v1", "v2"),
    dataset_path: Optional[str] = None,
    limit: Optional[int] = None,
    skip_ragas: bool = False,
) -> Dict[str, Any]:
    resolved_path = resolve_dataset_path(dataset_path)
    if not resolved_path.exists():
        raise FileNotFoundError(f"Dataset não encontrado em {resolved_path}")

    for pv in prompt_versions:
        if pv not in PROMPT_VERSIONS:
            raise ValueError(f"Prompt desconhecido '{pv}'. Disponíveis: {sorted(PROMPT_VERSIONS)}")

    with open(resolved_path, "r", encoding="utf-8") as f:
        dataset_items = json.load(f)

    if limit is not None:
        dataset_items = dataset_items[:limit]

    if not settings.GOOGLE_API_KEY:
        raise RuntimeError(
            "GOOGLE_API_KEY não configurada no .env. Configure a chave antes de rodar evals."
        )

    coverage = inspect_corpus_coverage()
    print(
        f"Corpus indexado: {coverage['indexed_documents_count']} documentos "
        f"({coverage['categories_covered_count']}/{coverage['categories_total_count']} categorias doc_type)."
    )

    prompt_summaries: List[Dict[str, Any]] = []
    details_by_prompt: Dict[str, List[Dict[str, Any]]] = {}

    for pv in prompt_versions:
        print(f"\n=== Executando {len(dataset_items)} perguntas com prompt '{pv}' ({settings.GEMINI_MODEL}) ===")
        predictions = asyncio.run(_collect_predictions(dataset_items, prompt_version=pv))

        ragas_summary: Dict[str, Any] = {}
        if not skip_ragas:
            print(f"Calculando métricas RAGAS (faithfulness e answer_relevancy) para '{pv}'...")
            ragas_summary = _compute_ragas_metrics(predictions)

        summary = summarize_prompt_run(pv, predictions, ragas_summary)
        prompt_summaries.append(summary)
        details_by_prompt[pv] = predictions

    primary_summary = prompt_summaries[-1] if prompt_summaries else {}
    report: Dict[str, Any] = {
        "model": settings.GEMINI_MODEL,
        "embedding_model": settings.EMBEDDING_MODEL,
        "embedding_dim": settings.EMBEDDING_DIM,
        "dataset_path": str(resolved_path.relative_to(EVALS_DIR.parent))
        if resolved_path.is_relative_to(EVALS_DIR.parent)
        else str(resolved_path),
        "total_questions": len(dataset_items),
        "corpus_coverage": coverage,
        "prompt_summaries": prompt_summaries,
        "source_recall_at_4": primary_summary.get("source_recall_at_4", 0.0),
        "source_citation_precision": primary_summary.get("source_citation_precision", 0.0),
        "abstention_rate": primary_summary.get("abstention_rate", 0.0),
        "avg_latency_ms": primary_summary.get("avg_latency_ms", 0.0),
        "ragas": primary_summary.get("ragas", {}),
        "details_by_prompt": details_by_prompt,
    }

    os.makedirs(RESULTS_DIR, exist_ok=True)
    out_json = RESULTS_DIR / "latest_report.json"
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    out_md = RESULTS_DIR / "prompt_comparison.md"
    comparison_md = render_comparison_markdown(report)
    with open(out_md, "w", encoding="utf-8") as f:
        f.write(comparison_md)

    print("\n" + comparison_md)
    print(f"Relatório JSON salvo em : {out_json}")
    print(f"Tabela MD salva em      : {out_md}")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Executa suíte de Evals comparativa (v1 vs v2) do PublicGov-RAG."
    )
    parser.add_argument(
        "--dataset",
        type=str,
        default=None,
        help="Caminho do dataset JSON (padrão: evals/golden_dataset.json).",
    )
    parser.add_argument(
        "--prompts",
        nargs="+",
        default=["v1", "v2"],
        help="Versões de prompt a comparar (ex.: --prompts v1 v2).",
    )
    parser.add_argument("--limit", type=int, default=None, help="Limita quantidade de perguntas.")
    parser.add_argument(
        "--skip-ragas",
        action="store_true",
        help="Executa apenas o agente e métricas de recuperação/citação/abstenção sem juiz RAGAS.",
    )
    parser.add_argument(
        "--coverage-only",
        action="store_true",
        help="Apenas inspeciona a cobertura das 8 categorias doc_type no banco.",
    )
    args = parser.parse_args()

    if args.coverage_only:
        coverage = inspect_corpus_coverage()
        print(json.dumps(coverage, ensure_ascii=False, indent=2))
        return

    run_evaluation(
        prompt_versions=args.prompts,
        dataset_path=args.dataset,
        limit=args.limit,
        skip_ragas=args.skip_ragas,
    )


if __name__ == "__main__":
    main()
