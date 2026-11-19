from typing import Any, Dict, List, Optional
from fastmcp import FastMCP

from app.db.models import DocumentModel
from app.db.session import SessionLocal
from app.services.agent_service import run_legislative_agent
from app.services.retrieval_service import hybrid_retrieve_and_rerank

mcp = FastMCP(
    name="PublicGov-RAG MCP",
    instructions=(
        "Servidor MCP oficial do PublicGov-RAG para consulta de legislação municipal, "
        "projetos de lei, pautas, atas e moções da Câmara de Vereadores de Santana do Livramento (RS)."
    ),
)


@mcp.tool()
def consultar_legislacao_municipal(
    consulta: str,
    top_k: int = 4,
) -> List[Dict[str, Any]]:
    """Busca trechos em Leis Municipais, Projetos de Lei, Regimento Interno e Pareceres via busca híbrida + reranking."""
    target_types = ["Lei_Municipal", "Projeto_de_Lei", "Regimento_e_LOM", "Parecer_Comissao"]
    docs = hybrid_retrieve_and_rerank(query=consulta, doc_types=target_types, top_n=top_k)
    if not docs:
        docs = hybrid_retrieve_and_rerank(query=consulta, top_n=top_k)

    return [
        {
            "source_file": doc.metadata.get("source_file", "Desconhecido"),
            "doc_type": doc.metadata.get("doc_type", "Desconhecido"),
            "page": doc.metadata.get("page"),
            "rerank_score": doc.metadata.get("rerank_score"),
            "content": doc.page_content,
        }
        for doc in docs
    ]


@mcp.tool()
def consultar_pautas_e_votacoes(
    consulta: str,
    top_k: int = 4,
) -> List[Dict[str, Any]]:
    """Busca trechos em Pautas de Sessões, Atas de Votação, Moções e Requerimentos via busca híbrida + reranking."""
    target_types = [
        "Pauta_Sessao",
        "Pauta_Legislativa",
        "Ata_Sessao",
        "Mocao",
        "Requerimento_Legislativo",
    ]
    docs = hybrid_retrieve_and_rerank(query=consulta, doc_types=target_types, top_n=top_k)
    if not docs:
        docs = hybrid_retrieve_and_rerank(query=consulta, top_n=top_k)

    return [
        {
            "source_file": doc.metadata.get("source_file", "Desconhecido"),
            "doc_type": doc.metadata.get("doc_type", "Desconhecido"),
            "page": doc.metadata.get("page"),
            "rerank_score": doc.metadata.get("rerank_score"),
            "content": doc.page_content,
        }
        for doc in docs
    ]


@mcp.tool()
def listar_documentos_camara() -> List[Dict[str, Any]]:
    """Lista todos os documentos legislativos PDF atualmente indexados no PostgreSQL."""
    db = SessionLocal()
    try:
        records = db.query(DocumentModel).order_by(DocumentModel.uploaded_at.desc()).all()
        return [
            {
                "id": r.id,
                "filename": r.filename,
                "doc_type": r.doc_type,
                "chunks_count": r.chunks_count,
                "uploaded_at": r.uploaded_at.isoformat() if r.uploaded_at else None,
            }
            for r in records
        ]
    finally:
        db.close()


@mcp.tool()
async def perguntar_oraculo_legislativo(
    pergunta: str,
    doc_type_filter: Optional[str] = None,
) -> Dict[str, Any]:
    """Executa o agente LangGraph completo (com tool calling e síntese fundamentada) sobre o acervo legislativo."""
    db = SessionLocal()
    try:
        result = await run_legislative_agent(
            question=pergunta,
            doc_type_filter=doc_type_filter,
            db=db,
        )
        return {
            "question": result["question"],
            "answer": result["answer"],
            "sources": result["sources"],
            "tools_used": result["tools_used"],
        }
    finally:
        db.close()


if __name__ == "__main__":
    mcp.run()
