from typing import List, Optional
from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    question: str
    doc_type_filter: Optional[str] = None  # ex: "Pauta_Sessao", "Lei_Municipal", "Projeto_de_Lei", "Mocao", "Ata_Sessao"


class QueryResponse(BaseModel):
    question: str
    answer: str
    sources: List[str]
    tools_used: List[str] = Field(default_factory=list)
    latency_ms: Optional[float] = None
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    estimated_cost_usd: Optional[float] = None
