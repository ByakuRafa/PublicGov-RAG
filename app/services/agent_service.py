import json
import re
import time
from contextvars import ContextVar
from typing import Annotated, Any, Dict, List, Optional, TypedDict

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import tool
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.observability import flush_langfuse, get_langfuse_callbacks
from app.core.telemetry import estimate_llm_cost_usd, extract_token_usage
from app.db.models import DocumentModel
from app.services.retrieval_service import hybrid_retrieve_and_rerank

# ContextVars de leitura por requisição (sessão SQL e filtro explícito)
_db_session_ctx: ContextVar[Optional[Session]] = ContextVar("_db_session_ctx", default=None)
_doc_filter_ctx: ContextVar[Optional[str]] = ContextVar("_doc_filter_ctx", default=None)


AGENT_PROMPT_V1 = """Você é o 'Oráculo PublicGov', assistente da Câmara Municipal de Vereadores de Santana do Livramento (RS).
Use as ferramentas disponíveis para pesquisar os documentos legislativos da Câmara e responder à pergunta do usuário de forma clara e útil."""

AGENT_PROMPT_V2 = """Você é o 'Oráculo PublicGov', agente especialista na legislação municipal, proposições, pautas e atas da Câmara Municipal de Vereadores de Santana do Livramento (RS).

Regras de atuação e roteamento:
1. Para perguntas sobre leis vigentes, projetos de lei (PLO/PLC), pareceres, Lei Orgânica ou Regimento Interno (Resolução nº 1.252/2016), use a ferramenta `consultar_legislacao_municipal`.
2. Para perguntas sobre pautas de sessão, atas de votação, moções (ex.: Moção de Apoio) ou requerimentos legislativos, use a ferramenta `consultar_pautas_e_votacoes`.
3. Para saber quais arquivos constam na base, use `listar_documentos_indexados`.
4. Se a pergunta do cidadão for muito vaga ou ambígua (por exemplo, "me fale sobre o projeto" sem indicar qual assunto, número ou tipo), acione `pedir_esclarecimento_ao_cidadao` pedindo detalhes de forma educada.
5. Escopo estrito e abstenção obrigatória: se a pergunta tratar de rotinas administrativas internas (diárias, férias, folha de pagamento), atos do Executivo alheios à Câmara (multas de trânsito, concursos da Prefeitura) ou decisões judiciais externas, ou se a informação solicitada NÃO constar nos trechos retornados pelas ferramentas, informe explicitamente que a informação não foi localizada nos registros indexados e NÃO especule.
6. Fidelidade e citação: responda utilizando APENAS os trechos recuperados pelas ferramentas. Nunca invente números, valores, datas, artigos ou nomes. Sempre que responder com base em um documento, cite explicitamente o arquivo fonte (`source_file`, ex.: `2758.pdf`). Caso não haja evidência suficiente, NÃO cite arquivos como fonte."""

AGENT_SYSTEM_PROMPT = AGENT_PROMPT_V2

PROMPT_VERSIONS: Dict[str, str] = {
    "v1": AGENT_PROMPT_V1,
    "v2": AGENT_PROMPT_V2,
}


def get_system_prompt(prompt_version: str = "v2") -> str:
    """Retorna o prompt de sistema correspondente à versão solicitada (v1 ou v2)."""
    if prompt_version not in PROMPT_VERSIONS:
        raise ValueError(
            f"Versão de prompt inválida: '{prompt_version}'. Opções: {sorted(PROMPT_VERSIONS.keys())}"
        )
    return PROMPT_VERSIONS[prompt_version]


class AgentState(TypedDict):
    messages: Annotated[List[BaseMessage], add_messages]


def _format_retrieval_payload(docs, fallback_note: str = "") -> str:
    if not docs:
        return json.dumps(
            {
                "encontrados": 0,
                "mensagem": "Nenhum trecho relevante foi localizado nos documentos indexados.",
                "trechos": [],
            },
            ensure_ascii=False,
        )

    payload_chunks = []
    for doc in docs:
        entry = {
            "source_file": doc.metadata.get("source_file", "Desconhecido"),
            "doc_type": doc.metadata.get("doc_type", "Desconhecido"),
            "page": doc.metadata.get("page"),
            "content": doc.page_content,
        }
        payload_chunks.append(entry)

    result = {"encontrados": len(payload_chunks), "trechos": payload_chunks}
    if fallback_note:
        result["observacao"] = fallback_note
    return json.dumps(result, ensure_ascii=False)


