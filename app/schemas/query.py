from typing import List, Optional
from pydantic import BaseModel, Field, field_validator

from app.core.constants import DOC_TYPES, DOC_TYPE_ALIASES


class QueryRequest(BaseModel):
    question: str = Field(
        ...,
        description="Pergunta do cidadão ou servidor público sobre a legislação e matérias da Câmara.",
        examples=["que informações relacionadas ao Dagberto Reis você tem?"],
    )
    doc_type_filter: Optional[str] = Field(
        default=None,
        description=(
            "Filtro opcional por tipo de documento legislativo. Categorias oficiais: "
            + ", ".join(DOC_TYPES)
        ),
        json_schema_extra={
            "examples": [None, "Projeto_de_Lei", "Pauta_Sessao", "Mocao"],
        },
    )

    @field_validator("doc_type_filter", mode="before")
    @classmethod
    def sanitize_doc_type_filter(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        if isinstance(v, str):
            v_clean = v.strip()
            # Swagger UI / OpenAPI frequentemente envia "string" como placeholder padrão
            if not v_clean or v_clean.lower() in ("string", "null", "none"):
                return None
            if v_clean in DOC_TYPE_ALIASES:
                return DOC_TYPE_ALIASES[v_clean]
            return v_clean
        return v


class QueryResponse(BaseModel):
    question: str
    answer: str
    sources: List[str]
    tools_used: List[str] = Field(default_factory=list)
    latency_ms: Optional[float] = None
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    estimated_cost_usd: Optional[float] = None
