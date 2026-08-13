from pydantic import BaseModel
from typing import Optional, List

class QueryRequest(BaseModel):
    question: str
    doc_type_filter: Optional[str] = None  # ex: "Edital", "pautas", "Ouvidoria" , "Explica-camara"

class QueryResponse(BaseModel):
    question: str
    answer: str
    sources: List[str]