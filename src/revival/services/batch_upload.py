"""Batch upload service — process multiple PDFs concurrently."""
from __future__ import annotations

import asyncio
import uuid
import os
from typing import Any

from revival.services import s3, pdf_parser, embeddings
from revival.services.chunker import chunk_pages
from revival.services.vector_store import get_store

# Max concurrent uploads
MAX_CONCURRENT = 5
TEMP_DIR = "/tmp/ragqa_uploads"


async def process_single_file(content: bytes, filename: str) -> dict[str, Any]:
    """Process a single PDF file through the RAG pipeline."""
    doc_id = uuid.uuid4().hex[:12]
    s3_key = f"documents/{doc_id}/{filename}"

    # Upload to S3
    s3.upload_pdf(content, s3_key)

    # Parse
    pages = pdf_parser.extract_pages(content)
    if not pages:
        return {"filename": filename, "status": "error", "error": "No text found"}

    # Chunk
    page_tuples = [(p.page_number, p.text) for p in pages]
    chunks = chunk_pages(page_tuples, document_id=doc_id)

    # Embed
    texts = [c.text for c in chunks]
    vecs = embeddings.embed_documents(texts)

    # Store
    store = get_store()
    store.add_document(
        doc_id=doc_id,
        filename=filename,
        s3_key=s3_key,
        page_count=len(pages),
        chunks=chunks,
        embeddings=vecs,
    )

    return {
        "id": doc_id,
        "filename": filename,
        "pages": len(pages),
        "chunks": len(chunks),
        "status": "success",
    }


async def batch_upload(files: list[tuple[str, bytes]]) -> list[dict]:
    """Upload multiple files concurrently.

    Args:
        files: list of (filename, content) tuples
    """
    # Save files to temp directory for processing
    os.makedirs(TEMP_DIR, exist_ok=True)

    semaphore = asyncio.Semaphore(MAX_CONCURRENT)

    async def limited_process(filename: str, content: bytes):
        async with semaphore:
            try:
                return await process_single_file(content, filename)
            except Exception as e:
                return {"filename": filename, "status": "error", "error": str(e)}

    tasks = [limited_process(name, content) for name, content in files]
    results = await asyncio.gather(*tasks)

    return list(results)


def validate_file(filename: str, content: bytes) -> str | None:
    """Validate a file before upload. Returns error message or None."""
    if not filename.lower().endswith(".pdf"):
        return "Only PDF files are supported"

    # 50MB limit
    if len(content) > 50 * 1024 * 1024:
        return "File too large (max 50MB)"

    # Check PDF magic bytes
    if content[:4] != b"%PDF":
        return "Invalid PDF file"

    return None