@tool
def consultar_legislacao_municipal(consulta: str) -> str:
    """Busca trechos em Leis Municipais, Projetos de Lei (PLO/PLC), Regimento Interno e Pareceres de Comissões."""
    explicit_filter = _doc_filter_ctx.get()
    if explicit_filter:
        docs = hybrid_retrieve_and_rerank(query=consulta, doc_type_filter=explicit_filter)
        return _format_retrieval_payload(docs)

    target_types = ["Lei_Municipal", "Projeto_de_Lei", "Regimento_e_LOM", "Parecer_Comissao"]
    docs = hybrid_retrieve_and_rerank(query=consulta, doc_types=target_types)
    if docs:
        return _format_retrieval_payload(docs)

    # Fallback para acervo geral caso documentos tenham sido indexados sob categoria ampla (ex.: Pauta_Sessao)
    docs = hybrid_retrieve_and_rerank(query=consulta)
    return _format_retrieval_payload(
        docs,
        fallback_note="Busca ampliada para todo o acervo legislativo indexado.",
    )


@tool
def consultar_pautas_e_votacoes(consulta: str) -> str:
    """Busca trechos em Pautas de Sessões Plenárias, Atas de Votação, Moções e Requerimentos Legislativos."""
    explicit_filter = _doc_filter_ctx.get()
    if explicit_filter:
        docs = hybrid_retrieve_and_rerank(query=consulta, doc_type_filter=explicit_filter)
        return _format_retrieval_payload(docs)

    target_types = [
        "Pauta_Sessao",
        "Pauta_Legislativa",
        "Ata_Sessao",
        "Mocao",
        "Requerimento_Legislativo",
    ]
    docs = hybrid_retrieve_and_rerank(query=consulta, doc_types=target_types)
    if docs:
        return _format_retrieval_payload(docs)

    docs = hybrid_retrieve_and_rerank(query=consulta)
    return _format_retrieval_payload(
        docs,
        fallback_note="Busca ampliada para todo o acervo legislativo indexado.",
    )


@tool
def listar_documentos_indexados() -> str:
    """Lista os documentos PDF oficialmente indexados no catálogo da Câmara Municipal."""
    db = _db_session_ctx.get()
    if db is None:
        return json.dumps({"documentos": [], "erro": "Sessão de banco indisponível."}, ensure_ascii=False)

    records = db.query(DocumentModel).order_by(DocumentModel.uploaded_at.desc()).all()
    items = [
        {
            "filename": r.filename,
            "doc_type": r.doc_type,
            "chunks_count": r.chunks_count,
        }
        for r in records
    ]
    return json.dumps({"total": len(items), "documentos": items}, ensure_ascii=False)


@tool
def pedir_esclarecimento_ao_cidadao(motivo: str, sugestao_perguntas: List[str]) -> str:
    """Acionada quando a pergunta do cidadão é ambígua ou precisa de mais contexto para uma busca precisa."""
    return json.dumps(
        {
            "acao": "esclarecimento",
            "motivo": motivo,
            "sugestoes": sugestao_perguntas,
        },
        ensure_ascii=False,
    )


TOOLS = [
    consultar_legislacao_municipal,
    consultar_pautas_e_votacoes,
    listar_documentos_indexados,
    pedir_esclarecimento_ao_cidadao,
]


def _build_agent_graph(prompt_version: str = "v2"):
    system_prompt = get_system_prompt(prompt_version)
    llm = ChatGoogleGenerativeAI(
        model=settings.GEMINI_MODEL,
        temperature=0.1,
        google_api_key=settings.GOOGLE_API_KEY,
    ).bind_tools(TOOLS)

    def agent_node(state: AgentState) -> Dict[str, Any]:
        messages = [SystemMessage(content=system_prompt)] + list(state["messages"])
        response = llm.invoke(messages)
        return {"messages": [response]}

    def route_after_agent(state: AgentState) -> str:
        last_message = state["messages"][-1]
        if isinstance(last_message, AIMessage) and getattr(last_message, "tool_calls", None):
            return "tools"
        return END

    tool_node = ToolNode(TOOLS)

    graph = StateGraph(AgentState)
    graph.add_node("agent", agent_node)
    graph.add_node("tools", tool_node)
    graph.add_edge(START, "agent")
    graph.add_conditional_edges("agent", route_after_agent, {"tools": "tools", END: END})
    graph.add_edge("tools", "agent")
    return graph.compile()


