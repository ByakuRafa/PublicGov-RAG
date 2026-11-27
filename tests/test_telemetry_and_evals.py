import asyncio
import json
import os
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

for _opt_mod, _attrs in (
    ("flashrank", {"Ranker": object, "RerankRequest": object}),
    ("rank_bm25", {"BM25Okapi": object}),
    ("langchain_postgres", {"PGVector": object}),
):
    if _opt_mod not in sys.modules:
        try:
            __import__(_opt_mod)
        except ImportError:
            _stub = types.ModuleType(_opt_mod)
            for _k, _v in _attrs.items():
                setattr(_stub, _k, _v)
            sys.modules[_opt_mod] = _stub

from langchain_core.messages import AIMessage, HumanMessage
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker

from app.api.v1.query import get_query_metrics
from app.core.constants import DOC_TYPES
from app.core.telemetry import estimate_llm_cost_usd, extract_token_usage
from app.db.models import Base, DocumentModel, QueryLogModel, ensure_query_logs_schema
from app.services.agent_service import (
    PROMPT_VERSIONS,
    _build_agent_graph,
    _extract_cited_sources,
    get_system_prompt,
    run_legislative_agent,
)
from app.services.rag_service import answer_question
from app.schemas.query import QueryRequest
from batch_upload import descobrir_arquivos_para_upload
from evals.run_eval import (
    GOLDEN_DATASET_PATH,
    inspect_corpus_coverage,
    is_abstention_response,
    render_comparison_markdown,
    score_prediction,
    summarize_prompt_run,
)
from sapl_downloader import LookupCatalog, classify_materia


class TelemetryAndCostTests(unittest.TestCase):
    def test_extract_token_usage_from_usage_and_response_metadata(self):
        messages = [
            HumanMessage(content="Qual o valor?"),
            AIMessage(
                content="",
                usage_metadata={"input_tokens": 120, "output_tokens": 30, "total_tokens": 150},
            ),
            AIMessage(
                content="Resposta final",
                response_metadata={
                    "usage_metadata": {
                        "prompt_token_count": 200,
                        "candidates_token_count": 50,
                    }
                },
            ),
        ]
        prompt_tokens, completion_tokens = extract_token_usage(messages)
        self.assertEqual(prompt_tokens, 320)
        self.assertEqual(completion_tokens, 80)

    def test_estimate_llm_cost_usd_gemini_flash(self):
        cost = estimate_llm_cost_usd("gemini-2.5-flash", prompt_tokens=1_000_000, completion_tokens=500_000)
        # 0.15 + (0.5 * 0.60) = 0.45
        self.assertAlmostEqual(cost, 0.45, places=6)

        cost_lite = estimate_llm_cost_usd("gemini-3.5-flash-lite", prompt_tokens=2322, completion_tokens=99)
        self.assertGreater(cost_lite, 0.0)
        self.assertAlmostEqual(cost_lite, 0.000272, places=6)

    def test_schema_migration_adds_telemetry_columns(self):
        engine = create_engine("sqlite:///:memory:")
        with engine.begin() as conn:
            conn.execute(
                text(
                    """
                    CREATE TABLE query_logs (
                        id INTEGER PRIMARY KEY,
                        question TEXT NOT NULL,
                        answer TEXT NOT NULL,
                        doc_type_filter VARCHAR(50),
                        tools_used VARCHAR(255),
                        created_at DATETIME
                    )
                    """
                )
            )

        ensure_query_logs_schema(engine)
        cols = {c["name"] for c in inspect(engine).get_columns("query_logs")}
        self.assertTrue(
            {"latency_ms", "prompt_tokens", "completion_tokens", "estimated_cost_usd"}.issubset(cols)
        )

    def test_rag_service_persists_telemetry_and_metrics_endpoint(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=engine)
        SessionLocal = sessionmaker(bind=engine)
        db = SessionLocal()

        mock_result = {
            "question": "Qual o teto do MEI citado na Moção?",
            "answer": "R$ 81 mil conforme 4429.pdf.",
            "sources": ["4429.pdf"],
            "cited_sources": ["4429.pdf"],
            "tools_used": ["consultar_pautas_e_votacoes"],
            "contexts": ["trecho"],
            "latency_ms": 412.5,
            "prompt_tokens": 350,
            "completion_tokens": 75,
            "estimated_cost_usd": 0.000098,
        }

        try:
            with patch(
                "app.services.rag_service.run_legislative_agent",
                new=AsyncMock(return_value=mock_result),
            ):
                response = asyncio.run(
                    answer_question(
                        question=mock_result["question"],
                        doc_type_filter="Mocao",
                        db=db,
                    )
                )

            self.assertEqual(response["latency_ms"], 412.5)
            self.assertEqual(response["prompt_tokens"], 350)
            self.assertEqual(response["completion_tokens"], 75)
            self.assertEqual(response["estimated_cost_usd"], 0.000098)

            log = db.query(QueryLogModel).one()
            self.assertEqual(log.latency_ms, 412.5)
            self.assertEqual(log.prompt_tokens, 350)
            self.assertEqual(log.completion_tokens, 75)
            self.assertEqual(log.estimated_cost_usd, 0.000098)

            metrics = get_query_metrics(db=db)
            self.assertEqual(metrics["total_queries"], 1)
            self.assertEqual(metrics["avg_latency_ms"], 412.5)
            self.assertEqual(metrics["total_prompt_tokens"], 350)
            self.assertEqual(metrics["total_completion_tokens"], 75)
            self.assertEqual(metrics["total_estimated_cost_usd"], 0.000098)
        finally:
            db.close()


