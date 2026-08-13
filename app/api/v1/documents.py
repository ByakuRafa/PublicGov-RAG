from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.api.deps import get_db
from app.services.pdf_service import process_and_index_pdf

router = APIRouter()

@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...),
    doc_type: str = Form("Edital"),
    db: Session = Depends(get_db)
):
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Apenas arquivos PDF são aceitos.")
        
    doc = await process_and_index_pdf(file, doc_type, db)
    return {
        "message": f"Documento '{doc.filename}' processado e indexado com sucesso!",
        "document_id": doc.id,
        "chunks_created": doc.chunks_count
    }