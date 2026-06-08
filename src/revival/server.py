from __future__ import annotations

import logging
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from revival.routers import health, documents, query
from revival.services.vector_store import get_store

log = logging.getLogger(__name__)

DEMO_PDF = Path(__file__).parent / "static" / "demo-document.pdf"


def _seed_demo_document() -> None:
    """Load the demo PDF on first startup so the app isn't empty."""
    store = get_store()
    if store.list_documents():
        return  # Already has documents

    if not DEMO_PDF.exists():
        return

    from revival.services import pdf_parser, embeddings, s3
    from revival.services.chunker import chunk_pages

    log.info("Seeding demo document...")
    content = DEMO_PDF.read_bytes()
    doc_id = uuid.uuid4().hex[:12]
    filename = "NovaTech-AI-Company-Report.pdf"
    s3_key = f"documents/{doc_id}/{filename}"

    try:
        s3.upload_pdf(content, s3_key)
    except Exception:
        s3_key = f"local/{doc_id}/{filename}"
        log.warning("S3 upload failed for demo doc, continuing with local-only")

    pages = pdf_parser.extract_pages(content)
    page_tuples = [(p.page_number, p.text) for p in pages]
    chunks = chunk_pages(page_tuples, document_id=doc_id)
    vecs = embeddings.embed_documents([c.text for c in chunks])

    store.add_document(
        doc_id=doc_id,
        filename=filename,
        s3_key=s3_key,
        page_count=len(pages),
        chunks=chunks,
        embeddings=vecs,
    )
    log.info(f"Demo document seeded: {len(pages)} pages, {len(chunks)} chunks")


@asynccontextmanager
async def lifespan(app: FastAPI):
    get_store()
    _seed_demo_document()
    yield


app = FastAPI(
    title="RAG Q&A — Document Intelligence",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(documents.router)
app.include_router(query.router)

# Serve the frontend
static_dir = Path(__file__).parent / "static"
app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="static")