class GoldenDatasetAndEvalTests(unittest.TestCase):
    def test_doc_types_has_9_official_categories(self):
        self.assertEqual(len(DOC_TYPES), 9)
        self.assertEqual(len(set(DOC_TYPES)), 9)
        self.assertIn("Materia_Legislativa", DOC_TYPES)

    def test_query_request_sanitizes_swagger_placeholder(self):
        req1 = QueryRequest(question="Quem é Dagberto?", doc_type_filter="string")
        self.assertIsNone(req1.doc_type_filter)

        req2 = QueryRequest(question="Quem é Dagberto?", doc_type_filter="   ")
        self.assertIsNone(req2.doc_type_filter)

        req3 = QueryRequest(question="Quem é Dagberto?", doc_type_filter="null")
        self.assertIsNone(req3.doc_type_filter)

        req4 = QueryRequest(question="Quem é Dagberto?", doc_type_filter="Projeto_de_Lei")
        self.assertEqual(req4.doc_type_filter, "Projeto_de_Lei")

        req5 = QueryRequest(question="Quem é Dagberto?", doc_type_filter="Pauta_Legislativa")
        self.assertEqual(req5.doc_type_filter, "Pauta_Sessao")

    def test_prompt_versions_and_citation_extraction(self):
        self.assertIn("v1", PROMPT_VERSIONS)
        self.assertIn("v2", PROMPT_VERSIONS)
        self.assertNotEqual(get_system_prompt("v1"), get_system_prompt("v2"))
        cited = _extract_cited_sources("Conforme consta em 2758.pdf.", ["2758.pdf", "2686.pdf"])
        self.assertEqual(cited, ["2758.pdf"])

    def test_run_legislative_agent_collects_telemetry_and_cited_sources(self):
        from langchain_core.messages import ToolMessage

        fake_graph_output = {
            "messages": [
                HumanMessage(content="Qual o teto do MEI?"),
                AIMessage(
                    content="",
                    tool_calls=[{"id": "call_1", "name": "consultar_pautas_e_votacoes", "args": {"consulta": "MEI"}}],
                    usage_metadata={"input_tokens": 500, "output_tokens": 40, "total_tokens": 540},
                ),
                ToolMessage(
                    content=json.dumps(
                        {
                            "encontrados": 1,
                            "trechos": [
                                {
                                    "source_file": "4429.pdf",
                                    "doc_type": "Mocao",
                                    "page": 1,
                                    "content": "Limite do MEI fixado em R$ 81 mil.",
                                }
                            ],
                        }
                    ),
                    name="consultar_pautas_e_votacoes",
                    tool_call_id="call_1",
                ),
                AIMessage(
                    content="O limite atual do MEI citado é de R$ 81 mil, conforme 4429.pdf.",
                    usage_metadata={"input_tokens": 700, "output_tokens": 60, "total_tokens": 760},
                ),
            ]
        }

        class FakeGraph:
            def __init__(self):
                self.captured_config = None

            async def ainvoke(self, payload, config=None):
                self.captured_config = config
                return fake_graph_output

        fake_graph = FakeGraph()
        with patch("app.services.agent_service._build_agent_graph", return_value=fake_graph), patch(
            "app.services.agent_service.get_langfuse_callbacks", return_value=["cb_mock"]
        ), patch("app.services.agent_service.flush_langfuse") as mock_flush:
            res = asyncio.run(run_legislative_agent("Qual o teto do MEI?", prompt_version="v2"))

        self.assertEqual(res["prompt_version"], "v2")
        self.assertEqual(res["prompt_tokens"], 1200)
        self.assertEqual(res["completion_tokens"], 100)
        self.assertGreater(res["estimated_cost_usd"], 0.0)
        self.assertGreaterEqual(res["latency_ms"], 0.0)
        self.assertEqual(res["sources"], ["4429.pdf"])
        self.assertEqual(res["cited_sources"], ["4429.pdf"])
        self.assertEqual(fake_graph.captured_config["callbacks"], ["cb_mock"])
        self.assertEqual(fake_graph.captured_config["metadata"]["prompt_version"], "v2")
        mock_flush.assert_called_once()

    def test_golden_dataset_structure_and_abstention_cases(self):
        self.assertTrue(GOLDEN_DATASET_PATH.exists())
        items = json.loads(GOLDEN_DATASET_PATH.read_text(encoding="utf-8"))
        self.assertGreaterEqual(len(items), 25)
        self.assertLessEqual(len(items), 30)

        ids = [i["id"] for i in items]
        self.assertEqual(len(ids), len(set(ids)))

        unanswerable = [i for i in items if not i.get("answerable", True)]
        self.assertEqual(len(unanswerable), 5)
        for item in unanswerable:
            self.assertIsNone(item["expected_source"])

    def test_eval_scoring_and_markdown_comparison(self):
        ans_item = {
            "id": "q01",
            "expected_source": "2686.pdf",
            "answerable": True,
            "in_scope": True,
        }
        unans_item = {
            "id": "q26",
            "expected_source": None,
            "answerable": False,
            "in_scope": False,
        }

        s_v1 = score_prediction(
            ans_item,
            {"answer": "O valor é R$ 384.205,00.", "predicted_sources": ["2686.pdf"], "cited_sources": []},
        )
        self.assertTrue(s_v1["source_hit"])
        self.assertEqual(s_v1["citation_precision"], 0.0)

        s_v2 = score_prediction(
            ans_item,
            {
                "answer": "O valor é R$ 384.205,00 (fonte: 2686.pdf).",
                "predicted_sources": ["2686.pdf"],
                "cited_sources": ["2686.pdf"],
            },
        )
        self.assertTrue(s_v2["citation_hit"])
        self.assertEqual(s_v2["citation_precision"], 1.0)

        s_abst = score_prediction(
            unans_item,
            {
                "answer": "Essa informação não foi localizada nos registros indexados e está fora do escopo.",
                "predicted_sources": ["2686.pdf"],
                "cited_sources": [],
            },
        )
        self.assertTrue(s_abst["abstention_hit"])
        self.assertEqual(s_abst["citation_precision"], 1.0)

        summary_v2 = summarize_prompt_run(
            "v2",
            [
                {
                    **s_v2,
                    "latency_ms": 500.0,
                    "prompt_tokens": 200,
                    "completion_tokens": 50,
                    "estimated_cost_usd": 0.00006,
                },
                {
                    **s_abst,
                    "latency_ms": 300.0,
                    "prompt_tokens": 150,
                    "completion_tokens": 30,
                    "estimated_cost_usd": 0.00004,
                },
            ],
            {"faithfulness": 0.96, "answer_relevancy": 0.91},
        )
        md = render_comparison_markdown(
            {
                "dataset_path": "evals/golden_dataset.json",
                "total_questions": 2,
                "model": "gemini-2.5-flash",
                "embedding_model": "MiniLM",
                "corpus_coverage": {
                    "indexed_documents_count": 8,
                    "categories_covered_count": 8,
                    "categories_total_count": 8,
                    "missing_categories": [],
                },
                "prompt_summaries": [summary_v2],
            }
        )
        self.assertIn("96.00%", md)
        self.assertIn("100.00%", md)

    def test_inspect_corpus_coverage_and_batch_discovery(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=engine)
        SessionLocal = sessionmaker(bind=engine)
        db = SessionLocal()
        try:
            db.add(DocumentModel(filename="ata1.pdf", doc_type="Ata_Sessao", chunks_count=5))
            db.add(DocumentModel(filename="lei1.pdf", doc_type="Lei_Municipal", chunks_count=12))
            db.commit()

            cov = inspect_corpus_coverage(db=db)
            self.assertEqual(cov["indexed_documents_count"], 2)
            self.assertEqual(cov["categories_covered_count"], 2)
            self.assertEqual(cov["categories_total_count"], 9)
            self.assertIn("Ata_Sessao", cov["covered_categories"])
            self.assertIn("Parecer_Comissao", cov["missing_categories"])
        finally:
            db.close()

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "root_doc.pdf").write_bytes(b"%PDF-1.4")
            (root / "Ata_Sessao").mkdir()
            (root / "Ata_Sessao" / "ata.pdf").write_bytes(b"%PDF-1.4")
            discovered = descobrir_arquivos_para_upload(root, "Pauta_Sessao")
            self.assertEqual(
                [(p.name, dt) for p, dt in discovered],
                [("root_doc.pdf", "Pauta_Sessao"), ("ata.pdf", "Ata_Sessao")],
            )

    def test_agent_graph_stops_gracefully_after_max_tool_rounds(self):
        class StubBoundLLM:
            def __init__(self, parent):
                self.parent = parent

            def invoke(self, messages):
                self.parent.bound_calls += 1
                return AIMessage(
                    content="",
                    tool_calls=[
                        {
                            "id": f"call_{self.parent.bound_calls}",
                            "name": "pedir_esclarecimento_ao_cidadao",
                            "args": {"motivo": "busca", "sugestao_perguntas": ["detalhe?"]},
                        }
                    ],
                )

        class StubLLM:
            def __init__(self, *args, **kwargs):
                self.bound_calls = 0
                self.unbound_calls = 0

            def bind_tools(self, tools):
                return StubBoundLLM(self)

            def invoke(self, messages):
                self.unbound_calls += 1
                return AIMessage(content="Não foi possível localizar a informação nos registros indexados.")

        stub_llm = StubLLM()
        with patch("app.services.agent_service.ChatGoogleGenerativeAI", return_value=stub_llm):
            graph = _build_agent_graph(prompt_version="v1")
            result = asyncio.run(
                graph.ainvoke(
                    {"messages": [HumanMessage(content="Pergunta sem fim")]},
                    config={"recursion_limit": 8},
                )
            )

        self.assertEqual(stub_llm.bound_calls, 3)
        self.assertEqual(stub_llm.unbound_calls, 1)
        self.assertIn("Não foi possível localizar", result["messages"][-1].content)

    def test_sapl_classify_materia_and_abstention_patterns(self):
        catalog = LookupCatalog(
            tipos_materia={
                34: {"id": 34, "sigla": "SUB", "descricao": "Substitutivo"},
                24: {"id": 24, "sigla": "RM", "descricao": "Resolução de Mesa"},
                28: {"id": 28, "sigla": "VC", "descricao": "Voto de Congratulação"},
                29: {"id": 29, "sigla": "VP", "descricao": "Voto de Pesar"},
                21: {"id": 21, "sigla": "PU", "descricao": "Pedido de Urgência"},
                30: {"id": 30, "sigla": "PD", "descricao": "Pedido de Diligência"},
                41: {"id": 41, "sigla": "ARPI", "descricao": "Anexo de Resp. PI"},
                19: {"id": 19, "sigla": "OF", "descricao": "Ofícios"},
                4: {"id": 4, "sigla": "MSG", "descricao": "Mensagem"},
                12: {"id": 12, "sigla": "REC", "descricao": "Recurso"},
                25: {"id": 25, "sigla": "CONV", "descricao": "Convite"},
            },
            tipos_documento_acessorio={},
            tipos_norma={},
            tipos_sessao={},
        )
        self.assertEqual(classify_materia(34, catalog), "Projeto_de_Lei")
        self.assertEqual(classify_materia(24, catalog), "Lei_Municipal")
        self.assertEqual(classify_materia(28, catalog), "Mocao")
        self.assertEqual(classify_materia(29, catalog), "Mocao")
        self.assertEqual(classify_materia(21, catalog), "Requerimento_Legislativo")
        self.assertEqual(classify_materia(30, catalog), "Requerimento_Legislativo")
        self.assertEqual(classify_materia(41, catalog), "Requerimento_Legislativo")
        for fallback_id in (19, 4, 12, 25):
            self.assertEqual(classify_materia(fallback_id, catalog), "Materia_Legislativa")

        self.assertTrue(is_abstention_response("Não há menção sobre esse tema nos registros."))
        self.assertTrue(is_abstention_response("Trata-se de rotinas administrativas internas fora do escopo."))


if __name__ == "__main__":
    unittest.main()
