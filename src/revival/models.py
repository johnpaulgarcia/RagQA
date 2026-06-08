from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class DocumentMeta(BaseModel):
    id: str
    filename: str
    s3_key: str
    page_count: int
    chunk_count: int
    created_at: str


class Chunk(BaseModel):
    document_id: str
    chunk_index: int
    page_number: int
    text: str
    char_start: int
    char_end: int


class ChunkResult(BaseModel):
    text: str
    document_id: str
    filename: str
    page_number: int
    chunk_index: int
    score: float


class ChatMessage(BaseModel):
    role: str  # "user" or "assistant"
    content: str


class QueryRequest(BaseModel):
    question: str
    history: list[ChatMessage] = []


class SourceReference(BaseModel):
    index: int
    filename: str
    page_number: int
    text: str
    score: float