def _extract_text_content(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                parts.append(block.get("text", ""))
            elif isinstance(block, str):
                parts.append(block)
        return "\n".join(p for p in parts if p).strip()
    return str(content)


def _extract_cited_sources(answer_text: str, retrieved_sources: List[str]) -> List[str]:
    """Identifica quais arquivos fonte recuperados foram citados explicitamente na resposta."""
    if not answer_text:
        return []
    cited = [src for src in retrieved_sources if src in answer_text]
    if cited:
        return cited
    return sorted(set(re.findall(r"\b[\w.-]+\.pdf\b", answer_text, flags=re.IGNORECASE)))


async def run_legislative_agent(
    question: str,
    doc_type_filter: Optional[str] = None,
    db: Optional[Session] = None,
    prompt_version: str = "v2",
) -> Dict[str, Any]:
    """Executa o agente LangGraph com busca híbrida, reranking, telemetria e tracing Langfuse."""
    token_db = _db_session_ctx.set(db)
    token_filter = _doc_filter_ctx.set(doc_type_filter)

    try:
        user_prompt = question
        if doc_type_filter:
            user_prompt = f"[Filtro de tipo de documento ativo: {doc_type_filter}]\n{question}"

        graph = _build_agent_graph(prompt_version=prompt_version)
        callbacks = get_langfuse_callbacks()
        invoke_config: Dict[str, Any] = {
            "recursion_limit": 8,
            "metadata": {
                "prompt_version": prompt_version,
                "doc_type_filter": doc_type_filter,
                "llm_model": settings.GEMINI_MODEL,
            },
            "tags": ["publicgov-rag", f"prompt:{prompt_version}"],
        }
        if callbacks:
            invoke_config["callbacks"] = callbacks

        started = time.perf_counter()
        result = await graph.ainvoke(
            {"messages": [HumanMessage(content=user_prompt)]},
            config=invoke_config,
        )
        latency_ms = round((time.perf_counter() - started) * 1000.0, 2)

        final_answer = ""
        tools_used: List[str] = []
        captured_chunks: List[Dict[str, Any]] = []
        for msg in result["messages"]:
            if isinstance(msg, ToolMessage):
                if msg.name and msg.name not in tools_used:
                    tools_used.append(msg.name)
                try:
                    payload = json.loads(_extract_text_content(msg.content))
                    if isinstance(payload, dict) and isinstance(payload.get("trechos"), list):
                        captured_chunks.extend(payload["trechos"])
                except (json.JSONDecodeError, TypeError):
                    pass
            elif isinstance(msg, AIMessage) and not getattr(msg, "tool_calls", None):
                final_answer = _extract_text_content(msg.content)

        prompt_tokens, completion_tokens = extract_token_usage(result["messages"])
        estimated_cost_usd = estimate_llm_cost_usd(
            model_name=settings.GEMINI_MODEL,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
        )

        sources = sorted(
            {chunk["source_file"] for chunk in captured_chunks if chunk.get("source_file")}
        )
        answer_text = final_answer or "Não foi possível gerar uma resposta fundamentada."
        cited_sources = _extract_cited_sources(answer_text, sources)
        contexts = [chunk["content"] for chunk in captured_chunks if chunk.get("content")]

        return {
            "question": question,
            "answer": answer_text,
            "sources": sources,
            "cited_sources": cited_sources,
            "tools_used": tools_used,
            "contexts": contexts,
            "prompt_version": prompt_version,
            "latency_ms": latency_ms,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "estimated_cost_usd": estimated_cost_usd,
        }
    finally:
        flush_langfuse()
        _db_session_ctx.reset(token_db)
        _doc_filter_ctx.reset(token_filter)
