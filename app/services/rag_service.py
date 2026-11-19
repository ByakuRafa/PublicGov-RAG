from typing import Optional
from sqlalchemy.orm import Session

from app.db.models import QueryLogModel
from app.services.agent_service import run_legislative_agent


async def answer_question(
    question: str,
    doc_type_filter: Optional[str],
    db: Session,
) -> dict:
    """Executa a consulta legislativa via agente LangGraph e registra auditoria no PostgreSQL."""
    agent_result = await run_legislative_agent(
        question=question,
        doc_type_filter=doc_type_filter,
        db=db,
    )

    query_log = QueryLogModel(
        question=question,
        answer=agent_result["answer"],
        doc_type_filter=doc_type_filter,
        tools_used=",".join(agent_result["tools_used"]) if agent_result["tools_used"] else None,
    )
    db.add(query_log)
    db.commit()

    return {
        "question": agent_result["question"],
        "answer": agent_result["answer"],
        "sources": agent_result["sources"],
        "tools_used": agent_result["tools_used"],
    }
