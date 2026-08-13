from sqlalchemy.orm import Session
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough

from app.core.config import settings
from app.db.vector_store import get_vector_store
from app.db.models import QueryLogModel

SYSTEM_PROMPT = """Você é o 'Oráculo PublicGov', um assistente virtual especializado em legislação pública, editais de licitação e demandas de ouvidoria.
Responda à pergunta do usuário utilizando APENAS o contexto de documentos fornecido abaixo.
Se a resposta não constar no contexto, informe explicitamente que os documentos oficiais disponíveis não contêm essa informação.

Contexto:
{context}

Pergunta: {question}"""

async def answer_question(question: str, doc_type_filter: str | None, db: Session) -> dict:
    vector_store = get_vector_store()
    
    search_kwargs = {"k": 4}
    if doc_type_filter:
        search_kwargs["filter"] = {"doc_type": doc_type_filter}
        
    retriever = vector_store.as_retriever(search_kwargs=search_kwargs)
    
    llm = ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0.1,
        openai_api_key=settings.OPENAI_API_KEY
    )
    
    prompt = ChatPromptTemplate.from_template(SYSTEM_PROMPT)
    
    # arquitetura LCEL
    def format_docs(docs):
        return "\n\n".join(doc.page_content for doc in docs)

    rag_chain = (
        {"context": retriever | format_docs, "question": RunnablePassthrough()}
        | prompt
        | llm
        | StrOutputParser()
    )
    
    # executa a chain
    answer = rag_chain.invoke(question)
    
    # recupera os documentos para listar as fontes
    docs = retriever.invoke(question)
    sources = list(set([
        f"{doc.metadata.get('source_file', 'Desconhecido')}"
        for doc in docs
    ]))
    
    # grava no banco de dados relacional (SQLAlchemy)
    query_log = QueryLogModel(
        question=question,
        answer=answer,
        doc_type_filter=doc_type_filter
    )
    db.add(query_log)
    db.commit()
    
    return {
        "question": question,
        "answer": answer,
        "sources": sources
    }