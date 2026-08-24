from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.api.deps import get_db
from app.schemas.query import QueryRequest, QueryResponse
from app.services.rag_service import answer_question
from app.db.models import QueryLogModel

router = APIRouter()

@router.post("/ask", response_model=QueryResponse)
async def ask_oracle(request: QueryRequest, db: Session = Depends(get_db)):
    return await answer_question(
        question=request.question,
        doc_type_filter=request.doc_type_filter,
        db=db
    )

@router.get("/history")
def get_query_history(limit: int = 10, db: Session = Depends(get_db)):
    """Retorna o histórico de auditoria das perguntas feitas ao sistema."""
    logs = db.query(QueryLogModel).order_by(QueryLogModel.created_at.desc()).limit(limit).all()
    return logs