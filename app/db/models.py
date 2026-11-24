from datetime import datetime, timezone
from sqlalchemy import Column, DateTime, Float, Integer, String, Text, inspect, text
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class DocumentModel(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(255), nullable=False)
    doc_type = Column(String(50), nullable=False)  # ex: Pauta_Sessao, Lei_Municipal, Projeto_de_Lei, Mocao, Ata_Sessao
    chunks_count = Column(Integer, default=0)
    uploaded_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class QueryLogModel(Base):
    __tablename__ = "query_logs"

    id = Column(Integer, primary_key=True, index=True)
    question = Column(Text, nullable=False)
    answer = Column(Text, nullable=False)
    doc_type_filter = Column(String(50), nullable=True)
    tools_used = Column(String(255), nullable=True)
    latency_ms = Column(Float, nullable=True)
    prompt_tokens = Column(Integer, nullable=True)
    completion_tokens = Column(Integer, nullable=True)
    estimated_cost_usd = Column(Float, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


def ensure_query_logs_schema(target_engine) -> None:
    """Garante colunas de telemetria em bancos existentes sem perda de dados."""
    inspector = inspect(target_engine)
    if "query_logs" not in inspector.get_table_names():
        return

    existing_columns = {col["name"] for col in inspector.get_columns("query_logs")}
    telemetry_columns = {
        "latency_ms": "DOUBLE PRECISION" if target_engine.dialect.name == "postgresql" else "FLOAT",
        "prompt_tokens": "INTEGER",
        "completion_tokens": "INTEGER",
        "estimated_cost_usd": "DOUBLE PRECISION" if target_engine.dialect.name == "postgresql" else "FLOAT",
    }

    with target_engine.begin() as conn:
        for col_name, col_type in telemetry_columns.items():
            if col_name not in existing_columns:
                conn.execute(text(f"ALTER TABLE query_logs ADD COLUMN {col_name} {col_type}"))
