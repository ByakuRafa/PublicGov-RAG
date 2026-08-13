from sqlalchemy.orm import Session
from langchain_openai import ChatOpenAI
from langchain.chains import create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import ChatPromptTemplate

from app.core.config import settings
from app.db.vector_store import get_vector_store
from app.db.models import QueryLogModel

# system prompt for "Oraculo Publicogov"
SYSTEM_PROMPT = (
    "Você é o 'Oráculo PublicGov', um assistente virtual especializado em legislação pública, "
    "editais de licitação e demandas de ouvidoria.\n"
    "Responda à pergunta do usuário utilizando APENAS o contexto de documentos fornecido abaixo.\n"
    "Se a resposta não constar no contexto, informe explicitamente que os documentos "
    "oficiais disponíveis não contêm essa informação.\n\n"
    "Contexto:\n{context}"
)

async def answer_question(question: str, doc_type_filter: str | None, db: Session) -> dict:
    vector_store = get_vector_store()
    
    # apply metadata filter if specified
    search_kwargs = {"k": 4}
    if doc_type_filter:
        search_kwargs["filter"] = {"doc_type": doc_type_filter}
        
    retriever = vector_store.as_retriever(search_kwargs=search_kwargs)

    # add some definitions to llm
    llm = ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0.1,
        openai_api_key=settings.OPENAI_API_KEY
    )
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", SYSTEM_PROMPT),
        ("human", "{input}")
    ])
    
    question_answer_chain = create_stuff_documents_chain(llm, prompt)
    rag_chain = create_retrieval_chain(retriever, question_answer_chain)
    
    response = rag_chain.invoke({"input": question})
    
    # extract unique sources cited
    sources = list(set([
        f"{doc.metadata.get('source_file', 'Desconhecido')} (Pág. {doc.metadata.get('page', 0) + 1})"
        for doc in response.get("context", [])
    ]))
    
    # log query execution
    query_log = QueryLogModel(
        question=question,
        answer=response["answer"],
        doc_type_filter=doc_type_filter
    )
    db.add(query_log)
    db.commit()
    
    return {
        "question": question,
        "answer": response["answer"],
        "sources": sources
    }