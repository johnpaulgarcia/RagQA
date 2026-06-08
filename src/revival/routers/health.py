from __future__ import annotations

from fastapi import APIRouter

from revival.services.vector_store import get_store

router = APIRouter(tags=["health"])


@router.get("/api/health")
async def health():
    stats = get_store().get_stats()
    return {"status": "ok", **stats}
