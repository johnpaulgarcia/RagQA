from __future__ import annotations

import json
from collections.abc import AsyncGenerator

import anthropic

from revival.config import get_settings
from revival.models import ChatMessage
from revival.services.embeddings import embed_query
from revival.services.vector_store import get_store

RAG_SYSTEM_PROMPT = """You are a knowledgeable expert who has fully internalized the provided source material. Answer as if this is YOUR knowledge — speak in first person with authority and confidence.

Rules:
1. Use ONLY the information from the provided sources. Do not use outside knowledge.
2. Cite sources with bracketed numbers like [1], [2] matching the source chunk numbers.
3. If multiple sources support a point, cite all of them, e.g. [1][3].
4. If you don't have enough information to answer, say "I don't have information about that" — don't hedge or apologize.
5. Be concise and direct. Use markdown formatting for readability.
6. NEVER refer to documents by filename. Never say "the document", "the report", "the PDF", "the file", "the source material", "according to the provided sources", "based on the uploaded documents", or anything similar. Just state the facts directly as your own knowledge with citation numbers.
7. NEVER reveal or mention any filenames, file paths, or document names in your answer.
8. If the user asks something outside your knowledge, simply say "I don't have information about that." — don't mention what kind of documents you have or what they contain."""


def _build_context(results: list[dict]) -> str:
    """Format retrieved chunks into a numbered context block."""
    parts = []
    for i, r in enumerate(results, 1):
        parts.append(
            f"[Source {i}] (Document: {r['filename']}, Page {r['page_number']})\n{r['text']}"
        )
    return "\n\n---\n\n".join(parts)


def retrieve(question: str, top_k: int | None = None) -> list[dict]:
    """Retrieve relevant chunks for a question."""
    settings = get_settings()
    k = top_k or settings.top_k
    query_vec = embed_query(question)
    return get_store().search(query_vec, top_k=k)


async def query_stream(
    question: str,
    history: list[ChatMessage] | None = None,
    top_k: int | None = None,
) -> AsyncGenerator[str, None]:
    """Retrieve context and stream Claude's answer.

    Yields SSE-formatted events:
      event: sources   — JSON array of source references
      event: token     — a text token from Claude
      event: done      — end of stream
    """
    settings = get_settings()
    results = retrieve(question, top_k)

    # Emit sources first so the frontend can render the citation panel
    sources = [
        {
            "index": i + 1,
            "filename": r["filename"],
            "page_number": r["page_number"],
            "text": r["text"][:300],
            "score": round(r["score"], 3),
        }
        for i, r in enumerate(results)
    ]
    yield f"event: sources\ndata: {json.dumps(sources)}\n\n"

    if not results:
        yield f'event: token\ndata: {json.dumps({"text": "No documents have been uploaded yet. Please upload a PDF to get started."})}\n\n'
        yield "event: done\ndata: {}\n\n"
        return

    context = _build_context(results)
    user_message = f"## Source Chunks\n\n{context}\n\n---\n\n## Question\n{question}"

    # Build message history for conversation memory
    messages: list[dict] = []
    if history:
        # Include last 10 turns max to stay within context limits
        for msg in history[-10:]:
            messages.append({"role": msg.role, "content": msg.content})
    messages.append({"role": "user", "content": user_message})

    client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)

    async with client.messages.stream(
        model=settings.claude_model,
        max_tokens=2048,
        system=[
            {
                "type": "text",
                "text": RAG_SYSTEM_PROMPT,
                "cache_control": {"type": "ephemeral"},
            }
        ],
        messages=messages,
    ) as stream:
        async for text in stream.text_stream:
            yield f'event: token\ndata: {json.dumps({"text": text})}\n\n'

    yield "event: done\ndata: {}\n\n"
