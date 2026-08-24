from sqlalchemy.orm import Session
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough

from app.core.config import settings
from app.db.vector_store import get_vector_store
from app.db.models import QueryLogModel

SYSTEM_PROMPT = """Você é o 'Oráculo PublicGov', um assistente especializado em legislação pública e atas da Câmara de Vereadores.
Responda à pergunta do usuário utilizando APENAS o contexto fornecido abaixo, extraído das pautas oficiais.
Se a resposta não constar nas pautas fornecidas, diga claramente que a informação não foi localizada nos registros indexados.

Contexto:
{context}

Pergunta: {question}"""

async def answer_question(question: str, doc_type_filter: str | None, db: Session) -> dict:
    vector_store = get_vector_store()
    
    search_kwargs = {"k": 4}
    if doc_type_filter:
        search_kwargs["filter"] = {"doc_type": doc_type_filter}
        
    retriever = vector_store.as_retriever(search_kwargs=search_kwargs)
    
    # Atualizado para o identificador estável mais recente do Gemini Flash
    llm = ChatGoogleGenerativeAI(
        model="gemini-3.6-flash", 
        temperature=0.1,
        google_api_key=settings.GOOGLE_API_KEY
    )
    
    prompt = ChatPromptTemplate.from_template(SYSTEM_PROMPT)
    
    def format_docs(docs):
        return "\n\n".join(doc.page_content for doc in docs)

    rag_chain = (
        {"context": retriever | format_docs, "question": RunnablePassthrough()}
        | prompt
        | llm
        | StrOutputParser()
    )
    
    answer = rag_chain.invoke(question)
    
    docs = retriever.invoke(question)
    sources = list(set([
        f"{doc.metadata.get('source_file', 'Desconhecido')}"
        for doc in docs
    ]))
    
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