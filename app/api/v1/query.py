import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.api.deps import get_db
from app.schemas.query import QueryRequest, QueryResponse
from app.services.rag_service import answer_question
from app.db.models import QueryLogModel

logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/ask", response_model=QueryResponse)
async def ask_oracle(request: QueryRequest, db: Session = Depends(get_db)):
    try:
        return await answer_question(
            question=request.question,
            doc_type_filter=request.doc_type_filter,
            db=db
        )
    except Exception as exc:
        logger.exception("Erro ao processar consulta legislativa no Oráculo: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Falha ao processar consulta: {str(exc)}",
        )

@router.get("/history")
def get_query_history(limit: int = 10, db: Session = Depends(get_db)):
    """Retorna o histórico de auditoria das perguntas feitas ao sistema."""
    logs = db.query(QueryLogModel).order_by(QueryLogModel.created_at.desc()).limit(limit).all()
    return logs


@router.get("/metrics")
def get_query_metrics(db: Session = Depends(get_db)):
    """Retorna métricas agregadas de telemetria (latência, tokens e custo estimado)."""
    row = db.query(
        func.count(QueryLogModel.id).label("total_queries"),
        func.avg(QueryLogModel.latency_ms).label("avg_latency_ms"),
        func.sum(QueryLogModel.prompt_tokens).label("total_prompt_tokens"),
        func.sum(QueryLogModel.completion_tokens).label("total_completion_tokens"),
        func.sum(QueryLogModel.estimated_cost_usd).label("total_estimated_cost_usd"),
    ).one()
    return {
        "total_queries": int(row.total_queries or 0),
        "avg_latency_ms": round(float(row.avg_latency_ms), 2) if row.avg_latency_ms is not None else 0.0,
        "total_prompt_tokens": int(row.total_prompt_tokens or 0),
        "total_completion_tokens": int(row.total_completion_tokens or 0),
        "total_estimated_cost_usd": round(float(row.total_estimated_cost_usd or 0.0), 6),
    }