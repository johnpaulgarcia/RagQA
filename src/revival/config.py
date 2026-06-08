from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parent.parent.parent  # revival/


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # LLM — Claude
    anthropic_api_key: str
    claude_model: str = "claude-sonnet-4-20250514"

    # Embeddings — OpenAI
    openai_api_key: str
    embedding_model: str = "text-embedding-3-small"
    embedding_dim: int = 1536

    # AWS S3
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""
    aws_region: str = "us-east-1"
    s3_bucket: str = "revival-docs-888491521698"

    # RAG tuning
    chunk_size: int = 500
    chunk_overlap: int = 50
    top_k: int = 5

    # Server
    host: str = "0.0.0.0"
    port: int = 8000

    # Paths
    @property
    def data_dir(self) -> Path:
        d = ROOT / "data"
        d.mkdir(exist_ok=True)
        return d

    @property
    def db_path(self) -> Path:
        return self.data_dir / "revival.db"

    @property
    def faiss_path(self) -> Path:
        return self.data_dir / "faiss.index"


_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
