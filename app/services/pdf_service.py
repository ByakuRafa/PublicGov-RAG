import os
import shutil
from fastapi import UploadFile, HTTPException
from sqlalchemy.orm import Session
from PIL import Image
import pytesseract
from pdf2image import convert_from_path

from langchain_core.documents import Document
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.core.config import settings
from app.db.models import DocumentModel
from app.db.vector_store import get_vector_store

def _extract_text_with_ocr(file_path: str) -> list[Document]:
    """Converte as páginas do PDF em imagens e aplica OCR via Tesseract."""
    documents = []
    try:
        images = convert_from_path(file_path)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Falha ao renderizar PDF para OCR (verifique se o 'poppler' está instalado): {str(e)}"
        )

    for page_num, image in enumerate(images, start=1):
        # lang='por' garante acentuação correta para português brasileiro
        ocr_text = pytesseract.image_to_string(image, lang="por")
        if ocr_text.strip():
            documents.append(
                Document(
                    page_content=ocr_text,
                    metadata={"page": page_num}
                )
            )
            
    return documents

async def process_and_index_pdf(file: UploadFile, doc_type: str, db: Session) -> DocumentModel:
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    file_path = os.path.join(settings.UPLOAD_DIR, file.filename)
    
    # 1. Salvar o arquivo localmente
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    # 2. Tentar extração direta de texto (rápida)
    loader = PyPDFLoader(file_path)
    documents = loader.load()
    
    valid_docs = [doc for doc in documents if len(doc.page_content.strip()) > 30]
    
    # 3. Fallback: Se não houver texto legível, aplica OCR
    if not valid_docs:
        print(f"⚠️ Nenhum texto nativo encontrado em '{file.filename}'. Executando OCR...")
        valid_docs = _extract_text_with_ocr(file_path)

    if not valid_docs:
        raise HTTPException(
            status_code=400,
            detail="Não foi possível extrair nenhum texto do PDF, mesmo após o processamento via OCR."
        )

    # 4. Enriquecer metadados para busca e citação
    for doc in valid_docs:
        doc.metadata["doc_type"] = doc_type
        doc.metadata["source_file"] = file.filename
        
    # 5. Chunking
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=150
    )
    chunks = text_splitter.split_documents(valid_docs)
    
    # 6. Indexação no ChromaDB
    vector_store = get_vector_store()
    vector_store.add_documents(chunks)
    
    # 7. Persistência no Banco Relacional
    doc_record = DocumentModel(
        filename=file.filename,
        doc_type=doc_type,
        chunks_count=len(chunks)
    )
    db.add(doc_record)
    db.commit()
    db.refresh(doc_record)
    
    return doc_record