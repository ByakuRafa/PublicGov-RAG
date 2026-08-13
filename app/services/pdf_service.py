import os
import shutil
from fastapi import UploadFile
from sqlalchemy.orm import Session
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.core.config import settings
from app.db.models import DocumentModel
from app.db.vector_store import get_vector_store

async def process_and_index_pdf(file: UploadFile, doc_type: str, db: Session) -> DocumentModel:
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    file_path = os.path.join(settings.UPLOAD_DIR, file.filename)
    
    # save local files
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    # load
    loader = PyPDFLoader(file_path)
    documents = loader.load()
    
    # inject metadata in chunks
    for doc in documents:
        doc.metadata["doc_type"] = doc_type
        doc.metadata["source_file"] = file.filename
        
    # split text into chunks
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=150
    )
    chunks = text_splitter.split_documents(documents)
    
    # store in ChromaDB
    vector_store = get_vector_store()
    vector_store.add_documents(chunks)
    
    # save record in relational database
    doc_record = DocumentModel(
        filename=file.filename,
        doc_type=doc_type,
        chunks_count=len(chunks)
    )
    db.add(doc_record)
    db.commit()
    db.refresh(doc_record)
    
    return doc_record