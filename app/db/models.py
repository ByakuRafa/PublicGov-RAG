from sqlalchemy import Column, Integer, String, DateTime, Text
from sqlalchemy.orm import declarative_base
from datetime import datetime

Base = declarative_base()

class DocumentModel(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(255), nullable=False)
    doc_type = Column(String(50), nullable=False)  # tipos: Pauta_Sessao, Lei_Municipal, Projeto_de_Lei, Mocao, Ata_Sessao, etc.
    chunks_count = Column(Integer, default=0)
    uploaded_at = Column(DateTime, default=datetime.utcnow)

class QueryLogModel(Base):
    __tablename__ = "query_logs"

    id = Column(Integer, primary_key=True, index=True)
    question = Column(Text, nullable=False)
    answer = Column(Text, nullable=False)
    doc_type_filter = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
