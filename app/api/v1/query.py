from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.api.deps import get_db
from app.schemas.query import QueryRequest, QueryResponse
from app.services.rag_service import answer_question

router = APIRouter()

@router.post("/ask", response_model=QueryResponse)
async def ask_oracle(
    request: QueryRequest,
    db: Session = Depends(get_db)
):
    result = await answer_question(
        question=request.question,
        doc_type_filter=request.doc_type_filter,
        db=db
    )
    return result