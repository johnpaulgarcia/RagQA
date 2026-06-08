# RAG Q&A — Document Intelligence

Upload PDFs. Ask questions. Get accurate answers with source citations — streamed in real-time.

Every RAG component (chunking, embedding, retrieval, generation) is **hand-written from scratch** — no LangChain, no black boxes.

**Live Demo: [ragqa.jadesect.com](https://ragqa.jadesect.com)** — pre-loaded with a sample document, try it now.

![Demo](docs/demo.gif)

## Why No LangChain?

Most RAG tutorials hide the pipeline behind LangChain abstractions. This project implements every step explicitly:

- **Chunking** — Recursive text splitting with paragraph → sentence → word boundary detection and configurable overlap
- **Embedding** — Direct OpenAI API calls with batch processing (2048 inputs/call)
- **Vector Search** — FAISS `IndexIDMap` with L2-normalized inner product (cosine similarity)
- **Retrieval** — Top-k similarity search with SQLite metadata for citation provenance
- **Generation** — Claude with streaming SSE, prompt caching, and conversation memory

This means every decision is visible, testable, and explainable in an interview.

## Architecture

```
Upload Flow
  PDF → AWS S3 → PyMuPDF (extract) → Recursive Chunker → OpenAI (embed) → FAISS + SQLite

Query Flow
  Question + Chat History → OpenAI (embed) → FAISS (top-k) → Claude (stream with citations) → SSE → Browser
```

## Features

- **Streaming answers** — Token-by-token SSE, not spinner → wall of text
- **Source citations** — Clickable `[1]` `[2]` references linked to exact document + page
- **Conversation memory** — Follow-up questions with context ("what about the security ones?")
- **Chat persistence** — Conversations survive page refresh via localStorage
- **Multi-document** — Query across all uploaded PDFs simultaneously
- **Drag-and-drop upload** — Visual progress: uploading → parsing → embedding → indexed → success
- **Prompt caching** — Anthropic `cache_control` on system prompts for cost efficiency
- **Dark mode UI** — Clean, polished single-page app

## Tech Stack

| Layer | Technology | Why |
|-------|-----------|-----|
| LLM | Claude (Anthropic SDK) | Best reasoning, streaming, prompt caching |
| Embeddings | OpenAI `text-embedding-3-small` | 1536-dim, 10K RPM, $0.02/1M tokens |
| Vector Store | FAISS `IndexIDMap` + SQLite | Zero-infra, cosine similarity, metadata tracking |
| PDF Parsing | PyMuPDF | Fastest Python PDF library |
| Backend | FastAPI | Async, type-safe, auto OpenAPI docs |
| Frontend | Vanilla JS + Tailwind CDN | Single-file SPA, no build step |
| Storage | AWS S3 | Durable document storage with presigned URLs |
| Packaging | uv + pyproject.toml | Modern Python |
| Deployment | Docker Compose | One command to run |

## Quick Start

```bash
git clone https://github.com/johnpaulgarcia/RagQA.git
cd RagQA

# Install
uv sync

# Configure
cp .env.example .env
# Add your keys:
#   ANTHROPIC_API_KEY — https://console.anthropic.com
#   OPENAI_API_KEY    — https://platform.openai.com

# Run
uv run revival
# Open http://localhost:8000
```

### Docker

```bash
cp .env.example .env
# Add your API keys to .env
docker compose up --build
# Open http://localhost:8000
```

### AWS S3 Setup (optional)

```bash
aws s3 mb s3://your-bucket-name --region us-east-1
# Update S3_BUCKET in .env
```

## Project Structure

```
src/revival/
├── __main__.py          # CLI entrypoint
├── config.py            # pydantic-settings
├── server.py            # FastAPI app
├── models.py            # Pydantic schemas
├── routers/
│   ├── documents.py     # Upload, list, delete
│   ├── query.py         # SSE streaming Q&A
│   └── health.py        # Health + stats
├── services/
│   ├── pdf_parser.py    # PyMuPDF text extraction
│   ├── chunker.py       # Recursive splitting with overlap
│   ├── embeddings.py    # OpenAI embedding wrapper
│   ├── vector_store.py  # FAISS IndexIDMap + SQLite
│   ├── s3.py            # S3 upload/download
│   └── rag.py           # RAG orchestrator
└── static/
    └── index.html       # Single-page frontend
```

## How It Works

**1. Document Ingestion**
PDFs are parsed page-by-page with PyMuPDF, then split into overlapping chunks (~500 tokens) using recursive boundary detection. Each chunk carries metadata: document ID, page number, and character offsets.

**2. Embedding**
Chunks are batch-embedded into 1536-dimensional vectors via OpenAI's `text-embedding-3-small`. Vectors are L2-normalized for cosine similarity.

**3. Vector Storage**
Vectors are stored in a FAISS `IndexIDMap` that maps directly to SQLite row IDs. This ensures correct chunk lookup even after document deletions and re-uploads.

**4. Retrieval + Generation**
User questions are embedded with the same model. FAISS returns the top-5 most similar chunks. These are formatted into a numbered context block and sent to Claude with conversation history. The system prompt enforces source-only answering with bracketed citations. Responses stream token-by-token via SSE.

## API

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/health` | Health check + index stats |
| `POST` | `/api/documents` | Upload PDF (multipart) |
| `GET` | `/api/documents` | List documents |
| `DELETE` | `/api/documents/:id` | Delete document |
| `POST` | `/api/query` | Ask a question (SSE stream) |

## License

MIT
