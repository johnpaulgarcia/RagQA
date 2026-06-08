from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, UploadFile, File, HTTPException

from revival.services import s3, pdf_parser, embeddings
from revival.services.chunker import chunk_pages
from revival.services.vector_store import get_store

log = logging.getLogger(__name__)
router = APIRouter(prefix="/api/documents", tags=["documents"])


@router.post("")
async def upload_document(file: UploadFile = File(...)):
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(400, "Only PDF files are supported")

    content = await file.read()
    if len(content) > 50 * 1024 * 1024:
        raise HTTPException(400, "File size must be under 50MB")

    doc_id = uuid.uuid4().hex[:12]
    s3_key = f"documents/{doc_id}/{file.filename}"

    try:
        # 1. Upload to S3
        s3.upload_pdf(content, s3_key)
    except Exception as e:
        log.exception("S3 upload failed")
        raise HTTPException(502, f"Failed to upload to S3: {e}")

    # 2. Parse PDF
    pages = pdf_parser.extract_pages(content)
    if not pages:
        raise HTTPException(400, "Could not extract text from PDF — no readable text found")

    # 3. Chunk
    page_tuples = [(p.page_number, p.text) for p in pages]
    chunks = chunk_pages(page_tuples, document_id=doc_id)

    try:
        # 4. Embed
        texts = [c.text for c in chunks]
        vecs = embeddings.embed_documents(texts)
    except Exception as e:
        log.exception("Embedding failed")
        msg = str(e)
        if "RateLimit" in type(e).__name__ or "rate" in msg.lower():
            raise HTTPException(429, "Embedding rate limit hit — please wait a moment and try again")
        raise HTTPException(502, f"Failed to generate embeddings: {msg}")

    # 5. Store
    store = get_store()
    store.add_document(
        doc_id=doc_id,
        filename=file.filename,
        s3_key=s3_key,
        page_count=len(pages),
        chunks=chunks,
        embeddings=vecs,
    )

    return {
        "id": doc_id,
        "filename": file.filename,
        "pages": len(pages),
        "chunks": len(chunks),
    }


@router.get("")
async def list_documents():
    return get_store().list_documents()


@router.delete("/{doc_id}")
async def delete_document(doc_id: str):
    store = get_store()
    docs = store.list_documents()
    doc = next((d for d in docs if d["id"] == doc_id), None)
    if not doc:
        raise HTTPException(404, "Document not found")

    s3.delete_object(doc["s3_key"])
    store.delete_document(doc_id)
    return {"deleted": doc_id}
