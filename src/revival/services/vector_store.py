from __future__ import annotations

import sqlite3
from pathlib import Path

import faiss
import numpy as np

from revival.config import get_settings
from revival.services.chunker import ChunkMeta


class VectorStore:
    """FAISS index (with ID mapping) + SQLite metadata store for document chunks."""

    def __init__(self, db_path: Path, faiss_path: Path, dim: int = 512):
        self.db_path = db_path
        self.faiss_path = faiss_path
        self.dim = dim
        self._conn: sqlite3.Connection | None = None
        self._index: faiss.IndexIDMap | None = None

    def initialize(self) -> None:
        """Create tables and load or create FAISS index."""
        self._conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS documents (
                id TEXT PRIMARY KEY,
                filename TEXT NOT NULL,
                s3_key TEXT NOT NULL,
                page_count INTEGER,
                chunk_count INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS chunks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                document_id TEXT REFERENCES documents(id) ON DELETE CASCADE,
                chunk_index INTEGER,
                page_number INTEGER,
                text TEXT NOT NULL,
                char_start INTEGER,
                char_end INTEGER
            );
            """
        )
        self._conn.execute("PRAGMA foreign_keys = ON")

        if self.faiss_path.exists():
            self._index = faiss.read_index(str(self.faiss_path))
        else:
            base = faiss.IndexFlatIP(self.dim)
            self._index = faiss.IndexIDMap(base)

    @property
    def conn(self) -> sqlite3.Connection:
        assert self._conn is not None, "Call initialize() first"
        return self._conn

    @property
    def index(self) -> faiss.IndexIDMap:
        assert self._index is not None, "Call initialize() first"
        return self._index

    def add_document(
        self,
        doc_id: str,
        filename: str,
        s3_key: str,
        page_count: int,
        chunks: list[ChunkMeta],
        embeddings: np.ndarray,
    ) -> None:
        """Store document metadata, chunks, and embeddings."""
        self.conn.execute(
            "INSERT INTO documents (id, filename, s3_key, page_count, chunk_count) VALUES (?, ?, ?, ?, ?)",
            (doc_id, filename, s3_key, page_count, len(chunks)),
        )

        chunk_ids: list[int] = []
        for chunk in chunks:
            cursor = self.conn.execute(
                "INSERT INTO chunks (document_id, chunk_index, page_number, text, char_start, char_end) VALUES (?, ?, ?, ?, ?, ?)",
                (
                    chunk.document_id,
                    chunk.chunk_index,
                    chunk.page_number,
                    chunk.text,
                    chunk.char_start,
                    chunk.char_end,
                ),
            )
            chunk_ids.append(cursor.lastrowid)
        self.conn.commit()

        # Normalize and add to FAISS with SQLite chunk IDs
        faiss.normalize_L2(embeddings)
        ids = np.array(chunk_ids, dtype=np.int64)
        self.index.add_with_ids(embeddings, ids)
        faiss.write_index(self.index, str(self.faiss_path))

    def search(
        self, query_embedding: np.ndarray, top_k: int = 5
    ) -> list[dict]:
        """Search for the top-k most similar chunks."""
        if self.index.ntotal == 0:
            return []

        query = query_embedding.reshape(1, -1).copy()
        faiss.normalize_L2(query)
        scores, ids = self.index.search(query, min(top_k, self.index.ntotal))

        results = []
        for score, chunk_id in zip(scores[0], ids[0]):
            if chunk_id == -1:
                continue
            row = self.conn.execute(
                """
                SELECT c.text, c.page_number, c.chunk_index, c.document_id, d.filename
                FROM chunks c JOIN documents d ON c.document_id = d.id
                WHERE c.id = ?
                """,
                (int(chunk_id),),
            ).fetchone()
            if row:
                results.append(
                    {
                        "text": row["text"],
                        "page_number": row["page_number"],
                        "chunk_index": row["chunk_index"],
                        "document_id": row["document_id"],
                        "filename": row["filename"],
                        "score": float(score),
                    }
                )
        return results

    def delete_document(self, doc_id: str) -> None:
        """Delete a document and rebuild the FAISS index."""
        self.conn.execute("DELETE FROM documents WHERE id = ?", (doc_id,))
        self.conn.execute("DELETE FROM chunks WHERE document_id = ?", (doc_id,))
        self.conn.commit()
        self._rebuild_index()

    def _rebuild_index(self) -> None:
        """Rebuild FAISS index from scratch (needed after deletion)."""
        from revival.services.embeddings import embed_documents

        base = faiss.IndexFlatIP(self.dim)
        self._index = faiss.IndexIDMap(base)
        rows = self.conn.execute(
            "SELECT id, text FROM chunks ORDER BY id"
        ).fetchall()
        if rows:
            ids = np.array([r["id"] for r in rows], dtype=np.int64)
            texts = [r["text"] for r in rows]
            embeddings = embed_documents(texts)
            faiss.normalize_L2(embeddings)
            self.index.add_with_ids(embeddings, ids)
        faiss.write_index(self.index, str(self.faiss_path))

    def list_documents(self) -> list[dict]:
        rows = self.conn.execute(
            "SELECT id, filename, s3_key, page_count, chunk_count, created_at FROM documents ORDER BY created_at DESC"
        ).fetchall()
        return [dict(r) for r in rows]

    def get_stats(self) -> dict:
        doc_count = self.conn.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
        chunk_count = self.conn.execute("SELECT COUNT(*) FROM chunks").fetchone()[0]
        return {
            "documents": doc_count,
            "chunks": chunk_count,
            "vectors": self.index.ntotal,
        }


# Singleton
_store: VectorStore | None = None


def get_store() -> VectorStore:
    global _store
    if _store is None:
        settings = get_settings()
        _store = VectorStore(
            db_path=settings.db_path,
            faiss_path=settings.faiss_path,
            dim=settings.embedding_dim,
        )
        _store.initialize()
    return _store
